import asyncio
import datetime
import discord
from discord.ext import commands
import os

_warnings: dict[int, list[dict]] = {}


def _log_channel(guild: discord.Guild) -> discord.TextChannel | None:
    cid = os.environ.get("LOG_CHANNEL_ID")
    if cid:
        return guild.get_channel(int(cid))
    return None


class Warnings(commands.Cog):
    """Warning system with escalating punishments."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _unmute_after(self, member: discord.Member, guild: discord.Guild, minutes: int):
        await asyncio.sleep(minutes * 60)
        muted_role = discord.utils.get(guild.roles, name="Muted")
        try:
            fresh = guild.get_member(member.id) or await guild.fetch_member(member.id)
            if muted_role and muted_role in fresh.roles:
                await fresh.remove_roles(muted_role, reason="Warning mute expired")
        except (discord.NotFound, discord.HTTPException):
            pass

    @commands.command(name="warn")
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Warn a member. Escalates: warn → mute → kick → ban."""
        if member.bot:
            await ctx.send("You cannot warn a bot.", delete_after=8)
            return
        if member == ctx.author:
            await ctx.send("You cannot warn yourself.", delete_after=8)
            return

        uid = member.id
        if uid not in _warnings:
            _warnings[uid] = []
        _warnings[uid].append({
            "reason": reason,
            "mod": str(ctx.author),
            "mod_id": ctx.author.id,
            "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        })
        count = len(_warnings[uid])

        if count == 1:
            action_label = "⚠️ Warned"
            action_desc = "No further action taken."
            color = discord.Color.yellow()
        elif count == 2:
            action_label = "🔇 Warned + Muted (10 min)"
            action_desc = "Auto-muted for 10 minutes."
            color = discord.Color.orange()
        elif count == 3:
            action_label = "👢 Warned + Kicked"
            action_desc = "Auto-kicked from the server."
            color = discord.Color.red()
        else:
            action_label = "🔨 Warned + Banned"
            action_desc = "Auto-banned from the server."
            color = discord.Color.dark_red()

        # DM the member
        try:
            dm = discord.Embed(
                title=f"⚠️ Warning #{count} — {ctx.guild.name}",
                description=f"**Reason:** {reason}\n\n{action_desc}",
                color=color,
                timestamp=datetime.datetime.utcnow(),
            )
            await member.send(embed=dm)
        except discord.Forbidden:
            pass

        # Apply escalating punishment
        if count == 2:
            muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
            if muted_role:
                try:
                    await member.add_roles(muted_role, reason=f"Warning #{count}: {reason}")
                    asyncio.create_task(self._unmute_after(member, ctx.guild, 10))
                except discord.Forbidden:
                    pass
        elif count == 3:
            try:
                await member.kick(reason=f"Warning #{count}: {reason}")
            except discord.Forbidden:
                pass
        elif count >= 4:
            try:
                await member.ban(reason=f"Warning #{count}: {reason}")
            except discord.Forbidden:
                pass

        embed = discord.Embed(
            title=action_label,
            description=f"{member.mention} (`{member}`) has been warned.",
            color=color,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Total Warnings", value=str(count), inline=True)
        embed.add_field(name="Action", value=action_desc, inline=True)
        embed.set_footer(text=f"Actioned by {ctx.author.display_name}")
        await ctx.send(embed=embed)

        log_ch = _log_channel(ctx.guild)
        if log_ch and log_ch != ctx.channel:
            await log_ch.send(embed=embed)

    @commands.command(name="warnings")
    @commands.has_permissions(kick_members=True)
    async def warnings(self, ctx: commands.Context, member: discord.Member):
        """Show all warnings for a member."""
        warns = _warnings.get(member.id, [])
        if not warns:
            await ctx.send(f"{member.mention} has no warnings on record.")
            return

        embed = discord.Embed(
            title=f"⚠️ Warnings for {member.display_name}",
            color=discord.Color.orange(),
        )
        for i, w in enumerate(warns, 1):
            embed.add_field(
                name=f"Warning #{i}",
                value=f"**Reason:** {w['reason']}\n**By:** {w['mod']}\n**When:** {w['timestamp']}",
                inline=False,
            )
        embed.set_footer(text=f"Total: {len(warns)} warning(s)")
        await ctx.send(embed=embed)

    @commands.command(name="clearwarn")
    @commands.has_permissions(kick_members=True)
    async def clearwarn(self, ctx: commands.Context, member: discord.Member, index: int = 0):
        """Clear warnings. Use index 0 (default) to clear all, or specify a number."""
        warns = _warnings.get(member.id, [])
        if not warns:
            await ctx.send(f"{member.mention} has no warnings to clear.")
            return

        if index == 0:
            count = len(warns)
            _warnings[member.id] = []
            await ctx.send(f"✅ Cleared all **{count}** warning(s) for {member.mention}.")
        else:
            if index < 1 or index > len(warns):
                await ctx.send(f"Invalid index. Provide a number between 1 and {len(warns)}, or 0 to clear all.")
                return
            removed = warns.pop(index - 1)
            await ctx.send(f"✅ Cleared warning #{index} (`{removed['reason']}`) for {member.mention}.")

    @warn.error
    @warnings.error
    @clearwarn.error
    async def warn_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need **Kick Members** permission to use this command.", delete_after=8)
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("Member not found. Please mention a valid user.", delete_after=8)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing argument. Usage: `!{ctx.invoked_with} <user> [reason]`", delete_after=8)
        else:
            await ctx.send(f"Error: {error}", delete_after=8)


async def setup(bot: commands.Bot):
    await bot.add_cog(Warnings(bot))
