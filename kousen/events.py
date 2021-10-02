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
import typing as t
from hikari.internal.enums import Enum
from hikari.events import Event

__all__: list[str] = ["GeneralEvents", "Listener", "create_listener"]


def create_listener(event_type, *, pass_bot=False):
    return lambda callback: Listener(event_type, callback, pass_bot=pass_bot)


class Listener:

    __slots__ = ("_event_type", "_callback", "_pass_bot")

    def __init__(
        self,
        event_type: t.Union[Event, "_Events"],
        callback: t.Callable[..., t.Coroutine[None, None, t.Any]],
        *,
        pass_bot=False
    ):
        self._event_type = event_type
        self._callback = callback
        self._pass_bot = pass_bot

    def __call__(self, *args, **kwargs):
        await self._callback(*args, **kwargs)


class _Events(str, Enum):
    ...


class GeneralEvents(_Events):
    MODULE_ADDED = "module_added"
    # todo add more
