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
import typing as t
import re
import hikari

from kousen.hooks import HookManager, dispatch_hooks, HookTypes
from kousen.errors import CheckError, CommandError

if t.TYPE_CHECKING:
    from kousen.components import Component
    from kousen.context import MessageContext, SlashContext, Context

__all__: list[str] = [
    "as_command",
    "create_command_group",
    "as_subcommand",
    "create_subcommand_group",
    "Command",
    "CommandGroup",
    "SubCommand",
    "SubCommandGroup",
    "CommandType",
    "SubCommandType",
    "CommandGroupType",
]


def as_command(
    name: str, description: str, *, message_only: bool = False, slash_only: bool = False
) -> t.Callable[[t.Callable], "Command"]:
    def decorate(func: t.Callable):
        cmd = Command(
            callback=func,
            name=str(name),
            description=str(description),
            slash_only=slash_only,
            message_only=message_only,
        )
        return cmd

    return decorate


def create_command_group(
    name: str, description: str, *, message_only: bool = False, slash_only: bool = False
) -> "CommandGroup":
    return CommandGroup(
        callback=NotImplemented,
        name=str(name),
        description=str(description),
        slash_only=slash_only,
        message_only=message_only,
    )


def as_subcommand(name: str, description: str) -> t.Callable[[t.Callable], "SubCommand"]:
    def decorate(func: t.Callable):
        cmd = SubCommand(callback=func, name=str(name), description=str(description))
        return cmd

    return decorate


def create_subcommand_group(name: str, description: str) -> "SubCommandGroup":
    return SubCommandGroup(callback=NotImplemented, name=str(name), description=str(description))


class BaseCommand:

    __slots__ = (
        "_callback",
        "_name",
        "_description",
        "_component",
        "_checks",
        "_hooks",
    )

    def __init__(
        self,
        *,
        callback: t.Callable[[Context, t.Any], t.Coroutine],
        name: str,
        description: str,
    ) -> None:
        if not re.match(r"^[a-z0-9_-]{1,32}$", str(name)):
            raise  # todo log error
        if len(description) > 100:
            raise  # todo log error
        self._callback: t.Callable[[Context, t.Any], t.Coroutine] = callback
        self._name: str = name
        self._description = description
        self._component: t.Optional[Component] = None
        self._checks = NotImplemented  # todo
        self._hooks: HookManager = HookManager(self, "command")

    def _set_component(self, component: Component) -> BaseCommand:
        self._component = component
        return self

    @property
    def callback(self) -> t.Callable[[Context, t.Any], t.Coroutine]:
        return self._callback

    @property
    def name(self) -> str:
        return self._name

    @property
    def full_name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def checks(self):
        return self._checks

    @property
    def hooks(self) -> HookManager:
        return self._hooks

    @property
    def component(self) -> t.Optional[Component]:
        return self._component

    async def slash_invoke(self, context: SlashContext, args: tuple[t.Any], kwargs: dict[str, t.Any]):
        ...

    async def message_invoke(self, context: MessageContext, args: tuple[t.Any], kwargs: dict[str, t.Any]):
        ...


class Command(BaseCommand):

    __slots__ = ("_parser", "_slash_parser", "_impl_message", "_impl_slash", "_app_command")

    def __init__(
        self,
        *,
        callback: t.Callable[[Context, t.Any], t.Coroutine],
        name: str,
        description: str,
        message_only: bool,
        slash_only: bool,
    ) -> None:
        super().__init__(callback=callback, name=name, description=description)
        if message_only and slash_only:
            raise  # todo log error
        self._impl_message = False if slash_only else True
        self._impl_slash = False if message_only else True

        self._parser = NotImplemented  # TODO tbd
        self._slash_parser = NotImplemented  # TODO tbd
        self._app_command: t.Optional[hikari.Command] = None

    async def slash_invoke(self, context: SlashContext, args: tuple[t.Any], kwargs: dict[str, t.Any]):
        ...

    async def message_invoke(self, context: MessageContext, args: tuple[t.Any], kwargs: dict[str, t.Any]):
        assert self._component is not None
        assert self._component._bot is not None
        comp = self._component
        bot = self._component._bot
        # todo cooldowns
        try:
            ...
            # todo run checks here
        except CheckError as ex:
            if dispatch_hooks(
                HookTypes.CHECK_ERROR,
                bot._hooks,
                component_hooks=comp._hooks,
                command_hooks=self._hooks,
                error=ex,
            ):
                return
            else:
                raise ex  # todo use logger error instead of raise
        try:
            await self._callback(context, *args, **kwargs)
        except Exception as ex:
            exp = CommandError(context, ex)
            if dispatch_hooks(
                HookTypes.ERROR,
                bot._hooks,
                component_hooks=comp._hooks,
                command_hooks=self._hooks,
                error=exp,
            ):
                return
            else:
                raise exp  # todo use logger error instead of raise


class CommandGroup(BaseCommand):

    __slots__ = ("_impl_message", "_impl_slash", "_names_to_subcommands", "_app_command")

    def __init__(
        self,
        *,
        callback: t.Callable[[Context, t.Any], t.Coroutine],
        name: str,
        description: str,
        message_only: bool,
        slash_only: bool,
    ) -> None:
        super().__init__(callback=callback, name=name, description=description)
        if message_only and slash_only:
            raise  # todo log error
        self._impl_message = False if slash_only else True
        self._impl_slash = False if message_only else True
        self._names_to_subcommands: dict[str, SubCommandType] = {}
        self._app_command: t.Optional[hikari.Command] = None

    def _set_component(self, component: Component) -> CommandGroup:
        self._component = component
        for command in self._names_to_subcommands.values():
            command._set_component(component)
        return self

    def get_subcommand(self, name_or_alias) -> t.Optional[SubCommandType]:
        return self._names_to_subcommands.get(name_or_alias, None)

    def walk_subcommands(self) -> t.Iterator[SubCommandType]:
        for command in self._names_to_subcommands.values():
            yield command

    def add_subcommand(self, command: SubCommandType) -> CommandGroup:
        if command.name in self._names_to_subcommands:
            raise ValueError(f"Cannot add command {command.name} as there is already a sub-command by that name.")

        self._names_to_subcommands[command._name] = command

        command._parent = self
        if self._component:
            command._set_component(self._component)
        return self

    def with_subcommand(self, command: SubCommandType) -> None:
        self.add_subcommand(command)
        return

    def with_message_callback(self, func) -> CommandGroup:
        self._callback = func
        return self

    async def message_invoke(self, context: MessageContext, args: tuple[t.Any], kwargs: dict[str, t.Any]):
        ...


class SubCommand(BaseCommand):

    __slots__ = (
        "_parent",
        "_parser",
        "_slash_parser",
    )

    def __init__(
        self,
        *,
        callback: t.Callable[[Context, t.Any], t.Coroutine],
        name: str,
        description: str,
    ) -> None:
        super().__init__(callback=callback, name=name, description=description)

        self._parent: CommandGroupType = NotImplemented
        self._parser = NotImplemented  # TODO tbd
        self._slash_parser = NotImplemented  # TODO tbd

    @property
    def full_name(self) -> str:
        full_name = []
        cmd: t.Any = self
        while not isinstance(cmd, CommandGroup):
            full_name.append(cmd._name)
            cmd = cmd._parent
        full_name.reverse()
        return " ".join(full_name)

    @property
    def parent(self) -> CommandGroupType:
        return self._parent

    async def slash_invoke(self, context: SlashContext, args: tuple[t.Any], kwargs: dict[str, t.Any]):
        ...

    async def message_invoke(self, context: MessageContext, args: tuple[t.Any], kwargs: dict[str, t.Any]):
        ...


class SubCommandGroup(BaseCommand):

    __slots__ = (
        "_parent",
        "_names_to_subcommands",
    )

    def __init__(
        self,
        *,
        callback: t.Callable[[Context, t.Any], t.Coroutine],
        name: str,
        description: str,
    ) -> None:
        super().__init__(callback=callback, name=name, description=description)

        self._parent: CommandGroupType = NotImplemented
        self._names_to_subcommands: dict[str, SubCommandType] = {}

    def _set_component(self, component: Component) -> SubCommandGroup:
        self._component = component
        for command in self._names_to_subcommands.values():
            command._set_component(component)
        return self

    def get_subcommand(self, name_or_alias) -> t.Optional[SubCommandType]:
        return self._names_to_subcommands.get(name_or_alias, None)

    def walk_subcommands(self) -> t.Iterator[SubCommandType]:
        for command in self._names_to_subcommands.values():
            yield command

    def add_subcommand(self, command: SubCommandType) -> SubCommandGroup:
        if command.name in self._names_to_subcommands:
            raise ValueError(f"Cannot add command {command.name} as there is already a sub-command by that name.")

        self._names_to_subcommands[command._name] = command

        command._parent = self
        if self._component:
            command._set_component(self._component)
        return self

    def with_subcommand(self, command: SubCommandType) -> None:
        self.add_subcommand(command)
        return None

    def with_message_callback(self, func) -> SubCommandGroup:
        self._callback = func
        return self

    @property
    def full_name(self) -> str:
        full_name = []
        cmd: t.Any = self
        while not isinstance(cmd, CommandGroup):
            full_name.append(cmd._name)
            cmd = cmd._parent
        full_name.reverse()
        return " ".join(full_name)

    @property
    def parent(self) -> CommandGroupType:
        return self._parent

    async def message_invoke(self, context: MessageContext, args: tuple[t.Any], kwargs: dict[str, t.Any]):
        ...


CommandType = t.Union[Command, CommandGroup]
SubCommandType = t.Union[SubCommand, SubCommandGroup]
CommandGroupType = t.Union[SubCommandGroup, CommandGroup]
