import asyncio
import datetime
import discord
from discord.ext import commands


def _parse_duration(s: str) -> int | None:
    """Parse '10s', '5m', '2h', '1d' into seconds. Returns None if invalid."""
    s = s.strip().lower()
    try:
        if s.endswith("s"):
            return int(s[:-1])
        elif s.endswith("m"):
            return int(s[:-1]) * 60
        elif s.endswith("h"):
            return int(s[:-1]) * 3600
        elif s.endswith("d"):
            return int(s[:-1]) * 86400
    except ValueError:
        pass
    return None


def _fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        return f"{seconds // 3600}h"
    else:
        return f"{seconds // 86400}d"


class Moderation(commands.Cog):
    """Server moderation commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Kick ──────────────────────────────────────────────────────────────────
    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Kick a member from the server."""
        await member.kick(reason=reason)
        embed = discord.Embed(
            title="Member Kicked",
            description=f"{member.mention} has been kicked.",
            color=discord.Color.orange(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Actioned by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    # ── Ban ───────────────────────────────────────────────────────────────────
    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Ban a member from the server."""
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="Member Banned",
            description=f"{member.mention} has been banned.",
            color=discord.Color.red(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Actioned by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    # ── Unban ─────────────────────────────────────────────────────────────────
    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, *, username: str):
        """Unban a user by their username."""
        bans = [entry async for entry in ctx.guild.bans()]
        match = next((entry for entry in bans if str(entry.user) == username), None)
        if match is None:
            await ctx.send(f"No banned user found matching `{username}`.")
            return
        await ctx.guild.unban(match.user)
        embed = discord.Embed(
            title="Member Unbanned",
            description=f"**{match.user}** has been unbanned.",
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Actioned by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    # ── Clear ─────────────────────────────────────────────────────────────────
    @commands.command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount: int = 10):
        """Delete a number of messages (default: 10, max: 100)."""
        amount = min(max(amount, 1), 100)
        deleted = await ctx.channel.purge(limit=amount)
        confirm = await ctx.send(f"Deleted {len(deleted)} message(s).")
        await confirm.delete(delay=4)

    # ── Slowmode ──────────────────────────────────────────────────────────────
    @commands.command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx: commands.Context, seconds: int = 0):
        """Set channel slowmode. Use 0 to disable. Max 21600 (6 hours)."""
        seconds = max(0, min(seconds, 21600))
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.send("✅ Slowmode disabled for this channel.")
        else:
            await ctx.send(f"✅ Slowmode set to **{_fmt_duration(seconds)}** in this channel.")

    # ── Tempmute ──────────────────────────────────────────────────────────────
    @commands.command(name="tempmute")
    @commands.has_permissions(manage_roles=True)
    async def tempmute(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
        """Temporarily mute a member. Usage: !tempmute <user> <duration> [reason]"""
        seconds = _parse_duration(duration)
        if not seconds or seconds < 10:
            await ctx.send(
                "❌ Invalid duration. Use `30s`, `10m`, `1h`, `1d`.\nExample: `!tempmute @user 10m Spamming`",
                delete_after=10,
            )
            return

        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
            await ctx.send(
                "❌ No **Muted** role found. Please create a role named `Muted` with Send Messages denied.",
                delete_after=10,
            )
            return

        if muted_role in member.roles:
            await ctx.send(f"{member.mention} is already muted.", delete_after=8)
            return

        expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)
        unix_ts = int(expires_at.timestamp())

        try:
            await member.add_roles(muted_role, reason=f"Tempmute by {ctx.author}: {reason}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to assign the Muted role.", delete_after=8)
            return

        # DM the member
        try:
            await member.send(
                f"You have been muted in **{ctx.guild.name}** for **{_fmt_duration(seconds)}**.\n"
                f"**Reason:** {reason}\n"
                f"**Expires:** <t:{unix_ts}:R>"
            )
        except discord.Forbidden:
            pass

        embed = discord.Embed(
            title="🔇 Member Tempmuted",
            description=f"{member.mention} (`{member}`) has been muted for **{_fmt_duration(seconds)}**.",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(name="Duration", value=_fmt_duration(seconds), inline=True)
        embed.add_field(name="Expires", value=f"<t:{unix_ts}:R>", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Actioned by {ctx.author.display_name}")
        await ctx.send(embed=embed)

        asyncio.create_task(self._unmute_after(member, ctx.guild, muted_role, seconds))

    async def _unmute_after(self, member: discord.Member, guild: discord.Guild, muted_role: discord.Role, seconds: int):
        await asyncio.sleep(seconds)
        try:
            fresh = guild.get_member(member.id) or await guild.fetch_member(member.id)
            if muted_role in fresh.roles:
                await fresh.remove_roles(muted_role, reason="Tempmute expired")
        except (discord.NotFound, discord.HTTPException):
            pass

    # ── Tempban ───────────────────────────────────────────────────────────────
    @commands.command(name="tempban")
    @commands.has_permissions(ban_members=True)
    async def tempban(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
        """Temporarily ban a member. Usage: !tempban <user> <duration> [reason]"""
        seconds = _parse_duration(duration)
        if not seconds or seconds < 60:
            await ctx.send(
                "❌ Invalid duration. Use `10m`, `1h`, `7d` (minimum 1 minute).\nExample: `!tempban @user 7d Breaking rules`",
                delete_after=10,
            )
            return

        expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)
        unix_ts = int(expires_at.timestamp())

        # DM before banning
        try:
            await member.send(
                f"You have been temporarily banned from **{ctx.guild.name}** for **{_fmt_duration(seconds)}**.\n"
                f"**Reason:** {reason}\n"
                f"**Expires:** <t:{unix_ts}:R>"
            )
        except discord.Forbidden:
            pass

        try:
            await member.ban(reason=f"Tempban ({_fmt_duration(seconds)}) by {ctx.author}: {reason}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban that member.", delete_after=8)
            return

        embed = discord.Embed(
            title="🔨 Member Tempbanned",
            description=f"{member.mention} (`{member}`) has been banned for **{_fmt_duration(seconds)}**.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(name="Duration", value=_fmt_duration(seconds), inline=True)
        embed.add_field(name="Expires", value=f"<t:{unix_ts}:R>", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Actioned by {ctx.author.display_name}")
        await ctx.send(embed=embed)

        asyncio.create_task(self._unban_after(ctx.guild, member.id, seconds))

    async def _unban_after(self, guild: discord.Guild, user_id: int, seconds: int):
        await asyncio.sleep(seconds)
        try:
            user = await self.bot.fetch_user(user_id)
            await guild.unban(user, reason="Tempban expired")
        except (discord.NotFound, discord.HTTPException):
            pass

    # ── Error handler ─────────────────────────────────────────────────────────
    @kick.error
    @ban.error
    @unban.error
    @clear.error
    @slowmode.error
    @tempmute.error
    @tempban.error
    async def moderation_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.", delete_after=8)
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("Member not found. Please mention a valid user.", delete_after=8)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing argument. Check the command usage.", delete_after=8)
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Invalid argument. Check your command and try again.", delete_after=8)
        else:
            await ctx.send(f"An error occurred: {error}", delete_after=8)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
