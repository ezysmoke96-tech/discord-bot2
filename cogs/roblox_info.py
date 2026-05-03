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

VERIFIED_ROLE_NAME = "Verified"


async def _fetch(session: aiohttp.ClientSession, url: str):
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
    except:
        pass
    return None


class RobloxInfo(commands.Cog):
    """Roblox profile lookup commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="info")
    async def info(self, ctx: commands.Context, *, roblox_username: str = ""):
        if not roblox_username:
            await ctx.send("Usage: `!info <roblox_username>`")
            return

        member = ctx.author
        verified_role = discord.utils.get(ctx.guild.roles, name=VERIFIED_ROLE_NAME)
        is_verified_discord = verified_role in member.roles if verified_role else False

        async with ctx.typing():
            async with aiohttp.ClientSession() as session:

                async with session.post(
                    ROBLOX_USERNAMES_URL,
                    json={"usernames": [roblox_username], "excludeBannedUsers": False},
                ) as resp:
                    if resp.status != 200:
                        await ctx.send("Could not reach Roblox API.")
                        return

                    data = await resp.json()
                    users = data.get("data", [])

                if not users:
                    await ctx.send(f"No Roblox user found: **{roblox_username}**")
                    return

                user_id = users[0]["id"]

                profile = await _fetch(session, ROBLOX_USER_URL.format(user_id=user_id))
                friends = await _fetch(session, ROBLOX_FRIENDS_URL.format(user_id=user_id))
                followers = await _fetch(session, ROBLOX_FOLLOWERS_URL.format(user_id=user_id))
                following = await _fetch(session, ROBLOX_FOLLOWING_URL.format(user_id=user_id))
                avatar = await _fetch(session, ROBLOX_AVATAR_URL.format(user_id=user_id))

        if not profile:
            await ctx.send("Failed to load Roblox profile.")
            return

        display_name = profile.get("displayName", "N/A")
        username = profile.get("name", "N/A")

        description = profile.get("description") or "No description."
        if len(description) > 200:
            description = description[:197] + "..."

        created = profile.get("created", "Unknown")[:10]
        is_banned = profile.get("isBanned", False)
        is_verified_roblox = profile.get("hasVerifiedBadge", False)

        friend_count = friends.get("count", "N/A") if friends else "N/A"
        follower_count = followers.get("count", "N/A") if followers else "N/A"
        following_count = following.get("count", "N/A") if following else "N/A"

        avatar_url = None
        if avatar:
            data = avatar.get("data", [])
            if data:
                avatar_url = data[0].get("imageUrl")

        embed = discord.Embed(
            title=f"{display_name} (@{username})",
            url=ROBLOX_PROFILE_URL.format(user_id=user_id),
            description=description,
            color=discord.Color.red() if is_banned else discord.Color.blurple(),
        )

        if avatar_url:
            embed.set_thumbnail(url=avatar_url)

        embed.add_field(name="User ID", value=str(user_id), inline=True)
        embed.add_field(name="Joined", value=created, inline=True)
        embed.add_field(
            name="Roblox Status",
            value="🚫 Banned" if is_banned else "✅ Active",
            inline=True,
        )

        embed.add_field(
            name="Roblox Verified",
            value="✅ Yes" if is_verified_roblox else "❌ No",
            inline=True,
        )

        embed.add_field(
            name="Discord Verified",
            value="✅ Yes" if is_verified_discord else "❌ No",
            inline=True,
        )

        embed.add_field(name="Friends", value=str(friend_count), inline=True)
        embed.add_field(name="Followers", value=str(follower_count), inline=True)
        embed.add_field(name="Following", value=str(following_count), inline=True)

        embed.set_footer(text="Roblox Info System")

        await ctx.send(embed=embed)

    @info.error
    async def info_error(self, ctx: commands.Context, error):
        await ctx.send(f"Error: {error}")


async def setup(bot: commands.Bot):
    await bot.add_cog(RobloxInfo(bot))
