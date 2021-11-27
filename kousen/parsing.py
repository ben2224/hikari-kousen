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
from hikari.internal.enums import Enum

if t.TYPE_CHECKING:
    ...

__all__: list[str] = ["Option", "ParserManager", "with_option"]


class OptionType(int, Enum):
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    MENTIONABLE = 9
    FLOAT = 10


class Option:

    __slots__ = ("_name", "_description", "_option_type", "_converter", "_default")

    def __init__(self, name: str, description: str, option_type: OptionType, converter, default: t.Any = hikari.UNDEFINED):
        if not re.match(r"^[a-z0-9_-]{1,32}$", str(name)):
            raise  # todo log error
        if len(description) > 100 or len(description) < 1:
            raise  # todo log error
        if not isinstance(option_type, OptionType):
            raise  # todo log error
        self._name: str = name
        self._description: str = description
        self._option_type: OptionType = option_type
        self._converter = converter
        self._default: t.Any = default

    def convert(self, original) -> t.Any:
        ...


class ParserManager:

    __slots__ = ("_names_to_options",)

    def __init__(self):
        self._names_to_options: dict[str, Option] = {}

    def convert_from_string(self, text: str) -> dict[str, t.Any]:
        # returns mapping of option name to the converted value
        ...

    def convert_from_options(self, *options) -> dict[str, t.Any]:
        ...


def with_option(
    name: str,
    description: str,
    *,
    option_type: OptionType = OptionType.STRING,
    converter=None,
    default: t.Any = hikari.UNDEFINED
):
    ...
