import asyncio
import secrets
import datetime
import aiohttp
import discord
from discord.ext import commands
from utils.verify_log import VerifyEvent, record

EXPIRY_MINUTES = 10
ROBLOX_USERNAMES_URL = "https://users.roblox.com/v1/usernames/users"
ROBLOX_USER_URL = "https://users.roblox.com/v1/users/{user_id}"

# pending[discord_id] = {roblox_username, roblox_id, code, expires_at, original_nick}
pending: dict[int, dict] = {}
# verified[discord_id] = {roblox_username, original_nick}
verified: dict[int, dict] = {}


def _make_code() -> str:
    return "GAR-" + secrets.token_hex(4).upper()


async def _get_roblox_user(username: str) -> dict | None:
    print(f"[verify] Looking up Roblox user: {username}")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            ROBLOX_USERNAMES_URL,
            json={"usernames": [username], "excludeBannedUsers": True},
        ) as resp:
            print(f"[verify] Roblox username lookup status: {resp.status}")
            if resp.status != 200:
                return None
            data = await resp.json()
            users = data.get("data", [])
            print(f"[verify] Found users: {users}")
            return users[0] if users else None


async def _get_roblox_description(user_id: int) -> str | None:
    print(f"[verify] Fetching Roblox description for user ID: {user_id}")
    async with aiohttp.ClientSession() as session:
        async with session.get(ROBLOX_USER_URL.format(user_id=user_id)) as resp:
            print(f"[verify] Roblox profile fetch status: {resp.status}")
            if resp.status != 200:
                return None
            data = await resp.json()
            desc = data.get("description", "")
            print(f"[verify] Description fetched (length {len(desc)}): {repr(desc[:100])}")
            return desc


def _get_role(guild: discord.Guild, name: str) -> discord.Role | None:
    role = discord.utils.get(guild.roles, name=name)
    if role:
        print(f"[verify] Found role '{name}' (ID: {role.id})")
    else:
        print(f"[verify] Role '{name}' NOT found on server. Available roles: {[r.name for r in guild.roles]}")
    return role


async def _expire_pending(user_id: int, code: str):
    await asyncio.sleep(EXPIRY_MINUTES * 60)
    if user_id in pending and pending[user_id]["code"] == code:
        pending.pop(user_id, None)
        print(f"[verify] Code expired for user ID {user_id}")


class Verification(commands.Cog):
    """Roblox account verification system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="verify")
    async def verify(self, ctx: commands.Context, *, roblox_username: str = ""):
        print(f"[verify] !verify called by {ctx.author} (ID: {ctx.author.id}), username arg: '{roblox_username}'")

        if not roblox_username:
            await ctx.send("Please provide your Roblox username. Usage: `!verify <roblox_username>`")
            return

        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass

        roblox_user = await _get_roblox_user(roblox_username)
        if not roblox_user:
            print(f"[verify] No Roblox user found for '{roblox_username}'")
            await ctx.author.send(
                f"Could not find a Roblox account with the username **{roblox_username}**. "
                "Please check the spelling and try again."
            )
            return

        code = _make_code()
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=EXPIRY_MINUTES)
        print(f"[verify] Generated code {code} for {ctx.author} → Roblox user '{roblox_user['name']}' (ID: {roblox_user['id']})")

        pending[ctx.author.id] = {
            "roblox_username": roblox_user["name"],
            "roblox_id": roblox_user["id"],
            "code": code,
            "expires_at": expires_at,
            "original_nick": ctx.author.display_name,
        }

        asyncio.create_task(_expire_pending(ctx.author.id, code))

        embed = discord.Embed(title="Roblox Verification", color=discord.Color.blurple())
        embed.add_field(
            name="Step 1",
            value=f"Go to your [Roblox profile](https://www.roblox.com/users/{roblox_user['id']}/profile) and open **Edit Profile**.",
            inline=False,
        )
        embed.add_field(
            name="Step 2",
            value=f"Paste the following code **anywhere** in your profile description:\n\n```\n{code}\n```",
            inline=False,
        )
        embed.add_field(
            name="Step 3",
            value="Save your profile, then type `!done` in the server.",
            inline=False,
        )
        embed.set_footer(text=f"This code expires in {EXPIRY_MINUTES} minutes.")

        try:
            await ctx.author.send(embed=embed)
            await ctx.send(f"{ctx.author.mention} Check your DMs for verification instructions!", delete_after=8)
            print(f"[verify] Instructions DM'd to {ctx.author}")
        except discord.Forbidden:
            print(f"[verify] Could not DM {ctx.author} — DMs likely closed")
            await ctx.send(
                f"{ctx.author.mention} I couldn't DM you. Please enable DMs from server members and try again.",
                delete_after=10,
            )
            pending.pop(ctx.author.id, None)

    @commands.command(name="done")
    async def done(self, ctx: commands.Context):
        print(f"[verify] !done called by {ctx.author} (ID: {ctx.author.id})")
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass

        entry = pending.get(ctx.author.id)
        if not entry:
            print(f"[verify] No pending entry for {ctx.author}")
            await ctx.author.send("You don't have a pending verification. Start with `!verify <roblox_username>`.")
            return

        if datetime.datetime.utcnow() > entry["expires_at"]:
            print(f"[verify] Code expired for {ctx.author}")
            pending.pop(ctx.author.id, None)
            await ctx.author.send("Your verification code has expired. Please run `!verify <roblox_username>` again.")
            return

        print(f"[verify] Checking Roblox description for user ID {entry['roblox_id']}, expecting code: {entry['code']}")
        description = await _get_roblox_description(entry["roblox_id"])
        if description is None:
            await ctx.author.send("Could not fetch your Roblox profile. Please try again in a moment.")
            return

        if entry["code"] not in description:
            print(f"[verify] Code NOT found in description for {ctx.author}")
            await ctx.author.send(
                f"Your code **{entry['code']}** was not found in your Roblox profile description.\n"
                "Make sure you saved your profile after pasting the code, then try `!done` again."
            )
            return

        print(f"[verify] Code FOUND — proceeding to verify {ctx.author} as '{entry['roblox_username']}'")
        pending.pop(ctx.author.id, None)
        verified[ctx.author.id] = {
            "roblox_username": entry["roblox_username"],
            "original_nick": entry["original_nick"],
        }

        verified_role = _get_role(ctx.guild, "Verified")
        unverified_role = _get_role(ctx.guild, "Unverified")
        warnings = []

        if not verified_role:
            warnings.append("⚠️ Could not find a role named **Verified** — make sure it exists on the server.")

        try:
            if unverified_role and unverified_role in ctx.author.roles:
                await ctx.author.remove_roles(unverified_role)
                print(f"[verify] Removed Unverified role from {ctx.author}")
        except discord.Forbidden as e:
            print(f"[verify] ERROR removing Unverified role: {e}")
            warnings.append("⚠️ Missing permission to remove the **Unverified** role.")

        try:
            if verified_role:
                await ctx.author.add_roles(verified_role)
                print(f"[verify] Added Verified role to {ctx.author}")
        except discord.Forbidden as e:
            print(f"[verify] ERROR adding Verified role: {e}")
            warnings.append("⚠️ Missing permission to assign the **Verified** role — bot's role must be above **Verified** in the role list.")

        try:
            await ctx.author.edit(nick=entry["roblox_username"])
            print(f"[verify] Nickname changed to '{entry['roblox_username']}' for {ctx.author}")
        except discord.Forbidden as e:
            print(f"[verify] ERROR changing nickname: {e}")
            warnings.append("⚠️ Missing permission to change your nickname — bot's role must be above your highest role.")

        steps = [("✅", f"Roblox code found in profile description")]
        steps.append(("✅" if verified_role and not any("Verified** role" in w and "assign" in w for w in warnings) else "❌", "Verified role assigned"))
        steps.append(("✅" if not any("Unverified** role" in w and "remove" in w for w in warnings) else "❌", "Unverified role removed"))
        steps.append(("✅" if not any("nickname" in w for w in warnings) else "❌", f"Nickname changed to '{entry['roblox_username']}'"))
        record(VerifyEvent(
            timestamp=datetime.datetime.utcnow(),
            discord_user=str(ctx.author),
            roblox_username=entry["roblox_username"],
            steps=steps,
            success=len(warnings) == 0,
        ))

        description = f"You are now verified as **{entry['roblox_username']}** on Roblox."
        if not warnings:
            description += "\nYou have been given the **Verified** role and your nickname has been updated."

        embed = discord.Embed(
            title="Verification Successful!",
            description=description,
            color=discord.Color.green() if not warnings else discord.Color.orange(),
        )
        if warnings:
            embed.add_field(name="Action Required", value="\n".join(warnings), inline=False)
            embed.set_footer(text="Ask a server admin to fix the bot's permissions or role hierarchy.")

        await ctx.author.send(embed=embed)
        print(f"[verify] Verification complete for {ctx.author}. Warnings: {warnings}")

    @commands.command(name="unverify")
    async def unverify(self, ctx: commands.Context):
        print(f"[verify] !unverify called by {ctx.author} (ID: {ctx.author.id})")
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass

        if ctx.author.id not in verified:
            print(f"[verify] {ctx.author} is not in verified dict")
            await ctx.author.send("You are not currently verified.")
            return

        entry = verified.pop(ctx.author.id)
        verified_role = _get_role(ctx.guild, "Verified")
        unverified_role = _get_role(ctx.guild, "Unverified")
        warnings = []

        try:
            if verified_role and verified_role in ctx.author.roles:
                await ctx.author.remove_roles(verified_role)
                print(f"[verify] Removed Verified role from {ctx.author}")
        except discord.Forbidden as e:
            print(f"[verify] ERROR removing Verified role: {e}")
            warnings.append("⚠️ Missing permission to remove the **Verified** role.")

        try:
            if unverified_role:
                await ctx.author.add_roles(unverified_role)
                print(f"[verify] Added Unverified role to {ctx.author}")
            else:
                warnings.append("⚠️ Could not find a role named **Unverified** — make sure it exists on the server.")
        except discord.Forbidden as e:
            print(f"[verify] ERROR adding Unverified role: {e}")
            warnings.append("⚠️ Missing permission to assign the **Unverified** role.")

        try:
            await ctx.author.edit(nick=entry["original_nick"])
            print(f"[verify] Restored nickname to '{entry['original_nick']}' for {ctx.author}")
        except discord.Forbidden as e:
            print(f"[verify] ERROR restoring nickname: {e}")
            warnings.append("⚠️ Missing permission to restore your nickname.")

        msg = "You have been unverified."
        if not warnings:
            msg += " Your nickname has been restored and the **Unverified** role has been applied."
        else:
            msg += "\n\n" + "\n".join(warnings)
            msg += "\n\nAsk a server admin to check the bot's permissions and role hierarchy."

        await ctx.author.send(msg)

    @verify.error
    @done.error
    @unverify.error
    async def verification_error(self, ctx: commands.Context, error):
        print(f"[verify] Unhandled error in verification command: {type(error).__name__}: {error}")
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
        else:
            await ctx.send(f"Something went wrong: {error}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Verification(bot))
