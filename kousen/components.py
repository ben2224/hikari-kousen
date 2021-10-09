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

from kousen.hooks import ComponentHooks
from kousen.context import MessageContext
from kousen.commands import MessageCommand

if t.TYPE_CHECKING:
    from kousen.context import PartialMessageContext
    from kousen.tasks import Task
    from kousen.handler import Bot

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
        pass_bot=False,
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
        "_bot",
        "_custom_parser",
        "_global_parser"
    )

    def __init__(self, *, name: str, parser: t.Optional[str] = None):
        self._name: str = name
        """The module's name."""
        self._names_to_message_commands: dict[str, MessageCommand] = {}
        """Mapping of message command name against message command object. Note that this does not include aliases."""
        self._listeners: dict[Event, list[Listener]] = {}
        """Mapping of hikari event type against its listener objects."""
        self._names_to_tasks: dict[str, Task] = {}
        """Mapping of task name to task object."""
        self._hooks: ComponentHooks = ComponentHooks()
        self._cooldowns = None  # todo implement cooldowns
        self._bot: t.Optional[Bot] = None
        self._custom_parser: t.Optional[str] = parser
        self._global_parser: t.Optional[str] = None

    def _set_bot(self, bot: t.Optional[Bot]) -> Component:
        self._bot = bot
        return self

    def _set_parser(self, parser: str):  # todo make a getter
        self._global_parser = parser
        if not self._custom_parser:
            for command in self._names_to_message_commands.values():
                command._set_parser(parser)

    def add_message_command(self, command: MessageCommand) -> Component:
        if command.name in self._names_to_message_commands:
            raise ValueError(
                f"Cannot add command {command.name} as there is already a command by that name."
            )  # todo for things like this use logger not error

        self._names_to_message_commands[command.name] = command
        command._set_component(self)
        command._set_parser(self._custom_parser or self._global_parser)
        return self

    def with_message_command(self, command: MessageCommand) -> MessageCommand:
        self.add_message_command(command)
        return command

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

    async def _parse_content_for_command(
        self, partial_context: PartialMessageContext, prefix: str, content: str
    ) -> bool:
        name = content.split(" ", maxsplit=1)[0]
        if not (command := self.get_command(name)):
            return False

        args, kwargs = command._parse_content_for_args(content)
        context = MessageContext._create_from_partial_context(
            partial_context, prefix, name, command, content
        )

        await command.invoke(context, args, kwargs)
        return True

    def get_command(self, name_or_alias: str) -> t.Optional[MessageCommand]:
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
