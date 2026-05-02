import asyncio
import datetime
import discord
from discord.ext import commands


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class Logging(commands.Cog):
    """Logs moderation actions to a designated channel."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_log_channel(self, guild: discord.Guild):
        import os
        channel_id = os.environ.get("LOG_CHANNEL_ID")
        if not channel_id:
            return None
        channel = guild.get_channel(int(channel_id))
        return channel

    async def _get_audit_entry(self, guild: discord.Guild, action: discord.AuditLogAction, target):
        await asyncio.sleep(1)
        async for entry in guild.audit_logs(limit=5, action=action):
            if entry.target.id == target.id:
                return entry
        return None

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        channel = self._get_log_channel(guild)
        if not channel:
            return
        entry = await self._get_audit_entry(guild, discord.AuditLogAction.ban, user)
        moderator = entry.user if entry else "Unknown"
        reason = entry.reason or "No reason provided" if entry else "No reason provided"

        embed = discord.Embed(
            title="🔨 Member Banned",
            color=discord.Color.red(),
            timestamp=_now(),
        )
        embed.add_field(name="User", value=f"{user} (`{user.id}`)", inline=False)
        embed.add_field(name="Moderator", value=str(moderator), inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        channel = self._get_log_channel(guild)
        if not channel:
            return
        entry = await self._get_audit_entry(guild, discord.AuditLogAction.unban, user)
        moderator = entry.user if entry else "Unknown"

        embed = discord.Embed(
            title="✅ Member Unbanned",
            color=discord.Color.green(),
            timestamp=_now(),
        )
        embed.add_field(name="User", value=f"{user} (`{user.id}`)", inline=False)
        embed.add_field(name="Moderator", value=str(moderator), inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel = self._get_log_channel(member.guild)
        if not channel:
            return
        await asyncio.sleep(1)
        entry = await self._get_audit_entry(member.guild, discord.AuditLogAction.kick, member)
        if not entry:
            return
        moderator = entry.user
        reason = entry.reason or "No reason provided"

        embed = discord.Embed(
            title="👢 Member Kicked",
            color=discord.Color.orange(),
            timestamp=_now(),
        )
        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Moderator", value=str(moderator), inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]):
        if not messages:
            return
        guild = messages[0].guild
        channel_origin = messages[0].channel
        channel = self._get_log_channel(guild)
        if not channel:
            return

        embed = discord.Embed(
            title="🗑️ Messages Cleared",
            color=discord.Color.blurple(),
            timestamp=_now(),
        )
        embed.add_field(name="Channel", value=channel_origin.mention, inline=True)
        embed.add_field(name="Messages deleted", value=str(len(messages)), inline=True)
        await channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Logging(bot))
