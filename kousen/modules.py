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

__all__: list[str] = ["Module", "ModuleExtender"]


class _BaseModule:

    __slots__ = ()

    async def add_command(self):
        ...

    async def create_command(self):
        ...

    async def add_listener(self):
        ...

    async def create_listener(self):
        ...

    async def add_task(self):
        ...

    async def create_task(self):
        ...

    async def add_check(self):
        ...


class Module(_BaseModule):

    __slots__ = ()

    async def set_parser(self):
        ...

    async def set_error_handler(self):
        ...

    async def load_extender(self):
        ...

    async def add_cooldown(self):
        ...

    async def add_command_cooldown(self):
        ...


class ModuleExtender(_BaseModule):

    __slots__ = ()
