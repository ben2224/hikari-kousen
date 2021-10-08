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
import functools
import typing as t
import hikari

if t.TYPE_CHECKING:
    import datetime
    from kousen.handler import Bot
    from kousen.commands import MessageCommand
    from kousen.components import Component

__all__: list[str] = ["PartialMessageContext", "MessageContext"]


class PartialMessageContext:
    """
    The initial context of a message before any command has been parsed for or invoked. Mostly used for getters that
    are needed for parsing message content, such as the prefix.

    Parameters
    ----------
    bot : :obj:~.handler.Bot`
        The instance of the bot.
    message : :obj:`hikari.Message`
        The message object in which the partial context relates to.
    """

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
        """
        The bot instance.

        Returns
        -------
        :obj:`~.handler.Bot`
            The bot instance.
        """
        return self._bot

    @property
    def cache(self) -> hikari.api.Cache:
        """
        The hikari cache implementation initialised with the bot.

        Returns
        -------
        :obj:`hikari.api.Cache`
            The cache instance."""
        return self._bot.cache

    @property
    def rest(self) -> hikari.api.RESTClient:
        """
        The hikari REST client that the bot was initialised with.

        Returns
        -------
        :obj:`~hikari.api.RESTClient`
            The Hikari REST client..
        """
        return self._bot.rest

    @property
    def shard(self) -> t.Optional[hikari.api.GatewayShard]:
        """
        The shard of the guild/DM that the message command was invoked in.

        Returns
        -------
        Optional[:obj:`hikari.api.GatewayShard`]
            The GatewayShard object.
        """
        if not self._bot.shards:
            return None

        if self._message.guild_id is not None:
            shard_id = hikari.snowflakes.calculate_shard_id(
                self.bot.shard_count, self._message.guild_id
            )
        else:
            shard_id = 0

        return self._bot.shards[shard_id]

    @property
    def message(self) -> hikari.Message:
        """
        The message object that the context relates to.

        Returns
        -------
        :obj:`hikari.Message`
            The message object.
        """
        return self._message

    @property
    def author(self) -> hikari.User:
        """
        The author of the message that invoked the command.

        Returns
        -------
        :obj:`hikari.User`
            The user object of the message author.
        """
        return self._message.author

    @property
    def member(self) -> t.Optional[hikari.Member]:
        """
        The guild member of the message's author'. This will be None if the message command was invoked in a DM.

        Returns
        -------
        Optional[:obj:`hikari.Member`]
            The member object of the author.
        """
        return self._message.member

    @property
    def is_human(self) -> bool:
        """
        Whether or not the author of the invoking message is a human. This filters out bots, webhooks and system
        accounts.

        Returns
        -------
        :obj:`bool`
            Whether or not the author is a human.
        """
        return (
            not self._message.author.is_system
            and not self._message.author.is_bot
            and self._message.webhook_id is None
        )

    @property
    def created_at(self) -> datetime.datetime:
        """
        The time at which the invoking message was sent.

        Returns
        -------
        :obj:`datetime.datetime`
            A datetime object of when the message was sent.
        """
        return self._message.created_at

    @property
    def channel_id(self) -> hikari.Snowflake:
        """
        The channel id of the channel that the invoking message was sent in.

        Returns
        -------
        :obj:`hikari.Snowflake`
            The channel id as a snowflake object.
        """
        return self._message.channel_id

    @property
    def guild_id(self) -> t.Optional[hikari.Snowflake]:
        """
        The guild id of the guild that the invoking message was sent in. This will be None if sent in a DM.

        Returns
        -------
        Optional[:obj:`hikari.Snowflake`]
            The guild id as a snowflake object.
        """
        return self._message.guild_id

    # todo raise not cached error?
    def get_channel(self) -> t.Optional[hikari.GuildChannel]:
        """
        Get the channel object that the message was sent in from the cache. This will be None if the cache is disabled,
        the message was sent in a DM or because the channel was not found in the cache.

        Note
        ----
        This method requires `hikari.config.CacheComponents.GUILD_CHANNELS` cache component enabled.

        Returns
        -------
        Optional[:obj:`hikari.GuildChannel`]
            An channel object the message was sent in.
        """
        if self.channel_id is not None:
            return self._bot.cache.get_guild_channel(self.channel_id)
        return None

    def get_guild(self) -> t.Optional[hikari.Guild]:
        """
        Get the guild object that the message was sent in from the cache. This will be None if the cache is disabled,
        the message was sent in a DM or because the guild was not found in the cache.

        Note
        ----
        This method requires `hikari.config.CacheComponents.GUILDS` cache component enabled.

        Returns
        -------
        Optional[:obj:`hikari.Guild`]
            An guild object the message was sent in.
        """
        if self.guild_id is not None:
            return self._bot.cache.get_guild(self.guild_id)
        return None

    # todo raise error instead of returning None?
    async def fetch_channel(self) -> t.Optional[hikari.PartialChannel]:
        """
        Fetch the channel object that the message was sent in

        Note
        ----
        This will perform an API call. Consider using :obj:`~.context.PartialContext.get_channel`
        if you have the guilds cache component enabled.

        Returns
        -------
        :obj:`hikari.PartialChannel`
            The channel object the message was sent in.

        Raises
        ------
        hikari.errors.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.errors.ForbiddenError
            If you are missing the `READ_MESSAGES` permission in the channel.
        hikari.errors.NotFoundError
            If the channel is not found.
        hikari.errors.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.errors.RateLimitedError
            Usually, Hikari will handle and retry on hitting
            rate-limits automatically. This includes most bucket-specific
            rate-limits and global rate-limits. In some rare edge cases,
            however, Discord implements other undocumented rules for
            rate-limiting, such as limits per attribute. These cannot be
            detected or handled normally by Hikari due to their undocumented
            nature, and will trigger this exception if they occur.
        hikari.errors.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """
        try:
            return await self._bot.rest.fetch_channel(self.channel_id)
        except hikari.NotFoundError:
            return None

    async def fetch_guild(self) -> t.Optional[hikari.RESTGuild]:
        """
        Fetch the guild object that the message was sent in

        Note
        ----
        This will perform an API call. Consider using :obj:`~.context.PartialContext.get_guild`
        if you have the guild channels cache component enabled.

        Returns
        -------
        :obj:`hikari.RESTGuild`
            The guild object the message was sent in.

        Raises
        ------
        hikari.errors.ForbiddenError
            If you are not part of the guild.
        hikari.errors.NotFoundError
            If the guild is not found.
        hikari.errors.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.errors.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.errors.RateLimitedError
            Usually, Hikari will handle and retry on hitting
            rate-limits automatically. This includes most bucket-specific
            rate-limits and global rate-limits. In some rare edge cases,
            however, Discord implements other undocumented rules for
            rate-limiting, such as limits per attribute. These cannot be
            detected or handled normally by Hikari due to their undocumented
            nature, and will trigger this exception if they occur.
        hikari.errors.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """
        if self.guild_id is not None:
            try:
                return await self._bot.rest.fetch_guild(self.guild_id)
            except hikari.NotFoundError:
                return None
        return None

    @functools.wraps(hikari.Message.respond)
    async def respond(
        self,
        content: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED,
        *,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[
            t.Sequence[hikari.Resourceish]
        ] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[
            t.Sequence[hikari.api.ComponentBuilder]
        ] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[t.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        nonce: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        reply: t.Union[
            hikari.UndefinedType, hikari.SnowflakeishOr[hikari.PartialMessage], bool
        ] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        mentions_reply: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            t.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            t.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        """
        An alias for :obj:`hikari.Message.respond`. See hikari's documentation for further details.

        Notes
        ----
        If no colour is passed inside any embeds passed then :obj:`~.handler.Bot.default_embed_colour`
        is set as the colour if available.

        """
        if embed_colour := self._bot._default_embed_colour:
            if isinstance(content, hikari.Embed):
                if content.colour is None:
                    content.colour = embed_colour
            if isinstance(embed, hikari.Embed):
                if embed.colour is None:
                    embed.colour = embed_colour
            if isinstance(embeds, t.Collection):
                for emd in embeds:
                    if isinstance(emd, hikari.Embed):
                        if emd.colour is None:
                            emd.colour = embed_colour

        return await self._message.respond(
            content=content,
            attachment=attachment,
            attachments=attachments,
            component=component,
            components=components,
            embed=embed,
            embeds=embeds,
            tts=tts,
            nonce=nonce,
            reply=reply,
            mentions_everyone=mentions_everyone,
            mentions_reply=mentions_reply,
            user_mentions=user_mentions,
            role_mentions=role_mentions,
        )


class MessageContext(PartialMessageContext):
    """
    The context of an invoked message command with various useful properties. For further information on message
    related properties see the hikari documentation.

    Parameters
    ----------
    bot : :obj:~.handler.Bot`
        The instance of the bot.
    message : :obj:`hikari.Message`
        The message object in which the context relates to.
    prefix : :obj:`str`
        The prefix used by the user to invoke the message command
    invoked_with : :obj:`str`
        The name of the command the user used to invoke the message command.
    command : :obj:`~.commands.MessageCommand`
        The object of the message command that was invoked by the user.
    args : :obj:`str`
        A string of the raw args passed by the user.
    """

    __slots__ = ("_prefix", "_invoked_with", "_command", "_parser", "_args")

    def __init__(
        self,
        bot: Bot,
        message: hikari.Message,
        *,
        prefix: str,
        invoked_with: str,
        command: MessageCommand,
        args: str,
    ) -> None:
        super().__init__(bot=bot, message=message)
        self._prefix: str = prefix
        self._parser: t.Optional[str] = command._parser
        self._invoked_with: str = invoked_with
        self._command: MessageCommand = command
        self._args: str = args

    @property
    def prefix(self) -> str:
        return self._prefix

    @property
    def parser(self) -> t.Optional[str]:
        return self._parser

    @property
    def invoked_with(self) -> str:
        return self._invoked_with

    @property
    def command(self) -> MessageCommand:
        return self._command

    @property
    def component(self) -> Component:
        return self._command.component

    @property
    def args(self) -> str:
        return self._args

    @classmethod
    def _create_from_partial_context(
        cls,
        partial_context: PartialMessageContext,
        prefix: str,
        invoked_with: str,
        command: MessageCommand,
        args: str,
    ) -> "MessageContext":
        return cls(
            bot=partial_context._bot,
            message=partial_context._message,
            prefix=prefix,
            invoked_with=invoked_with,
            command=command,
            args=args,
        )
