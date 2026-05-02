import os
import aiohttp
import discord
from discord.ext import commands
from utils.verify_log import get_recent
from . import antiraid as antiraid_state

def is_server_owner():
    async def predicate(ctx: commands.Context):
        if ctx.author != ctx.guild.owner:
            raise commands.CheckFailure("Only the server owner can use this command.")
        return True
    return commands.check(predicate)


class Debug(commands.Cog):
    """Owner-only diagnostics command."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="debug")
    @is_server_owner()
    async def debug(self, ctx: commands.Context):
        """Run a full bot diagnostics check (server owner only)."""
        await ctx.message.delete()
        embed = discord.Embed(
            title="Bot Diagnostics",
            description="Running checks...",
            color=discord.Color.blurple(),
        )
        msg = await ctx.author.send(embed=embed)

        guild = ctx.guild
        bot_member = guild.me
        bot_top_role = bot_member.top_role
        perms = bot_member.guild_permissions

        lines: list[tuple[str, str, bool]] = []

        def ok(label: str, detail: str = ""):
            lines.append(("✅", label, detail))

        def fail(label: str, detail: str = ""):
            lines.append(("❌", label, detail))

        def warn(label: str, detail: str = ""):
            lines.append(("⚠️", label, detail))

        # ── Bot Permissions ───────────────────────────────────────────────
        checks = [
            ("Manage Roles",     perms.manage_roles),
            ("Manage Nicknames", perms.manage_nicknames),
            ("Kick Members",     perms.kick_members),
            ("Ban Members",      perms.ban_members),
            ("Manage Messages",  perms.manage_messages),
            ("Send Messages",    perms.send_messages),
            ("Embed Links",      perms.embed_links),
            ("View Audit Log",   perms.view_audit_log),
        ]
        for name, has_perm in checks:
            (ok if has_perm else fail)(f"Permission: {name}")

        # ── Role Existence & Hierarchy ────────────────────────────────────
        for role_name in ("Verified", "Unverified"):
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                fail(f"Role '{role_name}'", "Role not found — create it on the server")
            elif bot_top_role > role:
                ok(f"Role '{role_name}'", f"Found & bot is above it (bot: #{bot_top_role.position}, role: #{role.position})")
            else:
                fail(
                    f"Role '{role_name}'",
                    f"Bot's top role is BELOW '{role_name}' — drag the bot's role above it "
                    f"(bot: #{bot_top_role.position}, role: #{role.position})"
                )

        # ── Welcome Channel ───────────────────────────────────────────────
        welcome_id = os.environ.get("WELCOME_CHANNEL_ID")
        if not welcome_id:
            warn("Welcome channel", "WELCOME_CHANNEL_ID not set")
        else:
            welcome_ch = guild.get_channel(int(welcome_id))
            if not welcome_ch:
                fail("Welcome channel", f"Channel ID {welcome_id} not found in this server")
            else:
                ch_perms = welcome_ch.permissions_for(bot_member)
                if ch_perms.send_messages and ch_perms.embed_links:
                    ok("Welcome channel", f"#{welcome_ch.name} — bot can send embeds")
                else:
                    fail("Welcome channel", f"#{welcome_ch.name} — bot cannot send/embed there")

        # ── Log Channel ───────────────────────────────────────────────────
        log_id = os.environ.get("LOG_CHANNEL_ID")
        if not log_id:
            warn("Log channel", "LOG_CHANNEL_ID not set")
        else:
            log_ch = guild.get_channel(int(log_id))
            if not log_ch:
                fail("Log channel", f"Channel ID {log_id} not found in this server")
            else:
                ch_perms = log_ch.permissions_for(bot_member)
                if ch_perms.send_messages and ch_perms.embed_links:
                    ok("Log channel", f"#{log_ch.name} — bot can send embeds")
                else:
                    fail("Log channel", f"#{log_ch.name} — bot cannot send/embed there")

        # ── Roblox API ────────────────────────────────────────────────────
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://users.roblox.com/v1/usernames/users",
                    json={"usernames": ["Roblox"], "excludeBannedUsers": False},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        ok("Roblox API", "Reachable and responding")
                    else:
                        fail("Roblox API", f"Returned status {resp.status}")
        except Exception as e:
            fail("Roblox API", f"Request failed: {e}")

        # ── Members Intent ────────────────────────────────────────────────
        if self.bot.intents.members:
            ok("Members intent", "Enabled (join/leave events will fire)")
        else:
            fail("Members intent", "Disabled — welcome/goodbye/logging won't work")

        # ── Build result embed ────────────────────────────────────────────
        all_ok = all(icon == "✅" for icon, _, _ in lines)
        has_fail = any(icon == "❌" for icon, _, _ in lines)

        result_embed = discord.Embed(
            title="Bot Diagnostics",
            color=discord.Color.green() if all_ok else (discord.Color.red() if has_fail else discord.Color.orange()),
        )

        perm_lines = []
        config_lines = []
        api_lines = []

        for icon, label, detail in lines:
            entry = f"{icon} **{label}**" + (f"\n  └ {detail}" if detail else "")
            if "Permission" in label:
                perm_lines.append(entry)
            elif "API" in label or "intent" in label.lower():
                api_lines.append(entry)
            else:
                config_lines.append(entry)

        if perm_lines:
            result_embed.add_field(name="Permissions", value="\n".join(perm_lines), inline=False)
        if config_lines:
            result_embed.add_field(name="Config & Roles", value="\n".join(config_lines), inline=False)
        if api_lines:
            result_embed.add_field(name="External", value="\n".join(api_lines), inline=False)

        # ── Anti-Raid Status ──────────────────────────────────────────────
        from cogs.antiraid import (
            lockdown_active, lockdown_reason,
            JOIN_FLOOD_COUNT, JOIN_FLOOD_SECONDS,
            MIN_ACCOUNT_AGE_DAYS, MAX_MENTIONS,
            SPAM_MSG_COUNT, SPAM_MSG_SECONDS,
        )
        muted_role = discord.utils.get(guild.roles, name="Muted")
        antiraid_lines = []
        if lockdown_active:
            antiraid_lines.append(f"🔒 **Lockdown: ACTIVE** — {lockdown_reason or 'No reason set'}")
        else:
            antiraid_lines.append("🔓 **Lockdown: Inactive**")
        antiraid_lines.append(f"{'✅' if muted_role else '❌'} **Muted role** — {'found' if muted_role else 'not found (create a role named exactly `Muted`)' }")
        antiraid_lines.append(f"⚙️ Join flood: `{JOIN_FLOOD_COUNT}` joins in `{JOIN_FLOOD_SECONDS}s` → lockdown")
        antiraid_lines.append(f"⚙️ New account filter: kick if account < `{MIN_ACCOUNT_AGE_DAYS}` days old")
        antiraid_lines.append(f"⚙️ Mass mention: kick if > `{MAX_MENTIONS}` mentions in one message")
        antiraid_lines.append(f"⚙️ Spam guard: mute if `{SPAM_MSG_COUNT}` messages in `{SPAM_MSG_SECONDS}s`")
        result_embed.add_field(name="Anti-Raid", value="\n".join(antiraid_lines), inline=False)

        # ── Recent Verification Activity ──────────────────────────────────
        recent = get_recent(5)
        if recent:
            activity_lines = []
            for event in recent:
                ts = event.timestamp.strftime("%H:%M:%S UTC")
                header = (
                    f"{'✅' if event.success else '⚠️'} "
                    f"**{event.discord_user}** → `{event.roblox_username}` at {ts}"
                )
                step_lines = [f"  └ {icon} {desc}" for icon, desc in event.steps]
                activity_lines.append(header + "\n" + "\n".join(step_lines))
            result_embed.add_field(
                name="Recent Verification Activity",
                value="\n\n".join(activity_lines),
                inline=False,
            )
        else:
            result_embed.add_field(
                name="Recent Verification Activity",
                value="No verifications have run since the bot last started.",
                inline=False,
            )

        if all_ok:
            result_embed.set_footer(text="All checks passed — everything looks good!")
        elif has_fail:
            result_embed.set_footer(text="One or more checks failed — fix the issues above.")
        else:
            result_embed.set_footer(text="Some optional settings are not configured.")

        await msg.edit(embed=result_embed)

    @debug.error
    async def debug_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.author.send("Only the server owner can run `!debug`.")
        else:
            await ctx.author.send(f"Debug error: {error}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Debug(bot))
