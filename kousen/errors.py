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
import hikari

if t.TYPE_CHECKING:
    from kousen.context import Context
    from kousen.handler import Bot
    from kousen.commands import BaseCommand

__all__: list[str] = ["KousenError", "CheckError", "CommandError", "CommandNotFound"]


class KousenError(Exception):
    """The base exception for all errors raised by Kousen."""

    __slots__ = ()


class CheckError(KousenError):
    """The base exception for all check errors."""

    __slots__ = ("bot", "event", "command")

    def __init__(self, bot, event, command) -> None:
        self.bot: Bot = bot
        self.event: hikari.MessageCreateEvent = event
        self.command: BaseCommand = command


class CommandError(KousenError):
    """Exception for raw errors that occur inside a command."""

    __slots__ = ("context", "raw_error")

    def __init__(self, context, raw_error) -> None:
        self.context: Context = context
        self.raw_error: Exception = raw_error


class CommandNotFound(KousenError):
    """Exception raised when a command could not be found by the name used."""

    __slots__ = ("bot", "event", "name")

    def __init__(self, bot, event, name) -> None:
        self.bot: Bot = bot
        self.event: hikari.MessageCreateEvent = event
        self.name: str = name


class _MissingUnload(Exception):
    ...


class _MissingLoad(Exception):
    ...
