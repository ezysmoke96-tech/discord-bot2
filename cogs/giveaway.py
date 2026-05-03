import asyncio
import datetime
import random
import discord
from discord.ext import commands

_active_giveaways: dict[int, dict] = {}


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


class Giveaway(commands.Cog):
    """Giveaway system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="giveaway", aliases=["gstart"])
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self, ctx: commands.Context, duration: str, *, prize: str):
        """Start a giveaway. Usage: !giveaway <duration> <prize> e.g. !giveaway 1h Robux"""
        seconds = _parse_duration(duration)
        if not seconds or seconds < 10:
            await ctx.send(
                "❌ Invalid duration. Use `10s`, `5m`, `1h`, `2d` (minimum 10 seconds).\n"
                "Example: `!giveaway 1h Robux`",
                delete_after=10,
            )
            return

        ends_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)
        unix_ts = int(ends_at.timestamp())

        embed = discord.Embed(
            title="🎉 GIVEAWAY 🎉",
            description=(
                f"**Prize:** {prize}\n\n"
                f"React with 🎉 to enter!\n\n"
                f"**Ends:** <t:{unix_ts}:R> (<t:{unix_ts}:f>)\n"
                f"**Hosted by:** {ctx.author.mention}"
            ),
            color=discord.Color.gold(),
            timestamp=ends_at,
        )
        embed.set_footer(text="Ends at")

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        msg = await ctx.channel.send(embed=embed)
        await msg.add_reaction("🎉")

        _active_giveaways[msg.id] = {
            "prize": prize,
            "channel_id": ctx.channel.id,
            "guild_id": ctx.guild.id,
            "host_id": ctx.author.id,
            "ends_at": ends_at,
            "active": True,
            "winner_id": None,
        }

        asyncio.create_task(self._end_giveaway(msg.id, ctx.channel.id, seconds, prize))

    async def _end_giveaway(self, message_id: int, channel_id: int, delay: int, prize: str):
        await asyncio.sleep(delay)
        giveaway = _active_giveaways.get(message_id)
        if not giveaway or not giveaway["active"]:
            return
        channel = self.bot.get_channel(channel_id)
        if channel:
            await self._conclude_giveaway(message_id, channel, prize)

    async def _conclude_giveaway(self, message_id: int, channel: discord.TextChannel, prize: str):
        giveaway = _active_giveaways.get(message_id)
        if not giveaway:
            return

        giveaway["active"] = False

        try:
            msg = await channel.fetch_message(message_id)
        except (discord.NotFound, discord.HTTPException):
            return

        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        users = [u async for u in reaction.users() if not u.bot] if reaction else []

        if not users:
            ended_embed = discord.Embed(
                title="🎉 GIVEAWAY ENDED",
                description=f"**Prize:** {prize}\n\nNo valid entries — no winner was drawn.",
                color=discord.Color.greyple(),
                timestamp=datetime.datetime.utcnow(),
            )
            ended_embed.set_footer(text="Giveaway ended")
            await msg.edit(embed=ended_embed)
            await channel.send(f"The giveaway for **{prize}** ended with no valid entries.")
            return

        winner = random.choice(users)
        giveaway["winner_id"] = winner.id

        ended_embed = discord.Embed(
            title="🎉 GIVEAWAY ENDED 🎉",
            description=(
                f"**Prize:** {prize}\n\n"
                f"🏆 **Winner:** {winner.mention}\n\n"
                f"Congratulations!"
            ),
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow(),
        )
        ended_embed.set_footer(text="Giveaway ended")
        await msg.edit(embed=ended_embed)
        await channel.send(f"🎉 Congratulations {winner.mention}! You won **{prize}**!")

        try:
            await winner.send(
                f"🎉 You won the giveaway for **{prize}** in **{channel.guild.name}**! Congratulations!"
            )
        except discord.Forbidden:
            pass

    @commands.command(name="gend")
    @commands.has_permissions(manage_guild=True)
    async def gend(self, ctx: commands.Context, message_id: int = None):
        """End a giveaway early. Omit message ID to end the latest one in this channel."""
        if message_id is None:
            active = [
                gid for gid, g in _active_giveaways.items()
                if g["active"] and g["channel_id"] == ctx.channel.id
            ]
            if not active:
                await ctx.send("No active giveaways found in this channel.", delete_after=8)
                return
            message_id = active[-1]

        giveaway = _active_giveaways.get(message_id)
        if not giveaway or not giveaway["active"]:
            await ctx.send("That giveaway is not active or was not found.", delete_after=8)
            return

        await self._conclude_giveaway(message_id, ctx.channel, giveaway["prize"])

    @commands.command(name="greroll")
    @commands.has_permissions(manage_guild=True)
    async def greroll(self, ctx: commands.Context, message_id: int = None):
        """Reroll the winner of an ended giveaway."""
        if message_id is None:
            ended = [
                gid for gid, g in _active_giveaways.items()
                if not g["active"] and g["channel_id"] == ctx.channel.id
            ]
            if not ended:
                await ctx.send("No ended giveaways found in this channel.", delete_after=8)
                return
            message_id = ended[-1]

        giveaway = _active_giveaways.get(message_id)
        if not giveaway:
            await ctx.send("Giveaway not found.", delete_after=8)
            return

        giveaway["active"] = False
        await self._conclude_giveaway(message_id, ctx.channel, giveaway["prize"])

    @giveaway.error
    @gend.error
    @greroll.error
    async def giveaway_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need **Manage Server** permission to use this command.", delete_after=8)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                "Usage: `!giveaway <duration> <prize>`\nExample: `!giveaway 1h 1000 Robux`",
                delete_after=10,
            )
        else:
            await ctx.send(f"Error: {error}", delete_after=8)


async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaway(bot))
