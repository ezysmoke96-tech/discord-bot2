import os
import discord
from discord.ext import commands


WELCOME_GIF = "https://media.giphy.com/media/0tZMVR5VXVuV6FQpaU/giphy.gif"

WELCOME_MESSAGE = (
    "Welcome to the Grand Army of the Republic, {mention}! "
    "We're grateful to have you here with us and we hope that "
    "you'll be doing great in this community. "
    "If you'd like to join a division you'll have to get enlisted into the army!"
)

GOODBYE_DM = (
    "Hey {name}, we noticed you've left the Grand Army of the Republic. "
    "We're sad to see you go, but we wish you all the best in whatever "
    "comes next. You're always welcome back — the GAR never forgets its soldiers. "
    "Take care, trooper!"
)


class Welcome(commands.Cog):
    """Welcome and goodbye messages."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_welcome_channel(self, guild: discord.Guild):
        channel_id = os.environ.get("WELCOME_CHANNEL_ID")
        if not channel_id:
            return None
        return guild.get_channel(int(channel_id))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = self._get_welcome_channel(member.guild)
        if not channel:
            return

        embed = discord.Embed(
            title="Welcome to the Grand Army of the Republic!",
            description=WELCOME_MESSAGE.format(mention=member.mention),
            color=discord.Color.gold(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url=WELCOME_GIF)
        embed.set_footer(text=f"Member #{member.guild.member_count}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        try:
            embed = discord.Embed(
                title="Farewell, Trooper",
                description=GOODBYE_DM.format(name=member.display_name),
                color=discord.Color.dark_gray(),
            )
            embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else None)
            await member.send(embed=embed)
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
