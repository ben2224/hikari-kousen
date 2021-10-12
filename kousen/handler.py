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
import importlib
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import hikari

from kousen.context import MessageContext, PartialMessageContext
from kousen.colours import Colour
from kousen.errors import _MissingLoad, _MissingUnload, CommandNotFound
from kousen.hooks import dispatch_hooks, Hooks, HookTypes
from kousen._getters import (
    _bool_getter_maker,
    _parser_getter_maker,
    _prefix_getter_maker,
)


if t.TYPE_CHECKING:
    from kousen.components import Component

__all__: list[str] = ["Bot", "loader", "unloader"]

_LOGGER = logging.getLogger("kousen")

PrefixGetterType = t.Callable[[PartialMessageContext], t.Coroutine[None, None, list[str]]]
ParserGetterType = t.Callable[[MessageContext], t.Coroutine[None, None, str]]
BoolGetterType = t.Callable[[PartialMessageContext], t.Coroutine[None, None, bool]]
PrefixArgType = t.Union[
    str,
    t.Iterable[str],
    t.Callable[[PartialMessageContext], t.Coroutine[None, None, t.Union[str, t.Iterable[str]]]],
]
ParserArgType = t.Union[str, ParserGetterType]
BoolArgType = t.Union[bool, BoolGetterType]


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


class Bot(hikari.GatewayBot):
    """The standard implementation of :class:`hikari.impl.bot.GatewayBot` with a command handler.

    Note
    ----
    Mention prefixes will continue to work with message commands after the message content intent becomes privileged.

    Parameters
    ----------
    default_prefix : :obj:`~.handler.PrefixArgType`
        The bot's command prefix.
    mention_prefix : :obj:`bool`
        Whether or not the bot's mention will be used as a prefix. This will be `True` if no default
        prefix is provided, else `False` by default.

    Other Parameters
    ----------------
    default_parser : :obj:`~.handler.ParserArgType`
        The default parser to use for parsing message content for command arguments. Defaults to a whitespace.
        (Note that regardless of this parser, commands and subcommands should always be seperated
        by a whitespace, as this option only affects argument parsing.)
    case_insensitive_commands : :obj:`~.handler.BoolArgType`
        Whether or not commands should be case-insensitive or not. Defaults to `False` (commands are case-sensitive).
    case_insensitive_prefixes : :obj:`~.handler.BoolArgType`
        Whether or not prefixes should be handled as case-insensitive or not.
        Defaults to `False` (prefixes are case-sensitive).
    ignore_bots : :obj:`~.handler.BoolArgType`
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
        "_case_insensitive_commands_getter",
        "_case_insensitive_prefixes_getter",
        "_ignore_bots_getter",
        "_owners",
        "_custom_attributes",
        "_default_embed_colour",
        "_scheduler",
        "_loaded_modules",
        "_names_to_components",
        "_hooks",
    )

    def __init__(
        self,
        *args,
        default_prefix: PrefixArgType = None,
        mention_prefix: bool = None,  # so the default can be different depending on whether a prefix was passed
        default_parser: ParserArgType = " ",
        case_insensitive_commands: BoolArgType = False,
        case_insensitive_prefixes: BoolArgType = False,
        ignore_bots: BoolArgType = True,
        owners: t.Iterable[int] = (),
        default_embed_colour: t.Optional[hikari.Colorish] = Colour.EMBED_BACKGROUND,
        scheduler: AsyncIOScheduler = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        if (cache_settings := kwargs.get("cache_settings")) is not None:
            self._cache_components = cache_settings.components
        else:
            self._cache_components = hikari.CacheComponents.ALL

        if mention_prefix is False and default_prefix is None:
            raise ValueError("No default prefix was provided and mention_prefix was set to False.")

        self._mention_prefixes: list[str] = []
        if mention_prefix is True or default_prefix is None:
            self.subscribe(hikari.StartedEvent, self._setup_mention_prefixes)
        if default_prefix is None:
            default_prefix = []

        self._prefix_getter = _prefix_getter_maker(default_prefix)
        self._default_parser_getter = _parser_getter_maker(default_parser)
        for component in self._names_to_components.values():
            component._set_parser(self._default_parser_getter)
        self._case_insensitive_commands_getter = _bool_getter_maker(
            case_insensitive_commands, name="Case insensitive commands"
        )
        self._case_insensitive_prefixes_getter = _bool_getter_maker(
            case_insensitive_prefixes, name="Case insensitive prefixes"
        )
        self._ignore_bots_getter = _bool_getter_maker(ignore_bots, name="Ignore bots")
        self._owners: list[int] = []
        self.set_owners(owners)

        if isinstance(scheduler, AsyncIOScheduler):
            self._scheduler = scheduler
        else:
            # todo log this
            self._scheduler = AsyncIOScheduler()

        self._custom_attributes: dict[str, t.Any] = {}
        self._default_embed_colour = default_embed_colour
        self._loaded_modules: list[str] = []
        self._names_to_components: dict[str, Component] = {}
        self._hooks: Hooks = Hooks(self, "bot")
        self.subscribe(hikari.MessageCreateEvent, self.on_message_create)

    async def _setup_mention_prefixes(self, _: hikari.StartedEvent) -> None:
        user = self.get_me()
        if user is None:
            user = await self.rest.fetch_my_user()
            # todo implement backoff with fetch
        self._mention_prefixes = [f"<@{user.id}>", f"<@!{user.id}>"]

    def set_default_prefix(self, prefix: PrefixArgType) -> Bot:
        self._prefix_getter = _prefix_getter_maker(prefix)
        return self

    def set_default_parser(self, parser: ParserArgType) -> Bot:
        self._default_parser_getter = _parser_getter_maker(parser)

        for component in self._names_to_components.values():
            component._set_parser(self._default_parser_getter)

        return self

    def set_case_insensitive_commands(self, bool_or_getter: BoolArgType) -> Bot:
        self._case_insensitive_commands_getter = _bool_getter_maker(bool_or_getter, name="Case insensitive commands")
        return self

    def set_case_insensitive_prefixes(self, bool_or_getter: BoolArgType) -> Bot:
        self._case_insensitive_prefixes_getter = _bool_getter_maker(bool_or_getter, name="Case insensitive prefixes")
        return self

    def set_ignore_bots(self, bool_or_getter: BoolArgType) -> Bot:
        self._ignore_bots_getter = _bool_getter_maker(bool_or_getter, name="Ignore bots")
        return self

    def set_owners(self, owners: t.Iterable[t.Union[hikari.User, int]]) -> Bot:
        if not isinstance(owners, t.Iterable):
            raise TypeError(f"Owners must be an iterable, not type {type(owners)}")
        else:
            self._owners.clear()
            for owner in owners:
                if isinstance(owner, hikari.User):
                    self._owners.append(int(owner.id))
                elif isinstance(owner, int):
                    self._owners.append(int(owner))
                else:
                    raise TypeError(f"Owners must be an iterable of hikari users or ints, not of type {type(owner)}")
        return self

    @property
    def scheduler(self) -> AsyncIOScheduler:
        """
        The AsyncIO scheduler instance being used to manage tasks and kousen events.

        Returns
        -------
        :obj:`apscheduler.schedulers.asyncio.AsyncIOScheduler`
            The AsyncioI0 scheduler.
        """
        return self._scheduler

    @property
    def prefix_getter(self) -> PrefixGetterType:
        """
        A getter that returns the prefixes used when checking for prefixes in message content.

        Returns
        -------
        :obj:`~.handler.PrefixGetterType`
            The prefix getter.
        """
        return self._prefix_getter

    @property
    def mention_prefixes(self) -> list[str]:
        """
        The mention prefixes to use as additional prefixes, essentially the bot's mention and nickname mention.

        Returns
        -------
        `list[str]`
            The mention prefixes.
        """
        return self._mention_prefixes

    @property
    def default_parser_getter(self) -> ParserGetterType:
        """
        A getter that returns the default parser
        to use when parsing for args, overwritten by individual component and command parsers.

        Returns
        -------
        :obj:`~.handler.ParserGetterType`
            The parser getter.
        """
        return self._default_parser_getter

    @property
    def case_insensitive_commands_getter(self) -> BoolGetterType:
        """
        A getter that determines whether or not commands are case insensitive.

        Returns
        -------
        :obj:`~.handler.BoolGetterType`
            The case insensitive commands getter.
        """
        return self._case_insensitive_commands_getter

    @property
    def case_insensitive_prefixes_getter(self) -> BoolGetterType:
        """
        A getter that determines whether or not prefixes are case insensitive.

        Returns
        -------
        :obj:`~.handler.BoolGetterType`
            The case insensitive prefixes getter.
        """
        return self._case_insensitive_prefixes_getter

    @property
    def ignore_bots_getter(self) -> BoolGetterType:
        """
        A getter that determines whether or not the bot should invoke commands when a bot sent the message.

        Returns
        -------
        :obj:`~.handler.BoolGetterType`
            The ignore bots getter.
        """
        return self._ignore_bots

    @property
    def owners(self) -> list[int]:
        """
        A list of ids of users who should be treated as owners of the bot.

        Returns
        -------
        `list[int]`
            The owner's user ids.
        """
        return self._owners

    @property
    def default_embed_colour(self) -> t.Optional[hikari.Colorish]:
        """
        The default embed colour used when using :obj:`MessageContext.respond`.

        Returns
        -------
        Optional[`hikari.Colorish`]
            The default embed colour.
        """
        return self._default_embed_colour

    @property
    def modules(self) -> list[str]:
        """
        A list of the currently loaded modules (path names).

        Returns
        -------
        `list[str]`
            The bot's modules.
        """
        return self._loaded_modules

    @property
    def components(self) -> t.Iterable[Component]:
        """
        An iterable of the bot's components.

        Returns
        -------
        `list[str]`
            The bot's components.
        """
        return self._names_to_components.values()

    @property
    def hooks(self) -> Hooks:
        """
        The bot's hooks that have been set.

        Returns
        -------
        :obj:`.hooks.Hooks`
            The bot's hooks.
        """
        return self._hooks

    async def on_message_create(self, event: hikari.MessageCreateEvent):
        if event.content is None:
            return

        partial_context = PartialMessageContext(self, event.message)

        if await self._ignore_bots_getter(partial_context) and not event.is_human:
            return

        prefix: str = ""
        prefixes = await self._prefix_getter(partial_context)
        prefixes.extend(self._mention_prefixes)
        if not prefixes:
            return
        prefixes.sort(key=len, reverse=True)
        content = event.content.lstrip()

        if await self._case_insensitive_prefixes_getter(partial_context):
            for prefix_ in prefixes:
                if content.lower().startswith(prefix_.lower()):
                    prefix = prefix_
        else:
            for prefix_ in prefixes:
                if content.startswith(prefix_):
                    prefix = prefix_

        if not (content := content[len(prefix) :].lstrip()):
            return

        for component in self._names_to_components.values():
            if await component._parse_content_for_command(partial_context, prefix, content):
                return

        dispatch_hooks(
            HookTypes.ERROR,
            self._hooks,
            error=CommandNotFound(partial_context, content.split(" ", maxsplit=1)[0]),
        )
        return

    def __getattr__(self, item):
        if item in self._custom_attributes:
            return self._custom_attributes[item]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

    def add_custom_attribute(self, name: str, attribute_value: t.Any) -> Bot:
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

    def edit_custom_attribute(self, name: str, new_attribute_value: t.Any) -> Bot:
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
            raise ValueError(f"Cannot set new value of '{name}' as there is no custom attribute named '{name}'")
        self._custom_attributes[name] = new_attribute_value
        return self

    def delete_custom_attribute(self, name: str) -> Bot:
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

    def load_modules(self, module_path: str, *module_paths: str):
        """
        Load an external module file into the bot from its path, which can contain components.

        Parameters
        ----------
        module_path : `str`
            The name of the path to load from. The path must be in the format <directory>.<file> or <directory>/<file>.
            (E.g. `"project.components.admin"` or `"project/components/admin"`.)
            Note that any additional slashes or dots are stripped.

        Other Parameters
        ----------------
        module_paths : `str`
            Addition paths to load from, they must follow the same rules as above.

        Examples
        --------
        In order for this to work, the module must have a function decorated with :obj:`loader` that takes
        one positional argument of type :obj:`Bot`

        .. code-block:: python
            import kousen

            admin_component = kousen.Component(...)

            ...

            @kousen.loader
            def admin_loader(bot: kousen.Bot):
                bot.add_component(admin_component)

        Returns
        -------
        :obj:`Bot`
            The instance of the bot to allow for chained calls.
        """
        all_module_paths = list(module_paths)
        all_module_paths.append(module_path)
        for _module_path in all_module_paths:
            _module_path.replace("/", ".").strip(".")
            if _module_path in self._loaded_modules:
                _LOGGER.error(f"The module {_module_path} failed to load because it was already loaded.")
            try:
                _module = importlib.import_module(_module_path)
                for _, member in inspect.getmembers(_module):
                    if isinstance(member, _Loader):
                        member(self)
                        self._loaded_modules.append(_module_path)
                        _LOGGER.info(f"module {_module_path} was successfully loaded.")
                        break
                else:
                    _LOGGER.error(f"The module {_module_path} failed to load because no loader function was found.")
            except Exception as ex:
                _LOGGER.error(f"The module {_module_path} failed to load.", exc_info=ex)

        return self

    def unload_modules(self, module_path: str, *module_paths: str):
        """
        Unload an module.

        Note
        ----
        There must be a :obj:`loader` function in the file.

        Parameters
        ----------
        module_path : `str`
            The name of the path to reload. The path must be in the format <directory>.<file> or <directory>/<file>.
            (E.g. `"project.components.admin"` or `"project/components/admin"`.)
            Note that any additional slashes or dots are stripped.

        Other Parameters
        ----------------
        module_paths : `str`
            Addition paths to reload, they must follow the same rules as above.

        Returns
        -------
        :obj:`Bot`
            The instance of the bot to allow for chained calls.
        """
        all_module_paths = list(module_paths)
        all_module_paths.append(module_path)
        for _module_path in all_module_paths:
            _module_path.replace("/", ".").strip(".")
            if _module_path not in self._loaded_moduless:
                _LOGGER.error(f"The module {_module_path} failed to unload because it was not loaded.")
            try:
                _module = importlib.import_module(_module_path)
                for _, member in inspect.getmembers(_module):
                    if isinstance(member, _UnLoader):
                        member(self)
                        self._loaded_moduless.remove(_module_path)
                        sys.modules.pop(_module_path)
                        _LOGGER.info(f"module {_module_path} was successfully unloaded.")
                        break
                else:
                    _LOGGER.error(f"The module {_module_path} failed to unload because no unloader function was found.")
            except Exception as ex:
                _LOGGER.error(f"The module {_module_path} failed to unload.", exc_info=ex)

        return self

    def reload_modules(self, module_path: str, *module_paths: str):
        """
        Reload an module (unload then reload), will revert to the previously loaded module if an error occurs.

        Note
        ----
        There must be a :obj:`loader` function in the file.

        Parameters
        ----------
        module_path : `str`
            The name of the path to unload. The path must be in the format <directory>.<file> or <directory>/<file>.
            (E.g. `"project.components.admin"` or `"project/components/admin"`.)
            Note that any additional slashes or dots are stripped.

        Other Parameters
        ----------------
        module_paths : `str`
            Addition paths to unload, they must follow the same rules as above.

        Returns
        -------
        :obj:`Bot`
            The instance of the bot to allow for chained calls.
        """
        all_module_paths = list(module_paths)
        all_module_paths.append(module_path)

        for _module_path in all_module_paths:
            if _module_path not in self._loaded_moduless:
                _LOGGER.error(f"The module {_module_path} failed to reload because it was not loaded.")
            old_module = sys.modules.pop(_module_path)
            try:
                module = importlib.import_module(_module_path)
                _unloader = None
                _loader = None
                for _, member in inspect.getmembers(module):
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
                sys.modules[_module_path] = old_module
                _LOGGER.error(f"The module {_module_path} failed to reload because no unloader function was found.")
            except _MissingLoad:
                sys.modules[_module_path] = old_module
                _LOGGER.error(f"The module {_module_path} failed to reload because no loader function was found.")
            except Exception as ex:
                sys.modules[_module_path] = old_module
                _LOGGER.error(f"The module {_module_path} failed to reload.", exc_info=ex)

        return self

    def add_component(self, component: Component) -> Bot:
        if component in self._names_to_components.values():
            return self  # todo raise error

        self._names_to_components[component._name] = component
        component._set_bot(self)
        component._set_parser(self._default_parser_getter)

        dispatch_hooks(
            HookTypes.COMPONENT_ADDED,
            bot_hooks=self._hooks,
            component_hooks=component._hooks,
        )

        return self

    def remove_component(self, component_name: str) -> Bot:
        if component_name not in self._names_to_components:
            return self  # todo raise error

        component = self._names_to_components.pop(component_name)
        dispatch_hooks(
            HookTypes.COMPONENT_ADDED,
            bot_hooks=self._hooks,
            component_hooks=component._hooks,
        )
        component._set_bot(None)

        return self

    def find_command(self):
        ...

    def get_component(self):
        ...
