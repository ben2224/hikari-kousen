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
import asyncio
import logging
import inspect
from hikari.internal.enums import Enum

from kousen.utils import _await_if_async

if t.TYPE_CHECKING:
    from kousen.handler import Bot
    from kousen.components import Component
    from kousen.commands import MessageCommand

__all__: list[str] = [
    "HookTypes",
    "Hooks",
]

_LOGGER = logging.getLogger("kousen.hooks")


class HookTypes(str, Enum):
    ERROR = "error"
    CHECK_ERROR = "check_error"

    PRE_INVOKE = "pre_invoke"
    POST_INVOKE = "post_invoke"
    COMMAND_SUCCESS = "command_success"

    COMPONENT_ADDED = "component_added"
    COMPONENT_REMOVED = "component_removed"


_component_only_hooks = ("component_added", "component_removed")


def dispatch_hooks(
    hook_type: HookTypes,
    bot_hooks: "Hooks",
    *,
    component_hooks: t.Optional["Hooks"] = None,
    command_hooks: t.Optional["Hooks"] = None,
    **kwargs: t.Any,
) -> bool:
    """
    Method used by kousen to dispatch all the hooks for that hook type taking into account component/command local overwrites.

    Parameters
    ----------
    hook_type : :obj:`.hooks.HookTypes`
        The hook type to dispatch.
    bot_hooks : :obj:`.hooks.Hooks`
        The bot's hooks.
    component_hooks : Optional[:obj:`.hooks.Hooks`]
        The component's hooks which overwrites the bot's hooks.
    command_hooks : Optional[:obj:`.hooks.Hooks`]
        The command's hooks which overwrites both the bot's and component's hooks. (Not relevant for non-command related
        hooks)
    **kwargs : dict[`str`, `Any`]
        The args to be passed into the hook callback, e.g. error= or context=

    Returns
    -------
    :obj:`bool`
        True if any hooks were dispatched, false if there were no set hooks.
    """
    return asyncio.wait_for(
        _dispatch_hooks(hook_type, bot_hooks, component_hooks, command_hooks, **kwargs), timeout=None
    ).result()


async def _dispatch_hooks(hook_type, bot_hooks, component_hooks, command_hooks, **kwargs) -> bool:
    if command_hooks:
        if await command_hooks.dispatch(hook_type, **kwargs):
            return True
    if component_hooks:
        if await component_hooks.dispatch(hook_type, **kwargs):
            return True
    if await bot_hooks.dispatch(hook_type, **kwargs):
        return True
    return False


class Hooks:

    __slots__ = ("_all_hooks", "_instance", "_type")

    def __init__(
        self, instance: t.Union[Component, Bot, MessageCommand], _type: t.Literal["bot", "component", "command"]
    ):
        self._all_hooks: dict[HookTypes, list[t.Callable]] = {}
        self._instance: t.Union[Component, Bot, MessageCommand] = instance
        self._type: t.Literal["bot", "component", "command"] = _type

    async def dispatch(self, hook_type: HookTypes, **kwargs) -> bool:
        """
        Method used to dispatch all the hook callables for that hook type.

        Parameters
        ----------
        hook_type : :obj:`.hooks.HookTypes`
            The hook type to dispatch.

        Returns
        -------
        :obj:`bool`
            True if any hooks were dispatched, false if there were no set hooks.
        """
        if hook_callables := self._all_hooks.get(hook_type):
            for callable_ in hook_callables:
                await _await_if_async(callable_, *(kwargs.values()))
            return True
        return False

    def with_hook_callback(self, hook_type: HookTypes):
        def decorate(func: t.Callable):
            self.add_hook_callback(hook_type, func)
            return func

        return decorate

    def add_hook_callback(self, hook_type: HookTypes, callback: t.Callable) -> "Hooks":
        error_msg = f"Failed to add hook callback '{callback}' to '{self._instance}' as "
        if not isinstance(hook_type, HookTypes):
            _LOGGER.error(error_msg + f"'{hook_type}' is not a valid hook type.")
            return self

        in_comp = hook_type.value in _component_only_hooks
        if self._type == "command" and in_comp:
            _LOGGER.error(error_msg + f"the hook type '{hook_type}' cannot be used with commands")
            return self

        params = len(inspect.signature(callback).parameters)
        if in_comp and params != 2:
            _LOGGER.error(error_msg + f"it takes {params} args when 2 will be passed.")
            return self
        if params != 1:
            _LOGGER.error(error_msg + f"it takes {params} args when 1 will be passed.")
            return self

        if hook_type in self._all_hooks:
            self._all_hooks[hook_type].append(callback)
        else:
            self._all_hooks[hook_type] = [callback]

        _LOGGER.debug(f"Added '{hook_type.name}' hook callback '{callback}' to '{self._instance}'.")
        return self
