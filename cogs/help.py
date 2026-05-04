import discord
from discord.ext import commands


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Remove the default help command
        self.bot.remove_command("help")

    @commands.command(name="help")
    async def help(self, ctx):
        embed = discord.Embed(
            title="📖 GAR Bot — Command List",
            description="Here are all available commands:",
            color=0x2f3136
        )

        # Dynamically pull commands grouped by cog
        cog_order = [
            "Announcements",
            "BGCheck",
            "Moderation",
            "Warnings",
            "AntiRaid",
            "Giveaway",
            "General",
            "Welcome",
            "Verification",
            "RobloxInfo",
            "Logging",
            "Debug",
        ]

        shown_cogs = set()

        # Show ordered cogs first
        for cog_name in cog_order:
            cog = self.bot.get_cog(cog_name)
            if not cog:
                continue
            cmds = [c for c in cog.get_commands() if not c.hidden]
            if not cmds:
                continue
            shown_cogs.add(cog_name)
            value = "\n".join(f"`!{c.name}` — {c.brief or c.help or 'No description'}" for c in cmds)
            embed.add_field(name=f"━━ {cog_name}", value=value, inline=False)

        # Catch any remaining cogs not in the order list
        for cog_name, cog in self.bot.cogs.items():
            if cog_name in shown_cogs or cog_name == "Help":
                continue
            cmds = [c for c in cog.get_commands() if not c.hidden]
            if not cmds:
                continue
            value = "\n".join(f"`!{c.name}` — {c.brief or c.help or 'No description'}" for c in cmds)
            embed.add_field(name=f"━━ {cog_name}", value=value, inline=False)

        embed.set_footer(text=f"Requested by {ctx.author.display_name} • GAR Bot")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Help(bot))
