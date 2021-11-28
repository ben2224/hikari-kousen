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
from hikari.events import Event

from kousen.hooks import HookManager
from kousen.commands import CommandType

if t.TYPE_CHECKING:
    from kousen.tasks import Task
    from kousen.listeners import Listener
    from kousen.handler import Bot

__all__: list[str] = ["Component"]


class Component:

    __slots__ = (
        "_name",
        "_names_to_commands",
        "_listeners",
        "_names_to_tasks",
        "_hooks",
        "_hook_names_added_to_bot",
        "_bot",
    )

    def __init__(self, *, name: str):
        self._name: str = name
        """The module's name."""
        self._names_to_commands: dict[str, CommandType] = {}
        """Mapping of command names against command objects."""
        self._listeners: dict[Event, list[Listener]] = {}
        """Mapping of hikari event type against its listener objects."""
        self._names_to_tasks: dict[str, Task] = {}
        """Mapping of task name to task object."""
        self._hooks: HookManager = HookManager(self, "component")
        self._hook_names_added_to_bot: list[str] = []
        self._bot: t.Optional[Bot] = None

    @property
    def hooks(self) -> HookManager:
        return self._hooks

    def _set_bot(self, bot: t.Optional[Bot]) -> Component:
        self._bot = bot
        return self

    def add_hook_callback_to_bot(self):
        ...  # waits until bot exists then adds to hooks, as connected to component before component is loaded
        # also need to store somewhere to remove from bot when removing component from the bot

    def add_command(self, command: CommandType) -> Component:
        if command.name in self._names_to_commands:
            raise ValueError(
                f"Cannot add command {command.name} as there is already a command by that name."
            )  # todo for things like this use logger not error

        self._names_to_commands[command.name] = command
        command._set_component(self)
        return self

    def with_command(self, command: CommandType) -> None:
        self.add_command(command)
        return

    def get_command(self, name: str) -> t.Optional[CommandType]:
        return self._names_to_commands.get(name, None)

    def add_listener(self):
        ...

    def with_listener(self):
        ...

    def add_task(self):
        ...

    def with_task(self):
        ...

    async def add_cooldown(self):
        # component level command, using a command in the component will trigger cooldown for all
        ...

    async def add_command_cooldown(self):
        # adds a separate/independent cooldown per command in the component (add to command object)
        ...

    def add_check(self):
        # (add to command object)
        ...

    def add_custom_check(self):
        # (add to command object)
        ...

    def with_custom_check(self):
        # Decorate a function to add it as a custom check to component
        ...
