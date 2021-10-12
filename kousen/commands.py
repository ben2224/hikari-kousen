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

from kousen.hooks import Hooks, dispatch_hooks, HookTypes
from kousen.errors import CheckError, CommandError
from kousen._getters import _parser_getter_maker
from kousen.parsing import parse_content_for_args

if t.TYPE_CHECKING:
    from kousen.components import Component
    from kousen.handler import ParserGetterType, ParserArgType

__all__: list[str] = [
    "MessageCommand",
    "create_message_command",
    "MessageCommandGroup",
    "create_message_command_group",
]


def create_message_command(
    name: str,
    *,
    aliases: t.Optional[t.Iterable[str]] = None,
    parser: t.Optional[str] = None,
):
    def decorate(func):
        cmd = MessageCommand(callback=func, name=name, aliases=aliases, parser=parser)
        return cmd

    return decorate


def create_message_command_group(
    name: str,
    *,
    aliases: t.Optional[t.Iterable[str]] = None,
    parser: t.Optional[str] = None,
) -> t.Callable[[t.Callable], "MessageCommandGroup"]:
    def decorate(func: t.Callable):
        cmd = MessageCommandGroup(callback=func, name=name, aliases=aliases, parser=parser)
        return cmd

    return decorate


class MessageCommand:
    __slots__ = (
        "_callback",
        "_name",
        "_aliases",
        "_parent",
        "_global_parser",
        "_custom_parser",
        "_component",
        "_checks",
        "_hooks",
    )

    def __init__(
        self,
        *,
        callback,
        name: str,
        aliases: t.Optional[t.Iterable[str]] = None,
        parser: t.Optional[ParserArgType] = None,
    ) -> None:
        self._callback = callback
        self._name: str = name
        self._aliases: list[str] = []
        if aliases:
            self._aliases.extend(list(*map(str, aliases)))
        self._parent: t.Optional[MessageCommandGroup] = None
        self._custom_parser: t.Optional[ParserGetterType] = _parser_getter_maker(parser) if parser else None
        self._global_parser: t.Optional[ParserGetterType] = None
        self._component: t.Optional[Component] = None
        self._checks: list = []
        self._hooks: Hooks = Hooks(self, "command")

    def _set_parent(self, parent: t.Optional[MessageCommandGroup]) -> MessageCommand:
        self._parent = parent
        return self

    def _set_parser(self, parser: ParserGetterType) -> MessageCommand:
        self._global_parser = parser
        return self

    def _set_component(self, component: Component) -> MessageCommand:
        self._component = component
        return self

    @property
    def callback(self):
        return self._callback

    @property
    def name(self):
        return self._name

    @property
    def full_name(self):
        full_name = []
        cmd = self
        while cmd is not None:
            full_name.append(cmd._name)
            cmd = cmd._parent
        full_name.reverse()
        return " ".join(full_name)

    @property
    def aliases(self) -> list[str]:
        return self._aliases

    @property
    def parent(self) -> t.Optional[MessageCommandGroup]:
        return self._parent

    @property
    def is_subcommand(self) -> bool:
        return self._parent is not None

    @property
    def parser(self) -> t.Optional[ParserGetterType]:
        return self._custom_parser or self._global_parser

    @property
    def checks(self):
        return self._checks

    @property
    def hooks(self) -> Hooks:
        return self._hooks

    @property
    def cooldown(self):
        return None  # todo impl

    @property
    def component(self) -> t.Optional[Component]:
        return self._component

    def _parse_content_for_args(self, content: str) -> tuple[tuple[t.Any], dict[str, t.Any]]:
        return parse_content_for_args(self, content)

    async def invoke(self, context, args, kwargs):
        comp = self._component
        # todo cooldowns
        try:
            ...
            # todo run checks here
        except CheckError as ex:
            if dispatch_hooks(
                HookTypes.CHECK_ERROR,
                comp._bot._hooks,
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
                comp._bot._hooks,
                component_hooks=comp._hooks,
                command_hooks=self._hooks,
                error=exp,
            ):
                return
            else:
                raise exp  # todo use logger error instead of raise


class MessageCommandGroup(MessageCommand):
    __slots__ = ("_names_to_commands", "_aliases_to_commands")

    def __init__(
        self,
        *,
        callback,
        name: str,
        aliases: t.Optional[t.Iterable[str]] = None,
        parser: t.Optional[ParserArgType] = None,
    ) -> None:
        super().__init__(callback=callback, name=name, aliases=aliases, parser=parser)
        self._names_to_commands: dict[str, MessageCommand] = {}
        self._aliases_to_commands: dict[str, MessageCommand] = {}

    def _set_parser(self, parser: ParserGetterType) -> MessageCommand:
        self._global_parser = parser
        for command in self._names_to_commands.values():
            command._set_parser(parser)
        return self

    def _set_component(self, component: Component) -> MessageCommand:
        self._component = component
        for command in self._names_to_commands.values():
            command._set_component(component)
        return self

    def get_command(self, name_or_alias) -> t.Optional[MessageCommand]:
        return self._aliases_to_commands.get(name_or_alias, None)

    def walk_sub_commands(self) -> t.Iterator[MessageCommand]:
        for command in self._names_to_commands.values():
            yield command

    def add_command(self, command: MessageCommand) -> MessageCommandGroup:
        if command.name in self._names_to_commands:
            raise ValueError(f"Cannot add command {command.name} as there is already a sub-command by that name.")

        self._names_to_commands[command._name] = command
        self._aliases_to_commands[command._name] = command
        for alias in command._aliases:
            self._aliases_to_commands[alias] = command

        command._set_parent(self)
        if self._component:
            command._set_component(self._component)
        if self._custom_parser:
            command._set_parser(self._custom_parser)
        elif self._global_parser:
            command._set_parser(self._global_parser)
        return self

    def with_command(self, command: MessageCommand) -> MessageCommand:
        self.add_command(command)
        return command
