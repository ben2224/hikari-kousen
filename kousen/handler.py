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
import hikari

from kousen.context import MessageContext
from kousen.errors import _MissingLoad, _MissingUnload, CommandNotFound
from kousen.hooks import dispatch_hooks, HookManager, HookTypes
from kousen._getters import (
    _bool_getter_maker,
    _parser_getter_maker,
    _prefix_getter_maker,
)


if t.TYPE_CHECKING:
    from kousen.components import Component

__all__: list[str] = ["Bot", "loader", "unloader"]

_LOGGER = logging.getLogger("kousen")

PrefixGetterType = t.Callable[
    ["Bot", hikari.MessageCreateEvent], t.Coroutine[None, None, list[str]]
]
ParserGetterType = t.Callable[[MessageContext], t.Coroutine[None, None, str]]
BoolGetterType = t.Callable[
    ["Bot", hikari.MessageCreateEvent], t.Coroutine[None, None, bool]
]
PrefixArgType = t.Union[
    str,
    t.Iterable[str],
    t.Callable[
        ["Bot", hikari.MessageCreateEvent],
        t.Coroutine[None, None, t.Union[str, t.Iterable[str]]],
    ],
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
    """
    The standard implementation of :obj:`hikari.impl.bot.GatewayBot` with a command handler.

    See :obj:`~.handler.Bot.setup_message_commands` and :obj:`~.handler.Bot.setup_slash_commands` for more information
    on setting up config for commands. If these are not used, both message and slash commands will work with the
    default config (see functions for more details), it is advised that they are called before starting.
    """

    __slots__ = (
        "_cache_components",
        "_mention_prefixes",
        "__mention_prefixes",
        "_started",
        "_setup_run",
        "_prefix_getter",
        "_default_parser_getter",
        "_case_insensitive_commands_getter",
        "_case_insensitive_prefixes_getter",
        "_owners",
        "_custom_attributes",
        "_loaded_modules",
        "_names_to_components",
        "_hooks",
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if (cache_settings := kwargs.get("cache_settings")) is not None:
            self._cache_components = cache_settings.components
        else:
            self._cache_components = hikari.CacheComponents.ALL

        self._mention_prefixes: list[str] = []
        self.__mention_prefixes: list[
            str
        ] = []  # so i dont have to re-get/fetch the user which won't change
        self.subscribe(hikari.StartingEvent, self._starting_event)
        self.subscribe(hikari.StartedEvent, self._setup_mention_prefixes_on_started)
        self._started = False
        self._setup_run = False
        self.subscribe(hikari.MessageCreateEvent, self.on_message_create)

        self._prefix_getter: PrefixGetterType = NotImplemented
        self._default_parser_getter: ParserGetterType = NotImplemented
        self._case_insensitive_commands_getter: BoolGetterType = NotImplemented
        self._case_insensitive_prefixes_getter: BoolGetterType = NotImplemented

        self._owners: list[int] = []
        self._custom_attributes: dict[str, t.Any] = {}
        self._loaded_modules: list[str] = []
        self._names_to_components: dict[str, Component] = {}
        self._hooks: HookManager = HookManager(self, "bot")

    async def _setup_mention_prefixes_on_started(self, _) -> None:
        user = self.get_me()
        if user is None:
            try:
                user = await self.rest.fetch_my_user()
                # todo implement backoff with fetch
            except hikari.HikariError:
                pass
        if user:
            if (
                self.__mention_prefixes
            ):  # will have an item if setup_message_commands was called before starting
                self._mention_prefixes = [f"<@{user.id}>", f"<@!{user.id}>"]
            self.__mention_prefixes = [f"<@{user.id}>", f"<@!{user.id}>"]
        else:
            ...  # todo raise logger error
        self._started = True

    async def _starting_event(self, _) -> None:
        if not self._setup_run:
            self.setup_message_commands()
            self.setup_slash_commands()

    def setup_message_commands(
        self,
        *,
        use_mention_prefixes: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        prefix: hikari.UndefinedOr[t.Optional[PrefixArgType]] = hikari.UNDEFINED,
        default_parser: hikari.UndefinedOr[ParserArgType] = hikari.UNDEFINED,
        case_insensitive_commands: hikari.UndefinedOr[BoolArgType] = hikari.UNDEFINED,
        case_insensitive_prefixes: hikari.UndefinedOr[BoolArgType] = hikari.UNDEFINED,
        message_commands_only: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
    ) -> Bot:
        """
        Setup a custom configuration for message commands. This will be called automatically if it was not called
        before the bot was started, therefore using the default config. If a custom config is needed, this should
        be called before starting/running the bot. However, this can be run at any time to change the config.

        For slash command configuration see :obj:`~.handler.Bot.setup_slash_commands`.

        Notes
        ----
        Mention prefixes will continue to work after the message content intent becomes privileged. If you want
        message commands but do not have the intent then no prefix needs to be passed, mention prefixes will be used.

        If a prefix was not previously set and is not passed, then use_mention_prefixes cannot be previously
        set to False, or passed as False. The bot must eiter use mention prefixes or a custom set prefix.

        Parameters
        ----------
        use_mention_prefixes : :obj:`bool`
            Whether or not the bot's mention will be used as a message command prefix. Defaults to `True`.
        prefix : Optional[:obj:`~.handler.PrefixArgType`]
            The bot's message command prefix.
        default_parser : :obj:`~.handler.ParserArgType`
            The default parser to use for parsing message content for message command arguments. Defaults to a
            whitespace. (Note that regardless of this parser, commands and subcommands should always be seperated
            by a whitespace, as this option only affects argument parsing.)
        case_insensitive_commands : :obj:`~.handler.BoolArgType`
            Whether or not commands should be case-insensitive or not. Defaults to `False`.
        case_insensitive_prefixes : :obj:`~.handler.BoolArgType`
            Whether or not prefixes should be handled as case-insensitive or not.
            Defaults to `False`.
        message_commands_only : `bool`
            Whether or not the bot should be message commands only. This can be set at any time and will unregister
            and delete any existing slash commands. Note that this can be overwritten by setting slash commands only.

        Returns
        -------
        :obj:`Bot`
            The instance of the bot to allow for chained calls.

        Raises
        ------
        ValueError
            If there is no prefix set or passed and use_mention_prefixes was set to False.
        """

        if (
            not prefix
            and not self._prefix_getter
            and not use_mention_prefixes
            and not self._mention_prefixes
        ):
            raise ValueError(
                "Prefix was set to None or no prefix was previously set and mention prefixes were set to "
                "False, either a prefix must be passed or use_mention_prefixes should not be False."
            )

        if use_mention_prefixes is True or use_mention_prefixes is hikari.UNDEFINED:
            if self._started:
                self._mention_prefixes = self.__mention_prefixes
            else:
                self._mention_prefixes = [
                    ""
                ]  # will be added on startup if this is called before bot is ran
        elif use_mention_prefixes is False:
            self._mention_prefixes = []

        if prefix is not hikari.UNDEFINED:
            self._prefix_getter = _prefix_getter_maker(
                prefix if prefix is not None else []
            )

        if default_parser is not hikari.UNDEFINED:
            self._default_parser_getter = _parser_getter_maker(default_parser)
        else:
            if not self._default_parser_getter:
                self._default_parser_getter = _parser_getter_maker(" ")
        for component in self._names_to_components.values():
            component._set_parser(self._default_parser_getter)

        if case_insensitive_commands is not hikari.UNDEFINED:
            self._case_insensitive_commands_getter = _bool_getter_maker(
                case_insensitive_commands, name="Case insensitive commands"
            )
        else:
            if not self._case_insensitive_commands_getter:
                self._case_insensitive_commands_getter = _bool_getter_maker(
                    False, name="Case insensitive commands"
                )

        if case_insensitive_prefixes is not hikari.UNDEFINED:
            self._case_insensitive_prefixes_getter = _bool_getter_maker(
                case_insensitive_prefixes, name="Case insensitive prefixes"
            )
        else:
            if not self._case_insensitive_prefixes_getter:
                self._case_insensitive_prefixes_getter = _bool_getter_maker(
                    False, name="Case insensitive prefixes"
                )

        self._setup_message_commands_only(
            message_commands_only
            if message_commands_only is not hikari.UNDEFINED
            else False
        )

        self._setup_run = True
        return self

    def setup_slash_commands(self):
        ...

    def _setup_message_commands_only(self, make_only: bool):
        ...  # todo

    def _setup_slash_commands_only(self):
        ...

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
                    raise TypeError(
                        f"Owners must be an iterable of hikari users or ints, not of type {type(owner)}"
                    )
        return self

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
    def hooks(self) -> HookManager:
        """
        The bot's hooks that have been set.

        Returns
        -------
        :obj:`.hooks.HookManager`
            The bot's hooks.
        """
        return self._hooks

    async def on_message_create(self, event: hikari.MessageCreateEvent):
        if event.content is None:
            return

        prefix: str = ""
        prefixes = await self._prefix_getter(self, event)
        prefixes.extend(self._mention_prefixes)
        if not prefixes:
            return
        prefixes.sort(key=len, reverse=True)
        content = event.content.lstrip()

        if await self._case_insensitive_prefixes_getter(self, event):
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
            if await component._parse_content_for_command(self, event, prefix, content):
                return

        dispatch_hooks(
            HookTypes.ERROR,
            self._hooks,
            error=CommandNotFound(self, event, content.split(" ", maxsplit=1)[0]),
        )
        return

    def __getattr__(self, item):
        if item in self._custom_attributes:
            return self._custom_attributes[item]
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{item}'"
        )

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
            raise ValueError(
                f"Cannot set new value of '{name}' as there is no custom attribute named '{name}'"
            )
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
        # todo allow path objects, and load from all files in a dir
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
                _LOGGER.error(
                    f"The module {_module_path} failed to load because it was already loaded."
                )
            try:
                _module = importlib.import_module(_module_path)
                for _, member in inspect.getmembers(_module):
                    if isinstance(member, _Loader):
                        member(self)
                        self._loaded_modules.append(_module_path)
                        _LOGGER.info(f"module {_module_path} was successfully loaded.")
                        break
                else:
                    _LOGGER.error(
                        f"The module {_module_path} failed to load because no loader function was found."
                    )
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
                _LOGGER.error(
                    f"The module {_module_path} failed to unload because it was not loaded."
                )
            try:
                _module = importlib.import_module(_module_path)
                for _, member in inspect.getmembers(_module):
                    if isinstance(member, _UnLoader):
                        member(self)
                        self._loaded_moduless.remove(_module_path)
                        sys.modules.pop(_module_path)
                        _LOGGER.info(
                            f"module {_module_path} was successfully unloaded."
                        )
                        break
                else:
                    _LOGGER.error(
                        f"The module {_module_path} failed to unload because no unloader function was found."
                    )
            except Exception as ex:
                _LOGGER.error(
                    f"The module {_module_path} failed to unload.", exc_info=ex
                )

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
                _LOGGER.error(
                    f"The module {_module_path} failed to reload because it was not loaded."
                )
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
                _LOGGER.error(
                    f"The module {_module_path} failed to reload because no unloader function was found."
                )
            except _MissingLoad:
                sys.modules[_module_path] = old_module
                _LOGGER.error(
                    f"The module {_module_path} failed to reload because no loader function was found."
                )
            except Exception as ex:
                sys.modules[_module_path] = old_module
                _LOGGER.error(
                    f"The module {_module_path} failed to reload.", exc_info=ex
                )

        return self

    def add_all_components_in_file(self):
        ...  # todo parse file for component and add to bot

    def add_component(self, component: Component) -> Bot:
        if component in self._names_to_components.values():
            return self  # todo raise error

        self._names_to_components[component._name] = component
        component._set_bot(self)
        component._set_parser(self._default_parser_getter)

        if self._is_alive:
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
        for hook_name in component._hook_names_added_to_bot:
            self._hooks.remove_hook(hook_name)

        if self._is_alive:
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
