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
import asyncio
import logging
import typing as t
from inspect import iscoroutinefunction

import functools

import hikari

from kousen import Context, PartialContext

__all__: list[str] = ["Bot"]

_LOGGER = logging.getLogger("kousen")


def _handle_prefixes(prefix, bot_user_id=None):
    prefix_list = []
    if isinstance(prefix, str):
        prefix_list.append(prefix)
        if bot_user_id:
            prefix_list.extend((f"<@{bot_user_id}>", f"<@!{bot_user_id}>"))
        return functools.partial(_base_getter, return_object=prefix_list)

    if isinstance(prefix, t.Iterable):
        prefix_list.extend(list(map(str, prefix)))
        if bot_user_id:
            prefix_list.extend((f"<@{bot_user_id}>", f"<@!{bot_user_id}>"))
        return functools.partial(_base_getter, return_object=prefix_list)

    if iscoroutinefunction(prefix):
        return functools.partial(
            _prefix_getter_with_callback, callback=prefix, bot_id=bot_user_id
        )

    else:
        raise TypeError(
            f"Prefix must be either a string, or iterable of strings, or a coroutine, not type {type(prefix)}"
        )


async def _prefix_getter_with_callback(
    partial_context: PartialContext, callback, bot_id
):
    getter_result = await callback(partial_context)
    prefixes = []

    if isinstance(getter_result, str):
        prefixes.append(str)
        if bot_id:
            prefixes.extend((f"<@{bot_id}>", f"<@!{bot_id}>"))
        return prefixes

    if isinstance(getter_result, t.Iterable):
        prefixes.extend(list(map(str, getter_result)))
        if bot_id:
            prefixes.extend((f"<@{bot_id}>", f"<@!{bot_id}>"))
        return prefixes

    else:
        raise TypeError(
            f"The prefix callback must return a string or iterable of strings, not type {type(getter_result)}"
        )


def _base_bool_getter_handler(callable_or_bool, name: str):
    if isinstance(callable_or_bool, bool):
        return functools.partial(_base_getter, return_object=callable_or_bool)
    elif iscoroutinefunction(callable_or_bool):
        return functools.partial(
            _base_getter_with_callback,
            callback=callable_or_bool,
            result_type=bool,
            error_text=f"The {name} callback must return a bool",
        )
    else:
        raise TypeError(
            f"{name.capitalize()} arg must be either a bool or a coroutine, not type {type(callable_or_bool)}"
        )


async def _base_getter_with_callback(
    partial_context_or_context, callback, result_type, error_text
):
    getter_result = await callback(partial_context_or_context)

    if isinstance(getter_result, result_type):
        return getter_result
    else:
        raise TypeError(f"{error_text}, not type {type(getter_result)}")


async def _base_getter(_, return_obj):
    return return_obj


class Bot(hikari.GatewayBot):
    """The standard implementation of :class:`hikari.impl.bot.GatewayBot` with a command handler.

    Note
    ----
    Mention prefixes will continue to work with message commands after the message content intent becomes privileged.

    Parameters
    ----------
    default_prefix : Union[:obj:`str`, Iterable[:obj:`str`], Callable[[:obj:`~PartialContext`], Coroutine[:obj:`None`, :obj:`None`, Union[:obj:`str`, Iterable[:obj:`str`]]]]
        The bot's command prefix.
    mention_prefix : :obj:`bool`
        Whether or not the bot's mention will be used as a prefix. This will be `True` if no default
        prefix is provided, else `False` by default. (Note: added in `hikari.StartedEvent` as cache/rest
         is not usable before then.)

    Other Parameters
    ----------------
    default_parser : Union[:obj:`str`, Callable[[:obj:`~PartialContext`], Coroutine[:obj:`None`, :obj:`None`, :obj:`str`]]]
        The default parser to use for parsing message content for command arguments. Defaults to a whitespace.
        (Note that regardless of this parser, commands and subcommands should always be seperated
        by a whitespace, as this option only affects argument parsing.)
    weak_command_search : :obj:`bool`
        If `True`, then the bot will parse for the prefix throughout the message content (instead of just the
        start), allowing for commands to be called at any point in the message. Defaults to False.
    case_insensitive_commands : :obj:`bool`
        Whether or not commands should be case-insensitive or not. Defaults to `False` (commands are case-sensitive).
    case_insensitive_prefixes : :obj:`bool`
        Whether or not prefixes should be handled as case-insensitive or not.
        Defaults to `False` (prefixes are case-sensitive).
    ignore_bots : :obj:`bool`
        Prevents other bot's messages invoking your bot's commands if `True`. Defaults to `True`.
    owners : Iterable[`int`]
        The IDs or User objects of the users which should be treated as "owners" of the bot.
        By default this will include the bot owner's id (added in `hikari.StartedEvent` as cache/rest
         is not usable before then.)
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        default_prefix: t.Union[
            str,
            t.Iterable[str],
            t.Callable[
                [PartialContext], t.Coroutine[None, None, t.Union[str, t.Iterable[str]]]
            ],
        ] = None,
        mention_prefix: bool = None,  # so the default can be different depending on whether a prefix was passed
        default_parser: t.Union[
            str, t.Callable[[Context], t.Coroutine[None, None, str]]
        ] = " ",
        weak_command_search: t.Union[
            bool, t.Callable[[PartialContext], t.Coroutine[None, None, bool]]
        ] = False,
        case_insensitive_commands: t.Union[
            bool, t.Callable[[PartialContext], t.Coroutine[None, None, bool]]
        ] = False,
        case_insensitive_prefixes: t.Union[
            bool, t.Callable[[PartialContext], t.Coroutine[None, None, bool]]
        ] = False,
        ignore_bots: t.Union[
            bool, t.Callable[[PartialContext], t.Coroutine[None, None, bool]]
        ] = True,
        owners: t.Iterable[int] = (),
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        # allows us to check cache settings later on
        if (cache_settings := kwargs.get("cache_settings")) is not None:
            self._cache_components = cache_settings.components
        else:
            self._cache_components = hikari.CacheComponents.ALL

        # turning passed args in to getters that can be called
        if mention_prefix is False and default_prefix is None:
            raise ValueError(
                "No default prefix was provided and mention_prefix was set to False."
            )

        if mention_prefix is True or default_prefix is None:
            self._prefix_getter = default_prefix  # will add bot mentions after running as cache/rest is needed
        self._prefix_getter = _handle_prefixes(default_prefix)

        if isinstance(default_parser, str):
            self._default_parser_getter = functools.partial(_base_getter, return_object=default_parser)

        elif iscoroutinefunction(default_parser):
            self._default_parser_getter = functools.partial(
                _base_getter_with_callback,
                callback=default_parser,
                result_type=str,
                error_text="The parser callback must return a string",
            )
        else:
            raise TypeError(
                f"Parser must be either a string or a coroutine, not type {type(default_parser)}"
            )

        self._weak_command_search = _base_bool_getter_handler(
            weak_command_search, "Weak command search"
        )
        self._case_insensitive_commands = _base_bool_getter_handler(
            case_insensitive_commands, "Case insensitive commands"
        )
        self._case_insensitive_prefixes = _base_bool_getter_handler(
            case_insensitive_prefixes, "Case insensitive prefixes"
        )
        self._ignore_bots = _base_bool_getter_handler(ignore_bots, "Ignore bots")

        if owners is not None:
            if not isinstance(owners, t.Iterable):
                raise TypeError(f"Owners must be an iterable, not type {type(owners)}")
            else:
                self._owners = []
                for owner in owners:
                    if not isinstance(owner, int):
                        raise TypeError(
                            f"Owners must be an iterable of ints, not of type {type(owner)}"
                        )
                    self._owners.append(owner)
        else:
            self._owners = None  # will add bot owner's id after running as cache/rest is needed

        if self._prefix_getter == default_prefix:
            self.subscribe(hikari.StartedEvent, self._create_prefix_getter_with_mentions)
        self.subscribe(hikari.StartedEvent, self._add_owner_to_owners)

    async def _create_prefix_getter_with_mentions(self):
        user = self.get_me()
        if user is None:
            user = await self.rest.fetch_my_user()
            # todo implement backoff with fetch
        self._prefix_getter = _handle_prefixes(self._prefix_getter, user.id)

    async def _add_owner_to_owners(self):
        user = self.get_me()
        if user is None:
            user = await self.rest.fetch_my_user()
            # todo implement backoff with fetch
        if (bot_id := user.id) not in self._owners:
            self._owners.append(bot_id)
