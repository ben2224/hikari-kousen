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
    """
    Enum of all hook types dispatched.
    The parameters listed for each type are the parameters that will be passed when calling the callback.

    Note
    ----
    Hooks that are related to components will not work for command hooks and will not be added to command hooks.
    """

    ERROR = "error"
    """
    Dispatched when any error relating to command handling (other than checks) occurs, such as CommandNotFound or CommandError. 
    
    Note
    ----
    Any raw errors unrelated to the command handling (error by the developer) should be logged by kousen
    and will not dispatch this hook.
    
    Parameters
    ----------
    error : :obj:`~.errors.KousenError`
        The error that was raised, all errors have access to the context and therefore the bot instance.
    """

    CHECK_ERROR = "check_error"
    """
    A specific error hook dispatched when checks for a command fail.
    
    Parameters
    ----------
    error : :obj:`~.errors.CheckError`
        The check error that was raised, all check errors have access to the context and therefore the bot instance.
    """

    PRE_INVOKE = "pre_invoke"
    """
    This will be dispatched before a command invocation. Applies to all commands as a bot hook, 
    or all commands inside a component for a component hook, or the individual command for a command hook.
    
    Warning
    ----
    This is dispatched regardless of checks and cooldowns.
    
    Parameters
    ----------
    context : :obj:`~.context.MessageContext`
        The context of the message and command.
    """

    POST_INVOKE = "post_invoke"
    """
    Dispatched after a command invocation. Applies to all commands as a bot hook, 
    or all commands inside a component for a component hook, or the individual command for a command hook.
    
    Warning
    ----
    This is dispatched regardless of any errors inside the command, including checks and cooldowns.
    
    Parameters
    ----------
    context : :obj:`~.context.MessageContext`
        The context of the message and command.
    """

    COMMAND_SUCCESS = "command_success"
    """
    Dispatched if a command invocation is successful and raises no errors. Applies to all commands as a bot hook, 
    or all commands inside a component for a component hook, or the individual command for a command hook.
    
    Parameters
    ----------
    context : :obj:`~.context.MessageContext`
        The context of the message and command.
    """

    COMPONENT_ADDED = "component_added"
    """
    Dispatched when a component is added to the bot. The bot hook will be dispatched for all components, 
    or the hook of the component added will be dispatched if set.
    
    Warning
    ----
    This will not be dispatched if the bot has not yet been started.
    
    Parameters
    ----------
    component : :obj:`~.component.Component`
        The component added.
    bot : :obj:`~.handler.Bot`
        The bot instance.
    """

    COMPONENT_REMOVED = "component_removed"
    """
    Dispatched when a component is removed from the bot. The bot hook will be dispatched for all components, 
    or the hook of the component removed will be dispatched if set.

    Warning
    ----
    This will not be dispatched if the bot has not yet been started.
    
    Parameters
    ----------
    component : :obj:`~.component.Component`
        The component added.
    bot : :obj:`~.handler.Bot`
        The bot instance.
    """


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
    dispatch_future = asyncio.wait_for(
        _dispatch_hooks(hook_type, bot_hooks, component_hooks, command_hooks, **kwargs), timeout=None
    )
    _LOGGER.debug(f"All available {hook_type} hooks were dispatched.")
    return dispatch_future.result()


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
    """
    Manager class of bot, component, and command hooks. Hook are used like hikari events and allow you to call certain
    functions when certain events happen in kousen, such as when an error is raised. See :obj:`~.hooks.HookTypes` for
    the different types/events. See below for examples on how to use hooks.

    Note
    ----
    Callables you add as hooks can be both sync and async.

    Examples
    --------
    Adding a hook to the bot's hooks:
    .. code-block:: python
        bot = kousen.Bot(...)

        @bot.hooks.with_hook_callback(hook_type=kousen.HookTypes.Error)
        async def error_handler(error: kousen.KousenError):
            await error.context.respond("An error occurred!!!")

    Adding to a component's hooks (and commands):
    .. code-block:: python
        component = kousen.Component(...)

        @component.hooks.with_hook_callback(hook_type=kousen.HookTypes.Error)
        async def error_handler(error: kousen.KousenError):
            await error.context.respond("An error occurred!!!")

        # with a command
        @kousen.with_message_command
        @kousen.create_message_command(...)
        async def ping(context: kousen.MessageContext):
           await context.respond("Pong!)

        @ping.hooks.with_client_callback(hook_type=kousen.HookTypes.Error)
        async def ping_error_handler(error: kousen.KousenError)
            await error.respond("A ping command error occurred!!!")

    Alternatively you can add hooks without decorators:
    .. code-block:: python
        async def error_handler(error: kousen.KousenError):
            await error.context.respond("An error occurred!!!")

        <bot/component/command>.hooks.add_hook_callback(kousen.HookTypes.Error, error_handler)

    Additionally you can add hooks to the bot inside components, though they will not be added until the component
    is added to the bot instance.
    .. code-block:: python
        component = kousen.Component(...)

        @component.add_hook_callback_to_bot(hook_type=kousen.HookTypes.Error)
        async def error_handler(error: kousen.KousenError):
            await error.context.respond("An error occurred!!!")

    Warning
    -------
    There is no need for a user of hikari to create their own instance of this class, as kousen creates the hooks for
    the bot and all components and commands.
    """

    __slots__ = ("_all_hooks", "_instance", "_type")

    def __init__(
        self, instance: t.Union[Component, Bot, MessageCommand], _type: t.Literal["bot", "component", "command"]
    ):
        self._all_hooks: dict[HookTypes, list[t.Callable]] = {}
        self._instance: t.Union[Component, Bot, MessageCommand] = instance
        self._type: t.Literal["bot", "component", "command"] = _type

    async def dispatch(self, hook_type: HookTypes, **kwargs) -> bool:
        """
        Method used by kousen dispatch all the hook callables for that hook type.

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
                try:
                    await _await_if_async(callable_, *(kwargs.values()))
                except Exception as ex:
                    _LOGGER.error(
                        f"The {hook_type.name} hook callable '{callable_}' raised the exception:", exc_info=ex
                    )
            return True
        return False

    def with_hook_callback(self, hook_type: HookTypes):
        """
        A decorator that adds the decorated function to the hooks. Function can be both sync or async.

        Note
        ----
        Hooks that are related to components will not work for command hooks and will not be added to command hooks.

        Warning
        -------
        The parameters for the function should all be positional as they will be passed positionally.

        Parameters
        ----------
        hook_type : :obj:`~.hooks.HookTypes`
            The hook type associated with the function.

        Returns
        -------
        Callable[[`Any`], `Any`]
            The original function that was decorated.
        """

        def decorate(func: t.Callable):
            self.add_hook_callback(hook_type, func)
            return func

        return decorate

    def add_hook_callback(self, hook_type: HookTypes, callback: t.Callable[[t.Any], t.Any]) -> "Hooks":
        """
        Add a callback hook for a hook type. See :obj:`~.hooks.HookTypes` for more information on the different types.
        Callbacks can be both sync or async.

        Note
        ----
        Hooks that are related to components will not work for command hooks and will not be added to command hooks.

        Warning
        -------
        The parameters for the callback should all be positional as they will be passed positionally.

        Parameters
        ----------
        hook_type : :obj:`~.hooks.HookTypes`
            The hook type associated with the callback.
        callback : Callable[[`Any`], `Any`]
            The callback to add to the hooks that will be called when the hook type is dispatched.

        Returns
        -------
        :obj:`~.hooks.Hooks`
            The instance of the hooks to allow for chain calls.
        """

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
