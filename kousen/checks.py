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
from abc import ABC, abstractmethod

if t.TYPE_CHECKING:
    from kousen.context import Context

__all__: list[str] = []


class AbstractCheck(ABC):
    __slots__ = ()

    @abstractmethod
    def check(self, context: Context) -> bool:
        """check

        Parameters
        ----------
        context : :obj:`~Context`
            The context to check against.

        Returns
        -------
        :obj:`bool`
            Returns `True` if the check passes.

        Raises
        ------
        :obj:`~CheckError`
            If the check fails.
        """

    @abstractmethod
    def check_without_error(self, context: Context) -> bool:
        """check

        Parameters
        ----------
        context : :obj:`~Context`
            The context to check against.

        Returns
        -------
        :obj:`bool`
            Returns `True` if the check passes and `False` if the check fails.
        """
