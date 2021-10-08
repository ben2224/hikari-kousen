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

from kousen.utils import _await_if_async

__all__: list[str] = ["Hooks", "CommandHooks", "ComponentHooks", "BotHooks"]


class _HookTypes(str, Enum):
    ERROR = "error"
    CHECK_ERROR = "check_error"

    PRE_INVOKE = "pre_invoke"
    POST_INVOKE = "post_invoke"
    COMMAND_SUCCESS = "command_success"

    COMPONENT_ADDED = "component_added"
    COMPONENT_REMOVED = "component_removed"


async def dispatch_hooks(
    hook_type: _HookTypes,
    bot_hooks: "BotHooks",
    component_hooks: "ComponentHooks",
    *,
    command_hooks: t.Optional["CommandHooks"] = None,
    **kwargs,
) -> bool:
    """
    Method used to dispatch all the hooks for that hook type taking into account component/command local overwrites.

    Parameters
    ----------
    hook_type : :obj:`.hooks._HookTypes`
        The hook type to dispatch.
    bot_hooks : :obj:`.hooks._Hooks`
        The bot's hooks.
    component_hooks : :obj:`.hooks._Hooks`
        The component's hooks which overwrites the bot's hooks.
    command_hooks : Optional[:obj:`.hooks._Hooks`]
        The command's hooks which overwrites both the bot's and component's hooks. (Not relevant for non-command related
        hooks)
    **kwargs : dict[`str`, `Any`]
        The args to be passed into the hook callback, e.g. error= or context=

    Returns
    -------
    :obj:`bool`
        True if any hooks were dispatched, false if there were no set hooks.
    """
    if command_hooks:
        if await command_hooks.dispatch(hook_type, **kwargs):
            return True
        if await component_hooks.dispatch(hook_type, **kwargs):
            return True
        if await bot_hooks.dispatch(hook_type, **kwargs):
            return True
        return False

    if await component_hooks.dispatch(hook_type, **kwargs):
        return True
    if await bot_hooks.dispatch(hook_type, **kwargs):
        return True
    return False


class Hooks:

    __slots__ = ("_all_hooks",)

    def __init__(self):
        self._all_hooks: dict[_HookTypes, list[t.Callable]] = {}

    async def dispatch(self, hook_type: _HookTypes, **kwargs) -> bool:
        """
        Method used to dispatch all the hook callables for that hook type.

        Parameters
        ----------
        hook_type : :obj:`.hooks._HookTypes`
            The hook type to dispatch.

        Returns
        -------
        :obj:`bool`
            True if any hooks were dispatched, false if there were no set hooks.
        """
        if hook_callables := self._all_hooks.get(hook_type):
            for callable_ in hook_callables:
                await _await_if_async(callable_, **kwargs)
                # todo turn dict into values iterable then pass unpacked *(kwargs.values)
            return True
        return False

    def on_error(self):
        # error
        ...

    def add_on_error(self):
        # error
        ...

    def on_check_error(self):
        # error
        ...

    def add_on_check_error(self):
        # error
        ...

    def on_command_disabled(self):
        # context
        ...

    def on_pre_invoke(self):
        # context
        ...

    def and_on_pre_invoke(self):
        # context
        ...

    def on_post_invoke(self):
        # context
        ...

    def add_on_post_invoke(self):
        # context
        ...

    def on_command_success(self):
        # context
        ...

    def add_on_command_success(self):
        # context
        ...


CommandHooks = Hooks


class ComponentHooks(Hooks):
    def on_component_added(self):
        # component + bot
        ...

    def add_on_component_added(self):
        # component + bot
        ...

    def on_component_removed(self):
        # component + bot
        ...

    def add_on_component_removed(self):
        # component + bot
        ...


BotHooks = ComponentHooks
