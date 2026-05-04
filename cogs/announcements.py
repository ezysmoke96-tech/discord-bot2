import discord
from discord.ext import commands

SSU_SSD_CHANNEL_ID = 1500845107736215724

ROBLOX_LINK = (
    "https://www.roblox.com/games/5041144419/SCP-Roleplay"
    "?gameSetTypeId=100000003&homePageSessionInfo=af204f3b-9369-4fdc-95f3-a89b59a2c816"
    "&isAd=false&numberOfLoadedTiles=135&page=homePage&placeId=5041144419"
    "&playContext=homePage&position=0&positionInRow=0&rowOnPage=1"
    "&sortPos=1&sortSubId=&universeId=1742264997"
)


class Announcements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── !announce ─────────────────────────────────────────────────────────────
    # Usage: !announce #channel <ping|none> <Title> <Text> [image|none]
    # For multi-word title or text, wrap in "quotes"
    # Examples:
    #   !announce #general @everyone Test Wassup none
    #   !announce #general none "Server Update" "We have a new update today!" none
    #   !announce #events @everyone "Event Night" "Join us at 8PM!" https://i.imgur.com/abc.gif
    @commands.command(name="announce")
    @commands.has_permissions(manage_messages=True)
    async def announce(self, ctx, channel: discord.TextChannel, ping: str, title: str, text: str, image: str = "none"):
        await ctx.message.delete()

        embed = discord.Embed(title=title, description=text, color=0xffd700)
        embed.set_footer(text=f"Announced by {ctx.author.display_name}")

        if image.lower() != "none":
            embed.set_image(url=image)

        content = None if ping.lower() == "none" else ping
        await channel.send(content=content, embed=embed)

    # ── !SSU ──────────────────────────────────────────────────────────────────
    # Usage: !SSU <ServerName> [note]
    @commands.command(name="SSU")
    @commands.has_permissions(manage_messages=True)
    async def ssu(self, ctx, sv: str, *, note: str = "N/A"):
        await ctx.message.delete()

        channel = self.bot.get_channel(SSU_SSD_CHANNEL_ID)
        if not channel:
            await ctx.send("SSU channel not found.", delete_after=10)
            return

        embed = discord.Embed(title="🟢 SERVER START UP!", color=0x00ff00)
        embed.add_field(name="HOST",        value=ctx.author.mention, inline=False)
        embed.add_field(name="Server Name", value=sv,                 inline=False)
        embed.add_field(name="Link",        value=ROBLOX_LINK,        inline=False)
        embed.add_field(name="Note",        value=note,               inline=False)

        await channel.send(content="@everyone", embed=embed)

    # ── !SSD ──────────────────────────────────────────────────────────────────
    @commands.command(name="SSD")
    @commands.has_permissions(manage_messages=True)
    async def ssd(self, ctx):
        await ctx.message.delete()

        channel = self.bot.get_channel(SSU_SSD_CHANNEL_ID)
        if not channel:
            await ctx.send("SSD channel not found.", delete_after=10)
            return

        embed = discord.Embed(title="🔴 SERVER SHUT DOWN!", color=0xff0000)
        embed.add_field(name="EXECUTED BY", value=ctx.author.mention, inline=False)
        embed.add_field(
            name="Note",
            value="Hope you had a lot of fun playing on our server, wait for a new SSU to be hosted soon, hope to see you there!",
            inline=False
        )

        await channel.send(content="@everyone", embed=embed)

    @announce.error
    @ssu.error
    @ssd.error
    async def cmd_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.", delete_after=5)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                "Usage: `!announce #channel <@ping|none> <Title> <Text> <ImageURL|none>`\n"
                "Wrap multi-word fields in quotes: `\"My Title Here\"`",
                delete_after=10
            )
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send("Channel not found. Tag it like `#channel-name`.", delete_after=5)
        else:
            await ctx.send(f"Error: {error}", delete_after=5)


async def setup(bot):
    await bot.add_cog(Announcements(bot))
