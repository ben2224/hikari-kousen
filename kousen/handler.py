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
import asyncio

from kousen.errors import _MissingLoad, _MissingUnload, CommandNotFound
from kousen.hooks import dispatch_hooks, HookManager, HookType
from kousen.context import MessageContext, SlashContext
from kousen._getters import (
    _bool_getter_maker,
    _prefix_getter_maker,
)

if t.TYPE_CHECKING:
    from kousen.components import Component
    from kousen.commands import CommandGroup, SubCommandGroup, BaseCommand, CommandType

__all__: list[str] = ["Bot", "loader", "unloader"]

_LOGGER = logging.getLogger("kousen")

PrefixGetterType = t.Callable[["Bot", hikari.MessageCreateEvent], t.Coroutine[None, None, list[str]]]
BoolGetterType = t.Callable[["Bot", hikari.MessageCreateEvent], t.Coroutine[None, None, bool]]
PrefixArgType = t.Union[
    str,
    t.Iterable[str],
    t.Callable[
        ["Bot", hikari.MessageCreateEvent],
        t.Coroutine[None, None, t.Union[str, t.Iterable[str]]],
    ],
]
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
        "_msg_setup_run",
        "_slash_setup_run",
        "_prefix_getter",
        "_default_parser_getter",
        "_case_insensitive_commands_getter",
        "_case_insensitive_prefixes_getter",
        "_default_slash_guilds",
        "_delete_commands_when_message_only",
        "_delete_commands_when_stopping",
        "_owners",
        "_custom_attributes",
        "_loaded_modules",
        "_names_to_components",
        "_hooks",
        "_application",
        "_names_to_commands",
        "_commands_to_commands",
        "_message_commands_only",
        "_slash_commands_only",
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if (cache_settings := kwargs.get("cache_settings")) is not None:
            self._cache_components = cache_settings.components
        else:
            self._cache_components = hikari.api.config.CacheComponents.ALL

        self._mention_prefixes: list[str] = []
        self.__mention_prefixes: list[str] = []  # so i dont have to re-get/fetch the user which won't change
        self.subscribe(hikari.StartingEvent, self._starting_event)
        self.subscribe(hikari.StartedEvent, self._setup_on_started)
        self.subscribe(hikari.StoppingEvent, self._delete_commands_on_stopping)
        self._started = False
        self._msg_setup_run = False
        self._slash_setup_run = False
        self.subscribe(hikari.MessageCreateEvent, self.on_message_create)
        self.subscribe(hikari.InteractionCreateEvent, self.on_interaction_create)

        self._prefix_getter: PrefixGetterType = NotImplemented
        self._case_insensitive_commands_getter: BoolGetterType = NotImplemented
        self._case_insensitive_prefixes_getter: BoolGetterType = NotImplemented

        self._default_slash_guilds: [list[int]] = []
        self._delete_commands_when_message_only: bool = True
        self._delete_commands_when_stopping: bool = True

        self._owners: list[int] = []
        self._custom_attributes: dict[str, t.Any] = {}
        self._loaded_modules: list[str] = []
        self._names_to_components: dict[str, Component] = {}
        self._hooks: HookManager = HookManager(self, "bot")
        self._application: hikari.Application = NotImplemented

        self._names_to_commands: dict[str, CommandType] = {}
        self._commands_to_commands: dict[CommandType, list[hikari.SlashCommand]] = {}
        self._message_commands_only: bool = False
        self._slash_commands_only: bool = False

    async def _setup_on_started(self, _) -> None:
        user = self.get_me()
        if user is None:
            try:
                user = await self.rest.fetch_my_user()
            except hikari.HikariError:
                pass
        if user:
            if self.__mention_prefixes:  # will have an item if setup_message_commands was called before starting
                self._mention_prefixes = [f"<@{user.id}>", f"<@!{user.id}>"]
            self.__mention_prefixes = [f"<@{user.id}>", f"<@!{user.id}>"]
        else:
            ...  # todo raise logger error

        await self.delete_all_slash_commands()

        self._application = await self.rest.fetch_application()
        self._started = True

    async def _delete_commands_on_stopping(self, _) -> None:
        if self._delete_commands_when_stopping:
            await self.delete_all_slash_commands()

    async def _starting_event(self, _) -> None:
        if not self._msg_setup_run:
            self.setup_message_commands()
        if not self._slash_setup_run:
            self.setup_slash_commands()

    def setup_message_commands(
        self,
        *,
        use_mention_prefixes: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        prefix: hikari.UndefinedOr[t.Optional[PrefixArgType]] = hikari.UNDEFINED,
        case_insensitive_commands: hikari.UndefinedOr[BoolArgType] = hikari.UNDEFINED,
        case_insensitive_prefixes: hikari.UndefinedOr[BoolArgType] = hikari.UNDEFINED,
        message_commands_only: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
    ) -> Bot:
        """
        Setup a custom configuration for message commands. This will be called automatically if it was not called
        before the bot was started, therefore using the default config (see defaults below). If a custom
        config is needed, this should be called before starting/running the bot. However, this can
        be run at any time to change the config.

        For slash command configuration see :obj:`~.handler.Bot.setup_slash_commands`.

        Notes
        ----
        Mention prefixes continue to work despite the message content intent becoming privileged. If you want
        message commands but do not have the intent then no prefix needs to be passed, mention prefixes will be used.

        If a prefix was not previously set and is not passed, then use_mention_prefixes cannot be previously
        set to False, or passed as False. The bot must eiter use mention prefixes or a custom set prefix.

        Parameters
        ----------
        use_mention_prefixes : :obj:`bool`
            Whether or not the bot's mention will be used as a message command prefix. Defaults to `True`.
        prefix : Optional[:obj:`~.handler.PrefixArgType`]
            The bot's message command prefix. (Will be stripped of leading spaces but not trailing, as a trailing space
            may be useful.)
        case_insensitive_commands : :obj:`~.handler.BoolArgType`
            Whether or not commands should be case-insensitive or not. Defaults to `False`.
        case_insensitive_prefixes : :obj:`~.handler.BoolArgType`
            Whether or not prefixes should be handled as case-insensitive or not.
            Defaults to `False`.
        message_commands_only : `bool`
            Whether or not the bot should be message commands only. This can be set at any time and will prevent slash
            commands from working. Note that this can be overwritten by setting slash commands only to `True`.
            Defaults to `False`.

        Returns
        -------
        :obj:`Bot`
            The instance of the bot to allow for chained calls.

        Raises
        ------
        ValueError
            If there is no prefix set or passed and use_mention_prefixes was set to False.
        """

        if message_commands_only is not hikari.UNDEFINED:
            self._message_commands_only = bool(message_commands_only)
            if message_commands_only:
                self._slash_commands_only = False
                if self._delete_commands_when_message_only and self._started:
                    await self.delete_all_slash_commands()

        if not prefix and not self._prefix_getter and not use_mention_prefixes and not self._mention_prefixes:
            raise ValueError(
                "Prefix was set to None or no prefix was previously set and mention prefixes were set to "
                "False, either a prefix must be passed or use_mention_prefixes should not be False."
            )

        if use_mention_prefixes is True or use_mention_prefixes is hikari.UNDEFINED:
            if self._started:
                self._mention_prefixes = self.__mention_prefixes
            else:
                self._mention_prefixes = [""]  # will be added on startup if this is called before bot is ran
        elif use_mention_prefixes is False:
            self._mention_prefixes = []

        if prefix is not hikari.UNDEFINED:
            self._prefix_getter = _prefix_getter_maker(prefix if prefix is not None else [])

        if case_insensitive_commands is not hikari.UNDEFINED:
            self._case_insensitive_commands_getter = _bool_getter_maker(
                case_insensitive_commands, name="Case insensitive commands"
            )
        else:
            if not self._case_insensitive_commands_getter:
                self._case_insensitive_commands_getter = _bool_getter_maker(False, name="Case insensitive commands")

        if case_insensitive_prefixes is not hikari.UNDEFINED:
            self._case_insensitive_prefixes_getter = _bool_getter_maker(
                case_insensitive_prefixes, name="Case insensitive prefixes"
            )
        else:
            if not self._case_insensitive_prefixes_getter:
                self._case_insensitive_prefixes_getter = _bool_getter_maker(False, name="Case insensitive prefixes")

        self._msg_setup_run = True
        return self

    def setup_slash_commands(
        self,
        *,
        default_slash_guilds: hikari.UndefinedOr[t.Union[
            hikari.PartialGuild,
            int,
            t.Iterable[t.Union[hikari.PartialGuild, int]]]] = hikari.UNDEFINED,
        delete_commands_when_message_only: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        delete_commands_when_stopping: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        slash_commands_only: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
    ) -> Bot:
        """
        Setup a custom configuration for slash commands. This will be called automatically if it was not called
        before the bot was started, therefore using the default config (see defaults below). If a custom config
        is needed, this should be called before starting/running the bot. However, this can
        be run at any time to change the config.

        For message command configuration see :obj:`~.handler.Bot.setup_message_commands`.

        Parameters
        ----------
        default_slash_guilds : Union[`hikari.PartialGuild`, `int`, Iterable[Union[`hikari.PartialGuild`, `int`]]]
            The guilds that slash commands should be declared in, if not provided then slash commands will be
            declared globally and work in all guilds. This is useful for testing/development as it may take up to
            and hour to propagate global slash commands, but guild specific commands will propagate instantly.
        delete_commands_when_message_only : `bool`
            Whether or not the bot should delete slash commands from discord when the bot is set to message commands
            only, else an interaction failure will occur for users. (i.e. They are deleted when message_commands_only
            is set to `True` in :obj:`.handler.Bot.setup_message_commands`). Defaults to `True`.
        delete_commands_when_stopping : `bool`
            Whether or not the bot should delete slash commands from discord when the bot stopping. Defaults to `True`.
            Warning - if this is set to false and different default guild ids are passed when run again
            there will be unbound commands in guilds that the bot cannot delete on startup (as it doesn't know what the
            old guilds are).
        slash_commands_only : `bool`
            Whether or not the bot should be slash commands only. This can be set at any time and will prevent message
            commands from working. Note that this can be overwritten by setting message commands only to `True`.
            Defaults to `False`.

        Returns
        -------
        :obj:`Bot`
            The instance of the bot to allow for chained calls.

        Raises
        ------
        TypeError
            Incorrect type for default enabled guilds is passed.
        """

        if slash_commands_only is not hikari.UNDEFINED:
            self._slash_commands_only = bool(slash_commands_only)
            if slash_commands_only:
                self._message_commands_only = False

        current_default_guilds = self._default_slash_guilds
        self._default_slash_guilds.clear()

        if default_slash_guilds is not hikari.UNDEFINED:
            if isinstance(default_slash_guilds, int):
                self._default_slash_guilds.append(default_slash_guilds)
            elif isinstance(default_slash_guilds, hikari.PartialGuild):
                self._default_slash_guilds.append(int(default_slash_guilds.id))
            elif isinstance(default_slash_guilds, t.Iterable):
                guilds = []
                for guild in default_slash_guilds:
                    if isinstance(guild, int):
                        guilds.append(default_slash_guilds)
                    elif isinstance(guild, hikari.PartialGuild):
                        guild.append(int(guild.id))
                    else:
                        raise TypeError(
                            f"Default enabled guilds must be a guild object, an integer or an iterable of such, not an"
                            f"iterable of type{type(guild)}."
                        )
                self._default_slash_guilds.append(guilds)
            else:
                raise TypeError(
                        f"Default enabled guilds must be a guild object, an integer or an iterable of such, "
                        f"not of type {type(default_slash_guilds)}."
                    )

        old_guilds = [guild for guild in current_default_guilds if guild not in self._default_slash_guilds]
        if old_guilds:
            await self.delete_all_slash_commands(old_guilds)

        if delete_commands_when_message_only is not hikari.UNDEFINED:
            self._delete_commands_when_message_only = bool(delete_commands_when_message_only)

        if delete_commands_when_stopping is not hikari.UNDEFINED:
            self._delete_commands_when_stopping = bool(delete_commands_when_stopping)

        self._slash_setup_run = True
        return self

    def set_owners(self, owners: t.Union[t.Iterable[t.Union[hikari.PartialUser, int]], int]) -> Bot:
        assert isinstance(self._owners, list)
        self._owners.clear()
        if isinstance(owners, t.Iterable):
            owners_ = []
            for owner in owners:
                if isinstance(owner, hikari.PartialUser):
                    owners_.append(int(owner.id))
                elif isinstance(owner, int):
                    owners_.append(owner)
                else:
                    raise TypeError(f"Owners must be an iterable of hikari users or ints, not an iterable "
                                    f"of type {type(owner)}.")
                self._owners = owners
        elif isinstance(owners, int):
            self._owners.append(owners)
        else:
            raise TypeError(f"Owners must be an iterable, not type {type(owners)}.")
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

    async def on_interaction_create(self, event: hikari.InteractionCreateEvent) -> None:
        if self._message_commands_only:
            return

        ...

    async def on_message_create(self, event: hikari.MessageCreateEvent) -> None:
        if self._slash_commands_only:
            return

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

        if not (content := content[len(prefix):].lstrip()):
            return

        name = content.split(" ", maxsplit=1)[0]
        for component in self._names_to_components.values():
            command: t.Any
            if command := component.get_command(name):
                while isinstance(command, (CommandGroup, SubCommandGroup)):
                    if cmd := command.get_subcommand(new_name := name.split(" ", maxsplit=1)[0]):
                        name = new_name
                        command = cmd
                        break
                assert isinstance(command, BaseCommand)
                args, kwargs = NotImplemented  # TODO tbd
                context = MessageContext(
                    bot=self,
                    event=event,
                    prefix=prefix,
                    invoking_name=name,
                    command=command,
                )

                await command.invoke(context, args, kwargs)

        else:
            dispatch_hooks(HookType.ERROR, self._hooks, error=CommandNotFound(self, event, name))

        return

    async def create_slash_command(self, command: BaseCommand) -> list[hikari.SlashCommand]:
        options = command._build_options()
        if self._default_slash_guilds:
            commands = []
            for guild in self._default_slash_guilds:
                app_command = await self.rest.create_slash_command(
                    application=self._application,
                    name=command._name,
                    description=command._description,
                    guild=guild,
                    options=options,
                    dm_enabled=command._dm_enabled
                )
                commands.append(app_command)
            return commands
        else:
            global_command = await self.rest.create_slash_command(
                application=self._application,
                name=command._name,
                description=command._description,
                options=options,
                dm_enabled=command._dm_enabled
            )
        return [global_command]

    async def delete_all_slash_commands(self, guilds: t.Optional[t.Iterable[t.Union[hikari.PartialGuild, int]]] = None) -> None:
        if guilds:
            for guild in guilds:
                await self.rest.set_application_commands(self.application, (), guild)
        elif self._default_slash_guilds:
            for guild_id in self._default_slash_guilds:
                await self.rest.set_application_commands(self.application, (), guild_id)
        else:
            await self.rest.set_application_commands(self.application, ())

    async def delete_slash_commands(self, commands: t.Iterable[hikari.SlashCommand]):
        default_enabled_guilds = self._default_slash_guilds
        if not default_enabled_guilds:
            default_enabled_guilds.append(hikari.UNDEFINED)

        for guild in default_enabled_guilds:
            for command in commands:
                await self.rest.delete_application_command(
                    application=self._application,
                    command=command,
                    guild=guild
                )

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
        if not name.isidentifier():
            raise ValueError(f"Failed to add the bot attribute '{name}', as it is not a valid identifier.")
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
            raise ValueError(f"Failed to set new value of '{name}' as there is no custom attribute named '{name}'")
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

    def add_all_components_in_file(self):
        ...  # todo parse file for component and add to bot

    def add_component(self, component: Component, create_slash_commands: bool = True) -> Bot:
        if component in self._names_to_components.values():
            return self  # todo raise error

        self._names_to_components[component._name] = component
        for name, command in component._names_to_commands:
            if command._impl_message:
                if name in self._names_to_commands:
                    raise  # todo raise error
                self._names_to_commands[name] = command
            if command._impl_slash and create_slash_commands:
                task = asyncio.create_task(self.create_slash_command(command))
                while not task.done():
                    pass
                if task.exception():
                    raise task.exception()
                self._commands_to_commands[task.result()] = command

        for hook_type, hook in component._hooks_added_to_bot:
            self._hooks._names_to_hooks[hook.name] = hook
            if hook_type in self._hooks._types_to_hooks:
                self._hooks._types_to_hooks[hook_type].append(hook)
            else:
                self._hooks._types_to_hooks[hook_type] = [hook]

        component._set_bot(self)

        return self

    def remove_component(self, component_name: str, delete_slash_commands: bool = True) -> Bot:
        if component_name not in self._names_to_components:
            return self  # todo raise error

        component = self._names_to_components.pop(component_name)
        for hook_name in component._hooks_added_to_bot:
            self._hooks.remove_hook(hook_name)
        # todo delete slash commands

        component._set_bot(None)

        return self

    def get_component(self):
        ...

    def find_command(self):
        ...
