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
import hikari
import abc

if t.TYPE_CHECKING:
    from kousen.handler import Bot
    from kousen.commands import MessageCommand, SlashCommand
    from kousen.components import Component

__all__: list[str] = ["Context", "MessageContext"]


class Context(abc.ABC):
    """
    Abstract base class for all context types.

    Parameters
    ----------
    bot : :obj:~.handler.Bot`
        The instance of the bot.
    """

    __slots__ = ("_bot", "_responses")

    def __init__(
        self,
        bot: Bot,
    ) -> None:
        self._bot: Bot = bot
        self._responses: list[hikari.Message] = []

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
    @abc.abstractmethod
    def shard(self) -> t.Optional[hikari.api.GatewayShard]:
        """
        The shard of the guild/DM that the command was invoked in.

        Returns
        -------
        Optional[:obj:`hikari.api.GatewayShard`]
            The GatewayShard object.
        """
        ...

    @property
    @abc.abstractmethod
    def user(self) -> hikari.User:
        """
        The user who invoked the command.

        Returns
        -------
        :obj:`hikari.User`
            The user object of the invoking user.
        """
        ...

    @property
    @abc.abstractmethod
    def member(self) -> t.Optional[hikari.Member]:
        """
        The guild member who invoked the command. This will be None if the command was invoked in a DM.

        Returns
        -------
        Optional[:obj:`hikari.Member`]
            The member object of the invoking user.
        """
        ...

    @property
    @abc.abstractmethod
    def channel_id(self) -> hikari.Snowflake:
        """
        The channel id of the channel that the command was invoked in.

        Returns
        -------
        :obj:`hikari.Snowflake`
            The channel id as a snowflake object.
        """
        ...

    @property
    @abc.abstractmethod
    def guild_id(self) -> t.Optional[hikari.Snowflake]:
        """
        The guild id of the guild that the command was invoked in. This will be None if invoked in a DM.

        Returns
        -------
        Optional[:obj:`hikari.Snowflake`]
            The guild id as a snowflake object.
        """
        ...

    @property
    @abc.abstractmethod
    def prefix(self) -> str:
        """
        The prefix the command was invoked with. This will always be a forward slash for slash commands.

        Returns
        -------
        `str`
            The invoking prefix.
        """
        ...

    @property
    @abc.abstractmethod
    def invoking_name(self) -> str:
        """
        The name of the command used to invoke the command. For slash commands this will always be the same, but may
        be an alias for message commands.

        Returns
        -------
        `str`
            The invoking command name.
        """
        ...

    @property
    @abc.abstractmethod
    def command(self) -> t.Union[MessageCommand, SlashCommand]:
        """
        The command that was invoked.

        Returns
        -------
        t.Union[:obj:`.commands.MessageCommand`, :obj:`.commands.SlashCommand`]
            The command object.
        """
        ...

    @property
    @abc.abstractmethod
    def component(self) -> Component:
        """
        The component that the command is added to.

        Returns
        -------
        :obj:`.components.Component`
            The component object.
        """
        ...

    @abc.abstractmethod
    def get_channel(self) -> t.Optional[hikari.GuildChannel]:
        """
        Get the channel object that the command was invoked in from the cache. This will be None if the cache is disabled,
        it was invoked in a DM or because the channel was not found in the cache.

        Note
        ----
        This method requires `hikari.config.CacheComponents.GUILD_CHANNELS` cache component enabled.

        Returns
        -------
        Optional[:obj:`hikari.GuildChannel`]
            The channel object the command was invoked in.
        """
        ...

    @abc.abstractmethod
    def get_guild(self) -> t.Optional[hikari.Guild]:
        """
        Get the guild object that the command was invoked in from the cache. This will be None if the cache is disabled,
        it was invoked in a DM or because the guild was not found in the cache.

        Note
        ----
        This method requires `hikari.config.CacheComponents.GUILDS` cache component enabled.

        Returns
        -------
        Optional[:obj:`hikari.Guild`]
            The guild object the command was invoked in.
        """
        ...

    @abc.abstractmethod
    async def fetch_channel(self) -> t.Optional[hikari.PartialChannel]:
        """
        Fetch the channel object that the command was invoked in

        Note
        ----
        This will perform an API call. Consider using :obj:`~.context.PartialContext.get_channel`
        if you have the guild channels cache component enabled.

        Returns
        -------
        :obj:`hikari.PartialChannel`
            The channel object the command was invoked in.

        Raises
        ------
        hikari.errors.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.errors.ForbiddenError
            If you are missing the `READ_MESSAGES` permission in the channel.
        hikari.errors.NotFoundError todo doesn't atm
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
        ...

    @abc.abstractmethod
    async def fetch_guild(self) -> t.Optional[hikari.RESTGuild]:
        """
        Fetch the guild object that the message was sent in

        Note
        ----
        This will perform an API call. Consider using :obj:`~.context.PartialContext.get_guild`
        if you have the guilds cache component enabled.

        Returns
        -------
        :obj:`hikari.RESTGuild`
            The guild object the command was invoked in.

        Raises
        ------
        hikari.errors.ForbiddenError
            If you are not part of the guild.
        hikari.errors.NotFoundError todo doesn't atm
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
        ...

    @abc.abstractmethod
    async def respond(self, *args: t.Any, **kwargs: t.Any) -> hikari.Message:
        ...

    async def get_initial_response(self) -> t.Optional[hikari.Message]:
        if not self._responses:
            return None
        return self._responses[0]

    async def get_last_response(self) -> t.Optional[hikari.Message]:
        if not self._responses:
            return None
        return self._responses[-1]

    async def get_all_responses(self) -> list[hikari.Message]:
        return self._responses

    async def delete_initial_response(self) -> None:
        if not self._responses:
            return None
        return await self._responses[0].delete()

    async def delete_last_response(self) -> None:
        if not self._responses:
            return None
        return await self._responses[-1].delete()

    async def delete_all_responses(self) -> None:
        return await self._bot.rest.delete_messages(self.channel_id, self._responses)


class MessageContext(Context):
    """
    The context of an invoked message command with various useful properties. For further information on message
    related properties see the hikari documentation.

    Parameters
    ----------
    bot : :obj:~.handler.Bot`
        The instance of the bot.
    event : :obj:`hikari.MessageCreateEvent`
        The message create event that the context relates to.
    prefix : :obj:`str`
        The prefix used by the user to invoke the message command
    invoking_name : :obj:`str`
        The name of the command the user used to invoke the message command.
    command : :obj:`~.commands.MessageCommand`
        The object of the message command that was invoked by the user.
    """

    __slots__ = ("_event", "_prefix", "_invoking_name", "_command")

    def __init__(
        self,
        bot: Bot,
        event: hikari.MessageCreateEvent,
        *,
        prefix: str,
        invoking_name: str,
        command: MessageCommand,
    ) -> None:
        super().__init__(bot=bot)
        self._event = event
        self._prefix: str = prefix
        self._invoking_name: str = invoking_name
        self._command: MessageCommand = command

    @property
    def shard(self) -> t.Optional[hikari.api.GatewayShard]:
        if not self._bot.shards:
            return None

        if (guild_id := self._event.message.guild_id) is not None:
            shard_id = hikari.snowflakes.calculate_shard_id(self.bot.shard_count, guild_id)
        else:
            shard_id = 0

        return self._bot.shards[shard_id]

    @property
    def user(self) -> hikari.User:
        return self._event.author

    @property
    def member(self) -> t.Optional[hikari.Member]:
        return self._event.message.member

    @property
    def channel_id(self) -> hikari.Snowflake:
        return self._event.channel_id

    @property
    def guild_id(self) -> t.Optional[hikari.Snowflake]:
        return self._event.message.guild_id

    @property
    def prefix(self) -> str:
        return self._prefix

    @property
    def invoking_name(self) -> str:
        return self._invoking_name

    @property
    def command(self) -> MessageCommand:
        return self._command

    @property
    def component(self) -> Component:
        assert self._command.component
        return self._command.component

    # todo raise not cached error?
    def get_channel(self) -> t.Optional[hikari.GuildChannel]:
        if (channel_id := self._event.channel_id) is not None:
            return self._bot.cache.get_guild_channel(channel_id)
        return None

    def get_guild(self) -> t.Optional[hikari.Guild]:
        if (guild_id := self._event.message.guild_id) is not None:
            return self._bot.cache.get_guild(guild_id)
        return None

    # todo raise error instead of returning None?
    async def fetch_channel(self) -> t.Optional[hikari.PartialChannel]:
        try:
            return await self._bot.rest.fetch_channel(self._event.channel_id)
        except hikari.NotFoundError:
            return None

    async def fetch_guild(self) -> t.Optional[hikari.RESTGuild]:
        if (guild_id := self._event.message.guild_id) is not None:
            try:
                return await self._bot.rest.fetch_guild(guild_id)
            except hikari.NotFoundError:
                return None
        return None

    async def respond(self, *args: t.Any, **kwargs: t.Any) -> hikari.Message:
        """
        An alias for :obj:`hikari.Message.respond`. See hikari's documentation for further details.

        Parameters
        ----------
        args : t.Any
            Positional args for :obj:`hikari.Message.respond`. See hikari docs.
        kwargs : t.Any
            Keyword args for :obj:`hikari.Message.respond`. See hikari docs.

        Warning
        -------
        Response types and flags cannot be used with messages and they will be omitted before calling
        :obj:`hikari.Message.respond`. They can still be passed due to the integration of the message and slash
        command interface in kousen and will work for slash commands.
        """

        if args and isinstance(args[0], hikari.ResponseType):
            args = args[1:]

        kwargs.pop("response_type")
        kwargs.pop("flags")

        msg = await self._event.message.respond(*args, **kwargs)
        self._responses.append(msg)
        return msg


class SlashContext(Context):
    """
    The context of an invoked slash command with various useful properties. For further information on interaction
    related properties see the hikari documentation.

    Parameters
    ----------
    bot : :obj:~.handler.Bot`
        The instance of the bot.
    event : :obj:`hikari.InteractionCreateEvent`
        The interaction create event that the context relates to.
    command : :obj:`~.commands.SlashCommand`
        The object of the slash command that was invoked by the user.
    """

    __slots__ = ("_event", "_prefix", "_invoking_name", "_command")

    def __init__(
        self,
        bot: Bot,
        event: hikari.InteractionCreateEvent,
        *,
        command: SlashCommand,
    ) -> None:
        super().__init__(bot=bot)
        self._event: hikari.InteractionCreateEvent = event
        assert isinstance(event.interaction, hikari.CommandInteraction)
        self._interaction: hikari.CommandInteraction = event.interaction
        self._prefix: str = "/"
        self._invoking_name: str = command.name
        self._command: SlashCommand = command

    @property
    def shard(self) -> t.Optional[hikari.api.GatewayShard]:
        if not self._bot.shards:
            return None

        if (guild_id := self._interaction.guild_id) is not None:
            shard_id = hikari.snowflakes.calculate_shard_id(self.bot.shard_count, guild_id)
        else:
            shard_id = 0

        return self._bot.shards[shard_id]

    @property
    def user(self) -> hikari.User:
        return self._interaction.user

    @property
    def member(self) -> t.Optional[hikari.Member]:
        return self._interaction.member

    @property
    def channel_id(self) -> hikari.Snowflake:
        return self._interaction.channel_id

    @property
    def guild_id(self) -> t.Optional[hikari.Snowflake]:
        return self._interaction.guild_id

    @property
    def prefix(self) -> str:
        return self._prefix

    @property
    def invoking_name(self) -> str:
        return self._invoking_name

    @property
    def command(self) -> SlashCommand:
        return self._command

    @property
    def component(self) -> Component:
        return self._command.component

    # todo raise not cached error?
    def get_channel(self) -> t.Optional[hikari.GuildChannel]:
        if (channel_id := self._interaction.channel_id) is not None:
            return self._bot.cache.get_guild_channel(channel_id)
        return None

    def get_guild(self) -> t.Optional[hikari.Guild]:
        if (guild_id := self._interaction.guild_id) is not None:
            return self._bot.cache.get_guild(guild_id)
        return None

    # todo raise error instead of returning None?
    async def fetch_channel(self) -> t.Optional[hikari.PartialChannel]:
        try:
            return await self._bot.rest.fetch_channel(self._interaction.channel_id)
        except hikari.NotFoundError:
            return None

    async def fetch_guild(self) -> t.Optional[hikari.RESTGuild]:
        if (guild_id := self._interaction.guild_id) is not None:
            try:
                return await self._bot.rest.fetch_guild(guild_id)
            except hikari.NotFoundError:
                return None
        return None

    async def respond(self, *args: t.Any, **kwargs: t.Any) -> hikari.Message:
        ...  # todo
