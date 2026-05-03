import asyncio
import datetime
import discord
from collections import defaultdict, deque
from discord.ext import commands

JOIN_FLOOD_COUNT = 5
JOIN_FLOOD_SECONDS = 10
MIN_ACCOUNT_AGE_DAYS = 3

MAX_MENTIONS = 5
SPAM_MSG_COUNT = 5
SPAM_MSG_SECONDS = 3

MENTION_MUTE_STEPS = [5, 10, 20, 30]

lockdown_active = False
lockdown_reason = ""

_join_times = deque()
_msg_times = defaultdict(lambda: deque())
_mention_offenses = {}
_active_mutes = {}


def _log_channel(guild: discord.Guild):
    import os
    cid = os.environ.get("LOG_CHANNEL_ID")
    return guild.get_channel(int(cid)) if cid else None


async def _send_log(guild: discord.Guild, embed: discord.Embed):
    ch = _log_channel(guild)
    if ch:
        try:
            await ch.send(embed=embed)
        except discord.Forbidden:
            pass


async def _apply_lockdown(guild: discord.Guild, reason: str):
    global lockdown_active, lockdown_reason
    lockdown_active = True
    lockdown_reason = reason

    everyone = guild.default_role

    try:
        await everyone.edit(send_messages=False)
    except discord.Forbidden:
        print("[antiraid] Missing permission to edit @everyone")

    embed = discord.Embed(
        title="🔒 Lockdown Activated",
        description=f"Reason: {reason}",
        color=discord.Color.red(),
        timestamp=datetime.datetime.utcnow(),
    )
    await _send_log(guild, embed)


async def _lift_lockdown(guild: discord.Guild, moderator: str):
    global lockdown_active, lockdown_reason
    lockdown_active = False
    lockdown_reason = ""

    try:
        await guild.default_role.edit(send_messages=True)
    except discord.Forbidden:
        print("[antiraid] Missing permission to restore @everyone")

    embed = discord.Embed(
        title="🔓 Lockdown Lifted",
        description=f"Lifted by {moderator}",
        color=discord.Color.green(),
        timestamp=datetime.datetime.utcnow(),
    )
    await _send_log(guild, embed)


def _next_mute_duration(offense: int):
    return MENTION_MUTE_STEPS[min(offense - 1, len(MENTION_MUTE_STEPS) - 1)]


class AntiRaid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── JOIN FLOOD ─────────────────────
    @commands.Cog.listener()
    async def on_member_join(self, member):
        now = datetime.datetime.utcnow()

        _join_times.append(now)
        cutoff = now - datetime.timedelta(seconds=JOIN_FLOOD_SECONDS)

        while _join_times and _join_times[0] < cutoff:
            _join_times.popleft()

        if len(_join_times) >= JOIN_FLOOD_COUNT and not lockdown_active:
            await _apply_lockdown(
                member.guild,
                "Join flood detected"
            )

    # ── MESSAGE HANDLER ─────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # MASS MENTIONS
        mention_count = len(message.mentions) + len(message.role_mentions)

        if mention_count >= MAX_MENTIONS:
            try:
                await message.delete()
            except discord.Forbidden:
                pass

            muted_role = discord.utils.get(message.guild.roles, name="Muted")
            if not muted_role:
                return

            uid = message.author.id
            _mention_offenses[uid] = _mention_offenses.get(uid, 0) + 1
            offense = _mention_offenses[uid]

            minutes = _next_mute_duration(offense)
            expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)

            try:
                await message.author.add_roles(muted_role, reason="Mass mention")
            except discord.Forbidden:
                return

            _active_mutes[uid] = {
                "expires_at": expires,
                "minutes": minutes,
            }

            await asyncio.sleep(1)

        # IMPORTANT: DO NOT process commands here (handled globally in main.py)
        return

    # ── COMMANDS ─────────────────────
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def lockdown(self, ctx, *, reason="Manual"):
        await _apply_lockdown(ctx.guild, reason)
        await ctx.send("Lockdown enabled", delete_after=5)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unlockdown(self, ctx):
        await _lift_lockdown(ctx.guild, str(ctx.author))
        await ctx.send("Lockdown disabled", delete_after=5)


async def setup(bot):
    await bot.add_cog(AntiRaid(bot))        mention_count = len(message.mentions) + len(message.role_mentions)

        if mention_count >= MAX_MENTIONS:
            try:
                await message.delete()
            except discord.Forbidden:
                pass

            muted_role = discord.utils.get(message.guild.roles, name="Muted")
            if not muted_role:
                return

            uid = message.author.id
            _mention_offenses[uid] = _mention_offenses.get(uid, 0) + 1
            offense = _mention_offenses[uid]

            minutes = _next_mute_duration(offense)
            expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)

            try:
                await message.author.add_roles(muted_role, reason="Mass mention")
            except discord.Forbidden:
                return

            _active_mutes[uid] = {
                "expires_at": expires,
                "minutes": minutes,
            }

            await asyncio.sleep(1)

        # IMPORTANT: DO NOT process commands here (handled globally in main.py)
        return

    # ── COMMANDS ─────────────────────
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def lockdown(self, ctx, *, reason="Manual"):
        await _apply_lockdown(ctx.guild, reason)
        await ctx.send("Lockdown enabled", delete_after=5)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unlockdown(self, ctx):
        await _lift_lockdown(ctx.guild, str(ctx.author))
        await ctx.send("Lockdown disabled", delete_after=5)


async def setup(bot):
    await bot.add_cog(AntiRaid(bot))    _active_mutes[member.id] = {
        "expires_at": expires_at,
        "minutes": minutes,
        "guild_id": guild.id,
    }

    try:
        await member.add_roles(muted_role, reason=f"Mass mention — offense #{offense} ({minutes}min mute)")
        print(f"[antiraid] Muted {member} for {minutes}min (offense #{offense})")
    except discord.Forbidden:
        print(f"[antiraid] Could not mute {member} — missing Manage Roles permission")
        _active_mutes.pop(member.id, None)
        return False

    asyncio.create_task(_expire_mention_mute(member.id, guild.id, muted_role.id, expires_at))
    return True


async def _expire_mention_mute(user_id: int, guild_id: int, muted_role_id: int, expires_at: datetime.datetime):
    """Wait until mute expires then remove the role."""
    delay = (expires_at - datetime.datetime.utcnow()).total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)

    # If the mute was refreshed (e.g. they rejoined), skip removal
    record = _active_mutes.get(user_id)
    if record and record["expires_at"] > datetime.datetime.utcnow():
        return

    _active_mutes.pop(user_id, None)

    from discord.utils import get as dget
    # Attempt to find the guild and member
    for guild in discord.utils.find(lambda g: g.id == guild_id, []):
        pass
    # Use bot via a global reference approach — handled inside the cog listener instead


class AntiRaid(commands.Cog):
    """Anti-raid and server security features."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _unmute_after(self, member: discord.Member, guild: discord.Guild, minutes: int, expires_at: datetime.datetime):
        """Wait for mute to expire and remove the Muted role."""
        delay = (expires_at - datetime.datetime.utcnow()).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)

        current = _active_mutes.get(member.id)
        if current and current["expires_at"] > datetime.datetime.utcnow():
            print(f"[antiraid] Mute for {member} was refreshed — skipping unmute")
            return

        _active_mutes.pop(member.id, None)

        # Re-fetch member in case they left/rejoined
        try:
            fresh = guild.get_member(member.id) or await guild.fetch_member(member.id)
        except (discord.NotFound, discord.HTTPException):
            print(f"[antiraid] Member {member.id} not found for unmute — they may have left")
            return

        muted_role = discord.utils.get(guild.roles, name="Muted")
        if muted_role and muted_role in fresh.roles:
            try:
                await fresh.remove_roles(muted_role, reason="Mention mute expired")
                print(f"[antiraid] Unmuted {fresh} after {minutes}min")
            except discord.Forbidden:
                print(f"[antiraid] Could not unmute {fresh}")

    # ── Join flood + rejoin punishment ────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        now = datetime.datetime.utcnow()

        # Check for active punishment from before they left
        punishment = _active_mutes.get(member.id)
        if punishment and punishment["expires_at"] > now:
            remaining = int((punishment["expires_at"] - now).total_seconds() / 60) + 1
            muted_role = discord.utils.get(member.guild.roles, name="Muted")
            if muted_role:
                try:
                    await member.add_roles(muted_role, reason="Rejoined with active mention mute")
                    print(f"[antiraid] Reapplied mute to rejoining member {member} ({remaining}min remaining)")
                except discord.Forbidden:
                    print("[antiraid] Could not reapply mute on rejoin")

            try:
                await member.send(
                    f"Rejoining the server won't evade your punishment.\n"
                    f"You still have **{remaining} minute(s)** remaining on your mute."
                )
            except discord.Forbidden:
                pass

            asyncio.create_task(
                self._unmute_after(member, member.guild, punishment["minutes"], punishment["expires_at"])
            )

            embed = discord.Embed(
                title="🔄 Mute Reapplied on Rejoin",
                description=f"{member.mention} (`{member}`) rejoined with an active mute. Punishment reapplied ({remaining}min remaining).",
                color=discord.Color.red(),
                timestamp=now,
            )
            await _send_log(member.guild, embed)
            return

        # New account filter
        account_age = (now - member.created_at.replace(tzinfo=None)).days
        if account_age < MIN_ACCOUNT_AGE_DAYS:
            print(f"[antiraid] Kicking new account {member} (age: {account_age}d)")
            try:
                await member.send(
                    f"Your account is too new to join this server (minimum age: {MIN_ACCOUNT_AGE_DAYS} days). "
                    "Please try again later."
                )
            except discord.Forbidden:
                pass
            try:
                await member.kick(reason=f"Account too new ({account_age} days old, minimum {MIN_ACCOUNT_AGE_DAYS})")
            except discord.Forbidden:
                print("[antiraid] Could not kick new account — missing Kick Members permission")
            embed = discord.Embed(
                title="🚫 New Account Kicked",
                description=f"{member.mention} (`{member}`) was kicked — account only {account_age} day(s) old.",
                color=discord.Color.orange(),
                timestamp=now,
            )
            await _send_log(member.guild, embed)
            return

        # Join flood detection
        _join_times.append(now)
        cutoff = now - datetime.timedelta(seconds=JOIN_FLOOD_SECONDS)
        while _join_times and _join_times[0] < cutoff:
            _join_times.popleft()

        if len(_join_times) >= JOIN_FLOOD_COUNT and not lockdown_active:
            await _apply_lockdown(
                member.guild,
                f"Join flood detected — {len(_join_times)} members joined in {JOIN_FLOOD_SECONDS}s"
            )

    # ── Mass mention guard (escalating mutes) ────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        mention_count = len(message.mentions) + len(message.role_mentions)
        if mention_count >= MAX_MENTIONS:
            print(f"[antiraid] Mass mention by {message.author} ({mention_count} mentions) — triggering mute")

            try:
                await message.delete()
            except discord.Forbidden:
                pass

            # Check Muted role exists before doing anything else
            muted_role = discord.utils.get(message.guild.roles, name="Muted")
            if not muted_role:
                print("[antiraid] ERROR: 'Muted' role not found — cannot apply mention mute")
                await message.channel.send(
                    f"⚠️ {message.author.mention} triggered the mass-mention guard but the **Muted** role doesn't exist. "
                    "Please create a role named `Muted` and deny Send Messages in channels.",
                    delete_after=15,
                )
                return

            uid = message.author.id
            _mention_offenses[uid] = _mention_offenses.get(uid, 0) + 1
            offense = _mention_offenses[uid]
            mute_minutes = _next_mute_duration(offense)
            next_minutes = _next_mute_duration(offense + 1)
            is_max = mute_minutes == MENTION_MUTE_STEPS[-1]

            expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=mute_minutes)
            muted = await self._do_mention_mute(message.author, message.guild, muted_role, mute_minutes, offense, expires_at)

            if muted:
                asyncio.create_task(
                    self._unmute_after(message.author, message.guild, mute_minutes, expires_at)
                )
                # Visible channel feedback
                if is_max:
                    channel_msg = (
                        f"🔇 {message.author.mention} has been muted for **{mute_minutes} minutes** "
                        f"for mass mentioning (offense #{offense} — maximum reached)."
                    )
                else:
                    channel_msg = (
                        f"🔇 {message.author.mention} has been muted for **{mute_minutes} minutes** "
                        f"for mass mentioning (offense #{offense})."
                    )
                await message.channel.send(channel_msg, delete_after=15)

            # DM the user
            if is_max:
                dm_text = (
                    f"You have been muted for **{mute_minutes} minutes** for mass mentioning in "
                    f"**{message.guild.name}** (offense #{offense}).\n\n"
                    f"This is the maximum mute duration. Any further offenses will result in a **{mute_minutes}-minute mute**."
                )
            else:
                dm_text = (
                    f"You have been muted for **{mute_minutes} minutes** for mass mentioning in "
                    f"**{message.guild.name}** (offense #{offense}).\n\n"
                    f"⚠️ **Warning:** Your next offense will result in a **{next_minutes}-minute mute**."
                )

            try:
                await message.author.send(dm_text)
            except discord.Forbidden:
                pass

            embed = discord.Embed(
                title="🔇 Mass Mention — Mute Applied",
                description=(
                    f"{message.author.mention} (`{message.author}`) muted for **{mute_minutes}min** "
                    f"(offense #{offense}, {mention_count} mentions)."
                ),
                color=discord.Color.orange(),
                timestamp=datetime.datetime.utcnow(),
            )
            embed.add_field(name="Next offense", value=f"{next_minutes} min" if not is_max else "30 min (max)", inline=True)
            await _send_log(message.guild, embed)
            return

        # Spam guard
        now = datetime.datetime.utcnow()
        uid = message.author.id
        _msg_times[uid].append(now)
        cutoff = now - datetime.timedelta(seconds=SPAM_MSG_SECONDS)
        while _msg_times[uid] and _msg_times[uid][0] < cutoff:
            _msg_times[uid].popleft()

        if len(_msg_times[uid]) >= SPAM_MSG_COUNT:
            _msg_times[uid].clear()
            print(f"[antiraid] Spam detected from {message.author} — muting for 60s")
            muted_role = discord.utils.get(message.guild.roles, name="Muted")
            if muted_role:
                try:
                    await message.author.add_roles(muted_role, reason="Spam detected by anti-raid")
                    await message.channel.send(
                        f"{message.author.mention} has been muted for 60 seconds due to spam.",
                        delete_after=10,
                    )
                    embed = discord.Embed(
                        title="🔇 Spam Mute Applied",
                        description=f"{message.author.mention} (`{message.author}`) was auto-muted for 60s — spam detected.",
                        color=discord.Color.orange(),
                        timestamp=datetime.datetime.utcnow(),
                    )
                    await _send_log(message.guild, embed)
                    await asyncio.sleep(60)
                    await message.author.remove_roles(muted_role, reason="Auto-mute expired")
                except discord.Forbidden:
                    print("[antiraid] Could not mute spammer — missing Manage Roles permission")
            else:
                print("[antiraid] No 'Muted' role found — spam mute skipped")

    async def _do_mention_mute(self, member: discord.Member, guild: discord.Guild, muted_role: discord.Role, minutes: int, offense: int, expires_at: datetime.datetime) -> bool:
        _active_mutes[member.id] = {
            "expires_at": expires_at,
            "minutes": minutes,
            "guild_id": guild.id,
        }

        try:
            await member.add_roles(muted_role, reason=f"Mass mention — offense #{offense} ({minutes}min mute)")
            print(f"[antiraid] Muted {member} for {minutes}min (offense #{offense})")
            return True
        except discord.Forbidden:
            print(f"[antiraid] Could not mute {member} — missing Manage Roles permission")
            _active_mutes.pop(member.id, None)
            return False

    # ── Manual lockdown commands ──────────────────────────────────────────────
    @commands.command(name="lockdown")
    @commands.has_permissions(administrator=True)
    async def lockdown_cmd(self, ctx: commands.Context, *, reason: str = "Manual lockdown by admin"):
        """Lock the server (admin only)."""
        await ctx.message.delete()
        if lockdown_active:
            await ctx.send("⚠️ Server is already in lockdown.", delete_after=8)
            return
        await _apply_lockdown(ctx.guild, reason)
        await ctx.send("🔒 Server is now in lockdown.", delete_after=8)

    @commands.command(name="unlockdown")
    @commands.has_permissions(administrator=True)
    async def unlockdown_cmd(self, ctx: commands.Context):
        """Lift the server lockdown (admin only)."""
        await ctx.message.delete()
        if not lockdown_active:
            await ctx.send("ℹ️ Server is not currently in lockdown.", delete_after=8)
            return
        await _lift_lockdown(ctx.guild, str(ctx.author))
        await ctx.send("🔓 Lockdown lifted.", delete_after=8)

    @lockdown_cmd.error
    @unlockdown_cmd.error
    async def lockdown_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need Administrator permission to use this command.", delete_after=8)
        else:
            await ctx.send(f"Error: {error}", delete_after=8)


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiRaid(bot))
