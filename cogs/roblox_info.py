import aiohttp
import discord
from discord.ext import commands

ROBLOX_USERNAMES_URL = "https://users.roblox.com/v1/usernames/users"
ROBLOX_USER_URL = "https://users.roblox.com/v1/users/{user_id}"
ROBLOX_FRIENDS_URL = "https://friends.roblox.com/v1/users/{user_id}/friends/count"
ROBLOX_FOLLOWERS_URL = "https://friends.roblox.com/v1/users/{user_id}/followers/count"
ROBLOX_FOLLOWING_URL = "https://friends.roblox.com/v1/users/{user_id}/followings/count"
ROBLOX_AVATAR_URL = (
    "https://thumbnails.roblox.com/v1/users/avatar-headshot"
    "?userIds={user_id}&size=150x150&format=Png"
)
ROBLOX_PROFILE_URL = "https://www.roblox.com/users/{user_id}/profile"


async def _fetch(session: aiohttp.ClientSession, url: str) -> dict | None:
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception:
        pass
    return None


class RobloxInfo(commands.Cog):
    """Roblox profile lookup commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="info")
    async def info(self, ctx: commands.Context, *, roblox_username: str = ""):
        """Look up a Roblox user's profile info."""
        if not roblox_username:
            await ctx.send("Usage: `!info <roblox_username>`")
            return

        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    ROBLOX_USERNAMES_URL,
                    json={"usernames": [roblox_username], "excludeBannedUsers": False},
                ) as resp:
                    if resp.status != 200:
                        await ctx.send("Could not reach the Roblox API. Try again later.")
                        return
                    data = await resp.json()
                    users = data.get("data", [])

                if not users:
                    await ctx.send(
                        f"No Roblox account found with the username **{roblox_username}**."
                    )
                    return

                user_id = users[0]["id"]

                profile, friends, followers, following, avatar = (
                    await _fetch(session, ROBLOX_USER_URL.format(user_id=user_id)),
                    await _fetch(session, ROBLOX_FRIENDS_URL.format(user_id=user_id)),
                    await _fetch(session, ROBLOX_FOLLOWERS_URL.format(user_id=user_id)),
                    await _fetch(session, ROBLOX_FOLLOWING_URL.format(user_id=user_id)),
                    await _fetch(session, ROBLOX_AVATAR_URL.format(user_id=user_id)),
                )

        if not profile:
            await ctx.send("Could not fetch profile data. Try again later.")
            return

        display_name = profile.get("displayName", profile.get("name", "N/A"))
        username = profile.get("name", "N/A")
        description = profile.get("description") or "No description."
        if len(description) > 200:
            description = description[:197] + "..."
        created_raw = profile.get("created", "")
        created = created_raw[:10] if created_raw else "Unknown"
        is_banned = profile.get("isBanned", False)

        friend_count = friends.get("count", "N/A") if friends else "N/A"
        follower_count = followers.get("count", "N/A") if followers else "N/A"
        following_count = following.get("count", "N/A") if following else "N/A"

        avatar_url = None
        if avatar:
            thumbs = avatar.get("data", [])
            if thumbs:
                avatar_url = thumbs[0].get("imageUrl")

        embed = discord.Embed(
            title=f"{display_name} (@{username})",
            url=ROBLOX_PROFILE_URL.format(user_id=user_id),
            description=description,
            color=discord.Color.red() if is_banned else discord.Color.blurple(),
        )
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)

        embed.add_field(name="User ID", value=str(user_id), inline=True)
        embed.add_field(name="Joined Roblox", value=created, inline=True)
        embed.add_field(name="Account Status", value="🚫 Banned" if is_banned else "✅ Active", inline=True)
        embed.add_field(name="Friends", value=str(friend_count), inline=True)
        embed.add_field(name="Followers", value=str(follower_count), inline=True)
        embed.add_field(name="Following", value=str(following_count), inline=True)
        embed.set_footer(text="Roblox Profile Lookup")

        await ctx.send(embed=embed)

    @info.error
    async def info_error(self, ctx: commands.Context, error):
        await ctx.send(f"Something went wrong: {error}")


async def setup(bot: commands.Bot):
    await bot.add_cog(RobloxInfo(bot))
