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

import datetime
import functools
import typing as t

import hikari

if t.TYPE_CHECKING:
    from kousen import Bot, Command, Module

__all__: list[str] = ["PartialContext", "Context"]


class PartialContext:
    """Partial context"""

    __slots__ = ("_bot", "_message")

    def __init__(
        self,
        bot: Bot,
        message: hikari.Message,
    ) -> None:
        self._bot: Bot = bot
        self._message: hikari.Message = message

    @property
    def bot(self) -> Bot:
        """The bot instance."""
        return self._bot

    @property
    def cache(self) -> t.Optional[hikari.api.Cache]:
        return self._bot.cache

    @property
    def rest(self) -> hikari.api.RESTClient:
        return self._bot.rest

    @property
    def shard(self) -> t.Optional[hikari.api.GatewayShard]:
        try:
            return self._bot._get_shard(self._message.guild_id)
        except RuntimeError:
            return None

    @property
    def message(self) -> hikari.Message:
        return self._message

    @property
    def author(self) -> hikari.User:
        return self._message.author

    @property
    def member(self) -> t.Optional[hikari.Member]:
        return self._message.member

    @property
    def is_human(self) -> bool:
        return (
            not self._message.author.is_system
            and not self._message.author.is_bot
            and self._message.webhook_id is None
        )

    @property
    def created_at(self) -> datetime.datetime:
        return self._message.created_at

    @property
    def channel_id(self) -> hikari.Snowflake:
        return self._message.channel_id

    @property
    def guild_id(self) -> t.Optional[hikari.Snowflake]:
        return self._message.guild_id

    # todo raise not cached error?
    def get_channel(self) -> t.Optional[hikari.PartialChannel]:
        if self._bot.cache._is_cache_enabled_for(hikari.CacheComponents.GUILD_CHANNELS):
            return self._bot.cache.get_guild_channel(self.channel_id)
        return None

    def get_guild(self) -> t.Optional[hikari.Guild]:
        if self.guild_id is not None and self._bot.cache._is_cache_enabled_for(
            hikari.CacheComponents.GUILDS
        ):
            return self._bot.cache.get_guild(self.guild_id)
        return None

    # todo raise error instead of returning None?
    async def fetch_channel(self) -> t.Optional[hikari.PartialChannel]:
        try:
            return await self._bot.rest.fetch_channel(self.channel_id)
        except hikari.NotFoundError:
            return None

    async def fetch_guild(self) -> t.Optional[hikari.Guild]:
        if self.guild_id is not None:
            try:
                return await self._bot.rest.fetch_guild(self.guild_id)
            except hikari.NotFoundError:
                return None
        return None

    @functools.wraps(hikari.Message.respond)
    async def respond(self, *args, **kwargs) -> hikari.Message:
        return await self.message.respond(*args, **kwargs)


class Context(PartialContext):
    """Context"""

    __slots__ = ("_prefix", "_invoked_with", "_command", "_parser")

    def __init__(
        self,
        bot: Bot,
        message: hikari.Message,
        prefix: str,
        parser: str,
        invoked_with: str,
        command: Command,
    ) -> None:
        super().__init__(bot=bot, message=message)
        self._prefix: str = prefix
        self._parser: str = parser
        self._invoked_with: str = invoked_with
        self._command: Command = command

    @property
    def prefix(self) -> str:
        return self._prefix

    @property
    def parser(self) -> str:
        return self._parser

    @property
    def invoked_with(self) -> str:
        return self._invoked_with

    @property
    def command(self) -> Command:
        return self._command

    @property
    def module(self) -> Module:
        return self._command.module
