#  MIT License
#
#  Copyright (c) 2021 ben
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.
from __future__ import annotations
import logging
import sys
import typing as t
import inspect
import functools
import importlib
import sys
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import hikari

from kousen.context import Context, PartialContext
from kousen.colours import Colour
from kousen.errors import _MissingLoad, _MissingUnload

if t.TYPE_CHECKING:
    from kousen.modules import Module

__all__: list[str] = ["Bot", "loader", "unloader"]

_LOGGER = logging.getLogger("kousen")


class _Loader:
    def __init__(self, callback: t.Callable[["Bot"], t.Any]) -> None:
        self._callback: t.Callable[["Bot"], t.Any] = callback

    def __call__(self, bot) -> None:
        self._callback(bot)


class _UnLoader:
    def __init__(self, callback: t.Callable[["Bot"], t.Any]) -> None:
        self._callback: t.Callable[["Bot"], t.Any] = callback

    def __call__(self, bot) -> None:
        self._callback(bot)


def loader(callback: t.Callable[["Bot"], t.Any]) -> _Loader:
    return _Loader(callback)


def unloader(callback: t.Callable[["Bot"], t.Any]) -> _UnLoader:
    return _UnLoader(callback)


async def _prefix_getter_with_callback(
    partial_context: PartialContext, callback
) -> list[str]:
    getter_result = await callback(partial_context)

    if isinstance(getter_result, str):
        return [getter_result]

    if isinstance(getter_result, t.Iterable):
        list1: list[str] = []
        list1.extend(list(*map(str, getter_result)))
        return list1

    else:
        raise TypeError(
            f"The prefix callback must return a string or iterable of strings, not type {type(getter_result)}"
        )


def _base_bool_getter_handler(callable_or_bool, name: str):
    if isinstance(callable_or_bool, bool):
        return functools.partial(_base_getter, return_object=callable_or_bool)
    elif inspect.iscoroutinefunction(callable_or_bool):
        return functools.partial(
            _base_getter_with_callback,
            callback=callable_or_bool,
            result_type=[bool],
            error_text=f"The {name} callback must return a bool",
        )
    else:
        raise TypeError(
            f"{name.capitalize()} arg must be either a bool or a coroutine, not type {type(callable_or_bool)}"
        )


async def _base_getter_with_callback(
    partial_context_or_context,
    callback,
    result_types: t.Iterable[t.Any],
    error_text: str,
):
    getter_result = await callback(partial_context_or_context)
    for result_tp in result_types:
        if isinstance(getter_result, result_tp):
            return getter_result
    else:
        raise TypeError(f"{error_text}, not type {type(getter_result)}")


async def _base_getter(_, return_obj):
    return return_obj


class Bot(hikari.GatewayBot):
    """The standard implementation of :class:`hikari.impl.bot.GatewayBot` with a command handler.

    Note
    ----
    Mention prefixes will continue to work with message commands after the message content intent becomes privileged.

    Parameters
    ----------
    default_prefix : Union[:obj:`str`, Iterable[:obj:`str`], Callable[[:obj:`~PartialContext`], Coroutine[:obj:`None`, :obj:`None`, Union[:obj:`str`, Iterable[:obj:`str`]]]]
        The bot's command prefix.
    mention_prefix : :obj:`bool`
        Whether or not the bot's mention will be used as a prefix. This will be `True` if no default
        prefix is provided, else `False` by default.

    Other Parameters
    ----------------
    default_parser : Union[:obj:`str`, Callable[[:obj:`~Context`], Coroutine[:obj:`None`, :obj:`None`, :obj:`str`]]]
        The default parser to use for parsing message content for command arguments. Defaults to a whitespace.
        (Note that regardless of this parser, commands and subcommands should always be seperated
        by a whitespace, as this option only affects argument parsing.)
    weak_command_search : Union[:obj:`bool`, Callable[[:obj:`~PartialContext`], Coroutine[:obj:`None`, :obj:`None`, :obj:`bool`]]]
        If `True`, then the bot will parse for the prefix throughout the message content (instead of just the
        start), allowing for commands to be called at any point in the message. Defaults to False.
    case_insensitive_commands : Union[:obj:`bool`, Callable[[:obj:`~PartialContext`], Coroutine[:obj:`None`, :obj:`None`, :obj:`bool`]]]
        Whether or not commands should be case-insensitive or not. Defaults to `False` (commands are case-sensitive).
    case_insensitive_prefixes : Union[:obj:`bool`, Callable[[:obj:`~PartialContext`], Coroutine[:obj:`None`, :obj:`None`, :obj:`bool`]]]
        Whether or not prefixes should be handled as case-insensitive or not.
        Defaults to `False` (prefixes are case-sensitive).
    ignore_bots : Union[:obj:`bool`, Callable[[:obj:`~PartialContext`], Coroutine[:obj:`None`, :obj:`None`, :obj:`bool`]]]
        Prevents other bot's messages invoking your bot's commands if `True`. Defaults to `True`.
    owners : Iterable[`int`]
        The IDs or User objects of the users which should be treated as "owners" of the bot.
    default_embed_colour : Optional[:obj:`hikari.Colorish`]
        The default colour to use in embeds, the default is :obj:`kousen.Colour.EMBED_BACKGROUND`.
        (Note: Kousen can only apply this default in :obj:`Context.respond()` but this can be
        used manually when setting colours of other embeds.) You must pass `None` if you do not want a default
        embed colour to be set
    scheduler : :obj:`AsyncIOScheduler`
        The async scheduler to use for managing tasks and kousen events.
    """

    __slots__ = (
        "_cache_components",
        "_prefix_getter",
        "_mention_prefixes",
        "_default_parser_getter",
        "_weak_command_search",
        "_case_insensitive_commands",
        "_case_insensitive_prefixes",
        "_ignore_bots",
        "_owners",
        "_custom_attributes",
        "_default_embed_colour",
    )

    def __init__(
        self,
        *args,
        default_prefix: t.Union[
            str,
            t.Iterable[str],
            t.Callable[
                [PartialContext], t.Coroutine[None, None, t.Union[str, t.Iterable[str]]]
            ],
        ] = None,
        mention_prefix: bool = None,  # so the default can be different depending on whether a prefix was passed
        default_parser: t.Union[
            str, t.Callable[[Context], t.Coroutine[None, None, str]]
        ] = " ",
        weak_command_search: t.Union[
            bool, t.Callable[[PartialContext], t.Coroutine[None, None, bool]]
        ] = False,
        case_insensitive_commands: t.Union[
            bool, t.Callable[[PartialContext], t.Coroutine[None, None, bool]]
        ] = False,
        case_insensitive_prefixes: t.Union[
            bool, t.Callable[[PartialContext], t.Coroutine[None, None, bool]]
        ] = False,
        ignore_bots: t.Union[
            bool, t.Callable[[PartialContext], t.Coroutine[None, None, bool]]
        ] = True,
        owners: t.Iterable[int] = (),
        default_embed_colour: t.Optional[
            t.Union[hikari.Colorish]
        ] = Colour.EMBED_BACKGROUND,
        scheduler: AsyncIOScheduler = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        # allows us to check cache settings later on
        if (cache_settings := kwargs.get("cache_settings")) is not None:
            self._cache_components = cache_settings.components
        else:
            self._cache_components = hikari.CacheComponents.ALL

        if mention_prefix is False and default_prefix is None:
            raise ValueError(
                "No default prefix was provided and mention_prefix was set to False."
            )

        self._mention_prefixes: list[str] = []
        if mention_prefix is True or default_prefix is None:
            self.subscribe(hikari.StartedEvent, self._setup_mention_prefixes)
            self._prefix_getter = functools.partial(_base_getter, return_object=[])
        else:
            if isinstance(default_prefix, str):
                self._prefix_getter = functools.partial(
                    _base_getter, return_object=[default_prefix]
                )

            if isinstance(default_prefix, t.Iterable):
                prefix_list: list[str] = []
                prefix_list.extend(list(*map(str, default_prefix)))
                self._prefix_getter = functools.partial(
                    _base_getter, return_object=prefix_list
                )

            if inspect.iscoroutinefunction(default_prefix):
                self._prefix_getter = functools.partial(
                    _prefix_getter_with_callback, callback=default_prefix
                )

            else:
                raise TypeError(
                    f"Prefix must be either a string, or iterable of strings, or a coroutine, not type {type(default_prefix)}"
                )

        if isinstance(default_parser, str):
            self._default_parser_getter = functools.partial(
                _base_getter, return_object=default_parser
            )

        elif inspect.iscoroutinefunction(default_parser):
            self._default_parser_getter = functools.partial(
                _base_getter_with_callback,
                callback=default_parser,
                result_type=[str],
                error_text="The parser callback must return a string",
            )
        else:
            raise TypeError(
                f"Parser must be either a string or a coroutine, not type {type(default_parser)}"
            )

        self._weak_command_search = _base_bool_getter_handler(
            weak_command_search, "Weak command search"
        )
        self._case_insensitive_commands = _base_bool_getter_handler(
            case_insensitive_commands, "Case insensitive commands"
        )
        self._case_insensitive_prefixes = _base_bool_getter_handler(
            case_insensitive_prefixes, "Case insensitive prefixes"
        )
        self._ignore_bots = _base_bool_getter_handler(ignore_bots, "Ignore bots")

        self._owners = []
        if owners is not None:
            if not isinstance(owners, t.Iterable):
                raise TypeError(f"Owners must be an iterable, not type {type(owners)}")
            else:
                for owner in owners:
                    if not isinstance(owner, int):
                        raise TypeError(
                            f"Owners must be an iterable of ints, not of type {type(owner)}"
                        )
                    self._owners.append(owner)

        if isinstance(scheduler, AsyncIOScheduler):
            self._scheduler = scheduler
        else:
            self._scheduler = AsyncIOScheduler()
        self._custom_attributes: dict[str, t.Any] = {"ok": 4}
        self._default_embed_colour = default_embed_colour
        self._extensions: list[str] = []

    async def _setup_mention_prefixes(self, _: hikari.StartedEvent) -> None:
        user = self.get_me()
        if user is None:
            user = await self.rest.fetch_my_user()
            # todo implement backoff with fetch
        self._mention_prefixes = [f"<@{user.id}>", f"<@!{user.id}>"]

    def __getattr__(self, item):
        if item in self._custom_attributes:
            return self._custom_attributes[item]
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{item}'"
        )

    def add_custom_attribute(self, name: str, attribute_value: t.Any) -> "Bot":
        """
        Add a custom attribute to the bot instance, the value of this can be anything and can be accessed with the
        name passed.

        Parameters
        ----------
        name : `str`
            The name to be used when accessing this attribute.
        attribute_value : :obj:`~typing.Any`
            The value returned when the the attribute is accessed.

        Example
        -------
        .. code-block:: python
            import kousen
            import DataBase  # an example use for a custom attribute, where DataBase is a user-made database class.

            bot = kousen.Bot(...)
            bot.add_custom_attribute("database", DataBase(...))

            # wherever you have access to the bot instance (e.g. in a command)
            database = bot.database
            database.method()

            # the custom attribute can also be a function that can be called
            def custom_callback(*args, **kwargs):
                ...

            bot.add_custom_attribute("custom_callback", custom_callback)
            item = bot.custom_callback(*args, **kwargs)

        Returns
        -------
        :obj:`Bot`
            The instance of the bot to allow for chained calls.

        Raises
        ------
        ValueError
            If there is already an existing attribute or method by that name.
        """
        name = str(name)
        if name in self._custom_attributes or getattr(self, name, None):
            raise ValueError(f"There is already a bot attribute '{name}'")
        self._custom_attributes[name] = attribute_value
        return self

    def edit_custom_attribute(self, name: str, new_attribute_value: t.Any) -> "Bot":
        """
        Set a new value for a previously added custom attribute. See :obj:`add_custom_attribute` for
        details on adding a custom attribute.

        Parameters
        ----------
        name : `str`
            The name of the existing attribute.
        new_attribute_value : :obj:`~typing.Any`
            The new value of the attribute.

        Returns
        -------
        :obj:`Bot`
            The instance of the bot to allow for chained calls.

        Raises
        ------
        ValueError
            If there is no existing custom attribute with the name passed.
        """
        name = str(name)
        if name not in self._custom_attributes:
            raise ValueError(
                f"Cannot set new value of '{name}' as there is no custom attribute named '{name}'"
            )
        self._custom_attributes[name] = new_attribute_value
        return self

    def delete_custom_attribute(self, name: str) -> "Bot":
        """
        Deletes a previously set custom attribute.

        Parameters
        ----------
        name : `str`
            The name of the existing attribute.

        Returns
        -------
        :obj:`Bot`
            The instance of the bot to allow for chained calls.

        Raises
        ------
        ValueError
            If there is no existing custom attribute with the name passed.
        """
        name = str(name)
        if name not in self._custom_attributes:
            raise ValueError(f"There is no custom attribute named '{name}'")
        self._custom_attributes.pop(name)
        return self

    def load_extensions(self, extension_path: str, *extension_paths: str):
        """
        Load an external extension file into the bot from its path, which can contain modules.

        Parameters
        ----------
        extension_path : `str`
            The name of the path to load from. The path must be in the format <directory>.<file> or <directory>/<file>.
            (E.g. `"project.modules.admin"` or `"project/modules/admin"`.)
            Note that any additional slashes or dots are stripped.

        Other Parameters
        ----------------
        extension_paths : `str`
            Addition paths to load from, they must follow the same rules as above.

        Examples
        --------
        In order for this to work, the extension must have a function decorated with :obj:`loader` that takes
        one positional argument of type :obj:`Bot`

        .. code-block:: python
            import kousen

            admin_module = kousen.Module(...)

            ...

            @kousen.loader
            def admin_loader(bot: kousen.Bot):
                bot.add_module(admin_module)

        Returns
        -------
        :obj:`Bot`
            The instance of the bot to allow for chained calls.
        """
        all_extension_paths = list(extension_paths)
        all_extension_paths.append(extension_path)
        for _extension_path in all_extension_paths:
            _extension_path.replace("/", ".").strip(".")
            if _extension_path in self._extensions:
                _LOGGER.error(
                    f"The extension {_extension_path} failed to load because it was already loaded."
                )
            try:
                _extension = importlib.import_module(_extension_path)
                for _, member in inspect.getmembers(_extension):
                    if isinstance(member, _Loader):
                        member(self)
                        self._extensions.append(_extension_path)
                        _LOGGER.info(f"Extension {_extension_path} was successfully loaded.")
                        break
                else:
                    _LOGGER.error(
                        f"The extension {_extension_path} failed to load because no loader function was found."
                    )
            except Exception as ex:
                _LOGGER.error(f"The extension {_extension_path} failed to load.", exc_info=ex)

        return self

    def unload_extensions(self, extension_path: str, *extension_paths: str):
        """
        Unload an extension.

        Note
        ----
        There must be a :obj:`loader` function in the file.

        Parameters
        ----------
        extension_path : `str`
            The name of the path to reload. The path must be in the format <directory>.<file> or <directory>/<file>.
            (E.g. `"project.modules.admin"` or `"project/modules/admin"`.)
            Note that any additional slashes or dots are stripped.

        Other Parameters
        ----------------
        extension_paths : `str`
            Addition paths to reload, they must follow the same rules as above.

        Returns
        -------
        :obj:`Bot`
            The instance of the bot to allow for chained calls.
        """
        all_extension_paths = list(extension_paths)
        all_extension_paths.append(extension_path)
        for _extension_path in all_extension_paths:
            _extension_path.replace("/", ".").strip(".")
            if _extension_path not in self._extensions:
                _LOGGER.error(
                    f"The extension {_extension_path} failed to unload because it was not loaded."
                )
            try:
                _extension = importlib.import_module(_extension_path)
                for _, member in inspect.getmembers(_extension):
                    if isinstance(member, _UnLoader):
                        member(self)
                        self._extensions.remove(_extension_path)
                        sys.modules.pop(_extension_path)
                        _LOGGER.info(f"Extension {_extension_path} was successfully unloaded.")
                        break
                else:
                    _LOGGER.error(
                        f"The extension {_extension_path} failed to unload because no unloader function was found."
                    )
            except Exception as ex:
                _LOGGER.error(f"The extension {_extension_path} failed to unload.", exc_info=ex)

        return self

    def reload_extensions(self, extension_path: str, *extension_paths: str):
        """
        Reload an extension (unload then reload), will revert to the previously loaded extension if an error occurs.

        Note
        ----
        There must be a :obj:`loader` function in the file.

        Parameters
        ----------
        extension_path : `str`
            The name of the path to unload. The path must be in the format <directory>.<file> or <directory>/<file>.
            (E.g. `"project.modules.admin"` or `"project/modules/admin"`.)
            Note that any additional slashes or dots are stripped.

        Other Parameters
        ----------------
        extension_paths : `str`
            Addition paths to unload, they must follow the same rules as above.

        Returns
        -------
        :obj:`Bot`
            The instance of the bot to allow for chained calls.
        """
        all_extension_paths = list(extension_paths)
        all_extension_paths.append(extension_path)

        for _extension_path in all_extension_paths:
            if _extension_path not in self._extensions:
                _LOGGER.error(
                    f"The extension {_extension_path} failed to reload because it was not loaded."
                )
            old_extension = sys.modules.pop(_extension_path)
            try:
                extension = importlib.import_module(_extension_path)
                _unloader = None
                _loader = None
                for _, member in inspect.getmembers(extension):
                    if isinstance(member, _UnLoader):
                        _unloader = member
                    if isinstance(member, _Loader):
                        _loader = member

                if not _unloader:
                    raise _MissingUnload
                if not _loader:
                    raise _MissingLoad

                _unloader(self)
                _loader(self)

            except _MissingUnload:
                sys.modules[_extension_path] = old_extension
                _LOGGER.error(
                    f"The extension {_extension_path} failed to reload because no unloader function was found."
                )
            except _MissingLoad:
                sys.modules[_extension_path] = old_extension
                _LOGGER.error(
                    f"The extension {_extension_path} failed to reload because no loader function was found."
                )
            except Exception as ex:
                sys.modules[_extension_path] = old_extension
                _LOGGER.error(f"The extension {_extension_path} failed to reload.", exc_info=ex)

        return self

    def add_module(self):
        ...

    def remove_module(self):
        ...

    def edit_bot(
        self,
        *,
        default_prefix=None,
        mention_prefix=None,
        default_parser=None,
        weak_command_search=None,
        case_insensitive_commands=None,
        case_insensitive_prefixes=None,
        ignore_bots=None,
        owners=None,
        default_embed_colour=None,
    ) -> None:
        # todo instead of this impl, have them all as properties with setters (like in test.py)
        ...
