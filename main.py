import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("DISCORD_TOKEN")

COGS = [
    "cogs.general",
    "cogs.moderation",
    "cogs.logging_cog",
    "cogs.welcome",
    "cogs.verification",
    "cogs.roblox_info",
    "cogs.debug",
    "cogs.antiraid",
    "cogs.warnings",
    "cogs.giveaway",
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)


async def main():
    async with bot:
        for cog in COGS:
            await bot.load_extension(cog)
        await bot.start(TOKEN)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN secret is not set.")
    asyncio.run(main())
