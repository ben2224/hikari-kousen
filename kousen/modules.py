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

if t.TYPE_CHECKING:
    from kousen.commands import Command
    from kousen.events import _Events, Listener
    from kousen.tasks import Task
    from kousen.context import Context

__all__: list[str] = ["Module", "ModuleExtender"]


class _BaseModule:

    __slots__ = ("_commands", "_listeners", "_tasks")

    def __init__(self):
        self._commands: list[Command] = []
        """List of extender's command objects."""
        self._listeners: list[Listener] = []
        """List of extender's listeners."""
        self._tasks: list[Task] = []
        """List of extender's task objects."""

    def add_command(self):
        ...

    def with_command(self):
        ...

    def add_listener(self):
        ...

    def with_listener(self):
        ...

    def add_task(self):
        ...

    def with_task(self):
        ...

    def parse_content_for_command(self):
        ...


class Module:

    __slots__ = (
        "_name",
        "_names_to_commands",
        "_listeners",
        "_names_to_tasks",
        "_checks",
        "_parser",
        "_cooldowns",
        "_error_handler",
    )

    def __init__(self, *, name: str):
        self._name: str = name
        """The module's name."""
        self._names_to_commands: dict[str, Command] = {}
        """Mapping of command name against command object. Note that this does not include aliases."""
        self._listeners: dict[t.Union[Event, _Events], list[Listener]] = {}
        """Mapping of event type against its listeners."""
        self._names_to_tasks: dict[str, Task] = {}
        """Mapping of task name to task object."""
        self._checks: list[t.Callable[[Context], t.Coroutine[None, None, bool]]] = []
        """List of local checks that are applied to all commands in the module."""
        self._parser: t.Optional[str] = None
        self._cooldowns = None  # todo implement cooldowns
        self._error_handler = None  # todo

    def add_command(self):
        ...

    def with_command(self):
        ...

    def add_listener(self):
        ...

    def with_listener(self):
        ...

    def add_task(self):
        ...

    def with_task(self):
        ...

    async def set_parser(self):
        ...

    async def set_error_handler(self):
        ...

    async def load_extender(self):
        # Allow both class and path?
        ...

    async def add_cooldown(self):
        # module level command, using a command in the module will trigger cooldown for all
        ...

    async def add_command_cooldown(self):
        # adds a separate/independent cooldown per command in the module
        ...

    def add_check(self):
        ...

    def add_custom_check(self):
        ...

    def with_custom_check(self):
        # Decorate a function to add it as a custom check to module
        ...

    def _parse_content_for_command(self):
        ...


class ModuleExtender:

    __slots__ = ("_commands", "_listeners", "_tasks")

    def __init__(self):
        self._commands: list[Command] = []
        """List of extender's command objects."""
        self._listeners: list[Listener] = []
        """List of extender's listeners."""
        self._tasks: list[Task] = []
        """List of extender's task objects."""

    def add_command(self):
        ...

    def with_command(self):
        ...

    def add_listener(self):
        ...

    def with_listener(self):
        ...

    def add_task(self):
        ...

    def with_task(self):
        ...
