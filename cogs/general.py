import discord
from discord.ext import commands


class General(commands.Cog):
    """General purpose commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context):
        """Check the bot's latency."""
        await ctx.send(f"Pong! Latency: {round(self.bot.latency * 1000)}ms")

    @commands.command(name="hello")
    async def hello(self, ctx: commands.Context):
        """Say hello to the bot."""
        await ctx.send(f"Hello, {ctx.author.display_name}!")

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context):
        """Show all available commands."""
        embed = discord.Embed(
            title="Bot Commands",
            description="Here's everything I can do:",
            color=discord.Color.blurple(),
        )

        for cog_name, cog in self.bot.cogs.items():
            cog_commands = cog.get_commands()
            if not cog_commands:
                continue
            lines = [
                f"`!{cmd.name}` — {cmd.help or 'No description'}"
                for cmd in cog_commands
            ]
            embed.add_field(
                name=cog_name,
                value="\n".join(lines),
                inline=False,
            )

        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
