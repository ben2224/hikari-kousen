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
import abc

from kousen.hooks import HookManager
from kousen.parsing import ParserManager

if t.TYPE_CHECKING:
    from kousen.components import Component
    from kousen.context import Context
    from kousen.checks import CheckManager
    from kousen.cooldowns import CooldownManager

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


def as_command(name: str, description: str, *, message_only: bool = False, slash_only: bool = False, use_slash_parser: bool = False) -> t.Callable[[t.Callable], "Command"]:
    def decorate(func: t.Callable):
        cmd = Command(
            callback=func,
            name=str(name),
            description=str(description),
            slash_only=slash_only,
            message_only=message_only,
            use_slash_parser=use_slash_parser
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


def as_subcommand(name: str, description: str, use_slash_parser: bool = False) -> t.Callable[[t.Callable], "SubCommand"]:
    def decorate(func: t.Callable):
        cmd = SubCommand(callback=func, name=str(name), description=str(description), use_slash_parser=use_slash_parser)
        return cmd

    return decorate


def create_subcommand_group(name: str, description: str) -> "SubCommandGroup":
    return SubCommandGroup(callback=NotImplemented, name=str(name), description=str(description))


class BaseCommand(abc.ABC):

    __slots__ = (
        "_callback",
        "_name",
        "_description",
        "_component",
        "_cooldown_manager",
        "_check_manager",
        "_hook_manager",
        "_parser",
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
        if len(description) > 100 or len(description) < 1:
            raise  # todo log error
        self._callback: t.Callable[[Context, t.Any], t.Coroutine] = callback
        self._name: str = name
        self._description = description
        self._component: t.Optional[Component] = None
        self._cooldown_manager: t.Optional[CooldownManager] = None
        self._check_manager: t.Optional[CheckManager] = None
        self._hook_manager: HookManager = HookManager(self, "command")
        self._parser: ParserManager = ParserManager()

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
    def component(self) -> t.Optional[Component]:
        return self._component

    @property
    def hooks(self) -> HookManager:
        return self._hook_manager

    @abc.abstractmethod
    async def invoke(self, context: Context, args: tuple[t.Any], kwargs: dict[str, t.Any]):
        ...


class Command(BaseCommand):

    __slots__ = ("_impl_message", "_impl_slash", "_use_slash_parser", "_app_command")

    def __init__(
        self,
        *,
        callback: t.Callable[[Context, t.Any], t.Coroutine],
        name: str,
        description: str,
        message_only: bool,
        slash_only: bool,
        use_slash_parser: bool = False
    ) -> None:
        super().__init__(callback=callback, name=name, description=description)
        if message_only and slash_only:
            raise  # todo log error
        self._impl_message = False if slash_only else True
        self._impl_slash = False if message_only else True

        self._use_slash_parser = use_slash_parser
        self._app_command: t.Optional[hikari.Command] = None

    async def invoke(self, context: Context, args: tuple[t.Any], kwargs: dict[str, t.Any]):
        ...


class CommandGroup(BaseCommand):

    __slots__ = (
        "_impl_message",
        "_impl_slash",
        "_names_to_subcommands",
        "_app_command",
    )

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

    def get_subcommand(self, name) -> t.Optional[SubCommandType]:
        return self._names_to_subcommands.get(name, None)

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

    async def invoke(self, context: Context, args: tuple[t.Any], kwargs: dict[str, t.Any]):
        ...


class SubCommand(BaseCommand):

    __slots__ = (
        "_parent",
        "_use_slash_parser"
    )

    def __init__(
        self,
        *,
        callback: t.Callable[[Context, t.Any], t.Coroutine],
        name: str,
        description: str,
        use_slash_parser: bool = False
    ) -> None:
        super().__init__(callback=callback, name=name, description=description)

        self._parent: CommandGroupType = NotImplemented
        self._use_slash_parser = use_slash_parser

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

    async def invoke(self, context: Context, args: tuple[t.Any], kwargs: dict[str, t.Any]):
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
        self._names_to_subcommands: dict[str, SubCommand] = {}

    def _set_component(self, component: Component) -> SubCommandGroup:
        self._component = component
        for command in self._names_to_subcommands.values():
            command._set_component(component)
        return self

    def get_subcommand(self, name) -> t.Optional[SubCommand]:
        return self._names_to_subcommands.get(name, None)

    def walk_subcommands(self) -> t.Iterator[SubCommand]:
        for command in self._names_to_subcommands.values():
            yield command

    def add_subcommand(self, command: SubCommand) -> SubCommandGroup:
        if command.name in self._names_to_subcommands:
            raise ValueError(f"Cannot add command {command.name} as there is already a sub-command by that name.")

        self._names_to_subcommands[command._name] = command

        command._parent = self
        if self._component:
            command._set_component(self._component)
        return self

    def with_subcommand(self, command: SubCommand) -> None:
        self.add_subcommand(command)
        return

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

    async def invoke(self, context: Context, args: tuple[t.Any], kwargs: dict[str, t.Any]):
        ...


CommandType = t.Union[Command, CommandGroup]
SubCommandType = t.Union[SubCommand, SubCommandGroup]
CommandGroupType = t.Union[SubCommandGroup, CommandGroup]
