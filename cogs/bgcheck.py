import discord
from discord.ext import commands
from datetime import datetime, timezone
import aiohttp

BGCHECK_CHANNEL_ID    = 1500847577531420813
RECRUITMENT_ROLE_NAME = "Recruitment Permission"

BADGE_REQUIREMENT = 75
ACCOUNT_AGE_DAYS  = 350


async def get_user_id(session: aiohttp.ClientSession, username: str):
    url = "https://users.roblox.com/v1/usernames/users"
    async with session.post(url, json={"usernames": [username], "excludeBannedUsers": False}) as r:
        if r.status != 200:
            return None
        data  = await r.json()
        users = data.get("data", [])
        return users[0]["id"] if users else None


async def get_user_info(session: aiohttp.ClientSession, user_id: int):
    url = f"https://users.roblox.com/v1/users/{user_id}"
    async with session.get(url) as r:
        if r.status != 200:
            return None
        return await r.json()


async def count_badges(session: aiohttp.ClientSession, user_id: int):
    count  = 0
    cursor = ""
    while True:
        url = (
            f"https://badges.roblox.com/v1/users/{user_id}/badges"
            f"?limit=100&sortOrder=Asc&cursor={cursor}"
        )
        async with session.get(url) as r:
            if r.status != 200:
                break
            data      = await r.json()
            count    += len(data.get("data", []))
            next_page = data.get("nextPageCursor")
            if not next_page:
                break
            cursor = next_page
    return count


class BGCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="BGCheck")
    async def bgcheck(self, ctx, *, roblox_username: str):
        # Channel restriction
        if ctx.channel.id != BGCHECK_CHANNEL_ID:
            await ctx.send(
                f"This command can only be used in <#{BGCHECK_CHANNEL_ID}>.",
                delete_after=5
            )
            return

        # Role restriction
        role = discord.utils.get(ctx.guild.roles, name=RECRUITMENT_ROLE_NAME)
        if not role or role not in ctx.author.roles:
            await ctx.send(
                f"You need the **{RECRUITMENT_ROLE_NAME}** role to use this command.",
                delete_after=5
            )
            return

        await ctx.message.delete()
        loading = await ctx.send(f"🔍 Checking **{roblox_username}**...")

        async with aiohttp.ClientSession() as session:
            user_id = await get_user_id(session, roblox_username)
            if not user_id:
                await loading.edit(content=f"❌ Roblox user **{roblox_username}** not found.")
                return

            user_info    = await get_user_info(session, user_id)
            badge_count  = await count_badges(session, user_id)

        if not user_info:
            await loading.edit(content="❌ Failed to fetch user info.")
            return

        # Account age
        created_str  = user_info.get("created", "")
        display_name = user_info.get("displayName", roblox_username)
        try:
            created_dt   = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            account_days = (datetime.now(timezone.utc) - created_dt).days
        except Exception:
            account_days = 0

        badge_pass   = badge_count  >= BADGE_REQUIREMENT
        age_pass     = account_days >= ACCOUNT_AGE_DAYS
        overall_pass = badge_pass and age_pass

        if overall_pass:
            verdict_text  = "✅ **PASS** — This is likely their **main account**."
            verdict_color = 0x00ff00
        else:
            verdict_text  = "❌ **FAIL** — This may be an **alternative account**."
            verdict_color = 0xff0000

        embed = discord.Embed(
            title=f"🔎 Background Check — {roblox_username}",
            color=verdict_color
        )
        embed.add_field(name="Display Name", value=display_name,  inline=True)
        embed.add_field(name="User ID",      value=str(user_id),  inline=True)
        embed.add_field(name="\u200b",       value="\u200b",      inline=False)
        embed.add_field(
            name="Badges",
            value=f"{badge_count} {'✅' if badge_pass else '❌'}  *(need {BADGE_REQUIREMENT}+)*",
            inline=True
        )
        embed.add_field(
            name="Account Age",
            value=f"{account_days} days {'✅' if age_pass else '❌'}  *(need {ACCOUNT_AGE_DAYS}+)*",
            inline=True
        )
        embed.add_field(name="\u200b",  value="\u200b",    inline=False)
        embed.add_field(name="Verdict", value=verdict_text, inline=False)
        embed.set_footer(text=f"Checked by {ctx.author.display_name}")
        embed.set_thumbnail(
            url=f"https://thumbs.roblox.com/v1/users/{user_id}/avatar-headshot?size=150x150&format=Png&isCircular=false"
        )

        await loading.edit(content=None, embed=embed)

    @bgcheck.error
    async def bgcheck_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Usage: `!BGCheck <RobloxUsername>`", delete_after=5)
        else:
            await ctx.send(f"Error: {error}", delete_after=5)


async def setup(bot):
    await bot.add_cog(BGCheck(bot))
