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
import functools
import inspect

if t.TYPE_CHECKING:
    from kousen.handler import (
        PrefixArgType,
        PrefixGetterType,
        BoolArgType,
        BoolGetterType,
        ParserArgType,
        ParserGetterType,
    )


async def _getter(_, return_obj):
    return return_obj


async def _getter_with_callback(ctx, callback, type_):
    getter_result = await callback(ctx)

    if type_ == "prefix":
        if isinstance(getter_result, str):
            return [getter_result]
        if isinstance(getter_result, t.Iterable):
            list1 = list(*map(str, getter_result))
            return list1
        else:
            raise TypeError(
                f"Prefix getter must return a string or iterable of strings, not type {type(getter_result)}"
            )  # todo use log error

    if type_ == "parser":
        if isinstance(getter_result, str):
            return getter_result
        else:
            raise TypeError(
                f"Parser getter must return a string, not type {type(getter_result)}"
            )

    if type_ == "bool":
        if isinstance(getter_result, str):
            return getter_result
        else:
            raise TypeError(
                f"Bool getter must return a bool, not type {type(getter_result)}"
            )  # todo more specific


def _prefix_getter_maker(prefix: PrefixArgType) -> PrefixGetterType:
    if isinstance(prefix, str):
        return functools.partial(_getter, return_object=[prefix])

    elif isinstance(prefix, t.Iterable):
        prefix_list: list[str] = list(*map(str, prefix))
        return functools.partial(_getter, return_object=prefix_list)

    elif inspect.iscoroutinefunction(prefix):
        return functools.partial(_getter_with_callback, callback=prefix, type_="prefix")

    else:
        raise TypeError(
            f"Prefix must be either a string, or iterable of strings, or a coroutine, not type "
            f"{type(prefix)}"
        )


def _bool_getter_maker(obj_: BoolArgType, name: str) -> BoolGetterType:
    if isinstance(obj_, bool):
        return functools.partial(_getter, return_object=obj_)

    elif inspect.iscoroutinefunction(obj_):
        return functools.partial(_getter_with_callback, callback=obj_, type_="bool")
    else:
        raise TypeError(
            f"{name} arg must be either a bool or a coroutine, not type {type(obj_)}"
        )


def _parser_getter_maker(parser: ParserArgType) -> ParserGetterType:
    if isinstance(parser, str):
        return functools.partial(_getter, return_object=parser)

    elif inspect.iscoroutinefunction(parser):
        return functools.partial(_getter_with_callback, callback=parser, type_="parser")
    else:
        raise TypeError(
            f"Parser arg must be either a string or a coroutine, not type {type(parser)}"
        )
