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

from kousen.hooks import ModuleHooks

if t.TYPE_CHECKING:
    from kousen.commands import MessageCommand
    from kousen.tasks import Task

__all__: list[str] = ["create_listener", "Listener", "Component", "ComponentExtender"]


def create_listener(event_type: Event, *, pass_bot: bool = False):
    return lambda callback: Listener(event_type, callback, pass_bot=pass_bot)


class Listener:

    __slots__ = ("_event_type", "_callback", "_pass_bot")

    def __init__(
        self,
        event_type: Event,
        callback: t.Callable[..., t.Coroutine[None, None, t.Any]],
        *,
        pass_bot=False
    ):
        self._event_type = event_type
        self._callback = callback
        self._pass_bot = pass_bot

    def __call__(self, *args, **kwargs):
        await self._callback(*args, **kwargs)


class Component:

    __slots__ = (
        "_name",
        "_names_to_message_commands",
        "_listeners",
        "_names_to_tasks",
        "_hooks",
        "_cooldowns",
    )

    def __init__(self, *, name: str):
        self._name: str = name
        """The module's name."""
        self._names_to_message_commands: dict[str, MessageCommand] = {}
        """Mapping of message command name against message command object. Note that this does not include aliases."""
        self._listeners: dict[Event, list[Listener]] = {}
        """Mapping of hikari event type against its listener objects."""
        self._names_to_tasks: dict[str, Task] = {}
        """Mapping of task name to task object."""
        self._hooks: ModuleHooks = ModuleHooks()
        self._cooldowns = None  # todo implement cooldowns

    def add_message_command(self):
        ...

    def with_message_command(self):
        ...

    def add_listener(self):
        ...

    def with_listener(self):
        ...

    def add_task(self):
        ...

    def with_task(self):
        ...

    async def load_extender(self):
        # Allow both class and path?
        ...

    async def add_cooldown(self):
        # component level command, using a command in the component will trigger cooldown for all
        ...

    async def set_parser(self):
        # (add to command object)
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

    def _parse_content_for_command(self):
        ...

    def get_command(self, name_or_alias):
        ...


class ComponentExtender:

    __slots__ = ("_message_commands", "_listeners", "_tasks")

    def __init__(self):
        self._message_commands: list[MessageCommand] = []
        """List of extender's message command objects."""
        self._listeners: list[Listener] = []
        """List of extender's listeners."""
        self._tasks: list[Task] = []
        """List of extender's task objects."""

    def add_message_command(self):
        ...

    def with_message_command(self):
        ...

    def add_listener(self):
        ...

    def with_listener(self):
        ...

    def add_task(self):
        ...

    def with_task(self):
        ...

    def set_parser(self):
        # (add to command object)
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
        # Decorate a function to add it as a custom check to component (add to command object)
        ...
