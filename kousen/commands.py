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

from kousen.hooks import CommandHooks

if t.TYPE_CHECKING:
    from kousen.components import Component

__all__: list[str] = ["MessageCommand", "create_message_command", "MessageCommandGroup", "create_message_command_group"]


def create_message_command():
    ...


def create_message_command_group():
    ...


class MessageCommand:
    __slots__ = ("_callback", "_name", "_aliases", "_parent", "_custom_parser", "_component", "_checks", "_hooks")

    def __init__(self, *, callback, name: str, aliases: t.Optional[list[str]] = None, component: Component) -> None:
        self._callback = callback
        self._name: str = name
        self._aliases: list[str] = list(map(str, aliases))
        self._parent: t.Optional[MessageCommandGroup] = None
        self._custom_parser: t.Optional[str] = None
        self._component: Component = component
        self._checks: list = []
        self._hooks: CommandHooks = CommandHooks()

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
    def parser(self) -> t.Optional[str]:
        return self._custom_parser

    @property
    def checks(self):
        return self._checks

    @property
    def hooks(self) -> CommandHooks:
        return self._hooks

    @property
    def cooldown(self):
        return None  # todo impl

    @property
    def component(self) -> Component:
        return self._component

    def set_parent(self, parent: t.Optional[MessageCommandGroup]) -> MessageCommand:
        self._parent = parent
        return self

    def set_parser(self, parser: str) -> MessageCommand:
        self._custom_parser = parser
        return self

    def parse_content_for_args(self, content: str):
        ...

    def invoke(self):
        ...


class MessageCommandGroup(MessageCommand):
    __slots__ = ("_names_to_commands",)

    def __init__(self, *, callback, name: str, aliases: t.Optional[list[str]] = None, component: Component) -> None:
        super().__init__(callback=callback, name=name, aliases=aliases, component=component)
        self._names_to_commands: dict[str, MessageCommand] = {}

    @property
    def commands(self) -> list[MessageCommand]:
        return list(self._names_to_commands.values())

    def add_command(self, command: MessageCommand) -> MessageCommandGroup:
        if command.name in self._names_to_commands:
            raise ValueError(f"Cannot add command {command.name} as there is already a sub-command by that name.")

        self._names_to_commands[command.name] = command
        command.set_parent(self)
        return self

    def remove_command(self, command_name: str) -> MessageCommandGroup:
        command = self._names_to_commands.pop(command_name)
        command.set_parent(None)
        return self

    def with_command(self, command):
        ...
