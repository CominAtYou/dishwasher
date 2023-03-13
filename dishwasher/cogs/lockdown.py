from discord.ext import commands
from discord.ext.commands import Cog
import config
import discord
from helpers.checks import check_if_staff


class Lockdown(Cog):
    def __init__(self, bot):
        self.bot = bot

    async def set_sendmessage(
        self, channel: discord.TextChannel, role, allow_send, issuer
    ):
        try:
            roleobj = channel.guild.get_role(role)
            overrides = channel.overwrites_for(roleobj)
            overrides.send_messages = allow_send
            await channel.set_permissions(
                roleobj, overwrite=overrides, reason=str(issuer)
            )
        except:
            pass

    async def unlock_for_staff(self, channel: discord.TextChannel, issuer):
        for role in config.staff_role_ids:
            await self.set_sendmessage(channel, role, True, issuer)

    @commands.guild_only()
    @commands.check(check_if_staff)
    @commands.command()
    async def lock(self, ctx, channel: discord.TextChannel = None, soft: bool = False):
        """[S] Prevents people from speaking in a channel.

        Defaults to current channel."""
        if not channel:
            channel = ctx.channel
        log_channel = self.bot.get_channel(config.modlog_channel)

        roles = None
        for key, lockdown_conf in config.lockdown_configs.items():
            if channel.id in lockdown_conf["channels"]:
                roles = lockdown_conf["roles"]

        if roles is None:
            roles = config.lockdown_configs["default"]["roles"]

        for role in roles:
            await self.set_sendmessage(channel, role, False, ctx.author)

        await self.unlock_for_staff(channel, ctx.author)

        public_msg = "🔒 Channel locked down. "
        if not soft:
            public_msg += (
                "Only Staff may speak. "
                '**Do not** bring the topic to other channels or risk action taken. This includes "What happened?" messages.'
            )

        await ctx.send(public_msg)
        safe_name = await commands.clean_content(escape_markdown=True).convert(
            ctx, str(ctx.author)
        )
        msg = f"🔒 **Lockdown**: {ctx.channel.mention} by {safe_name}"
        await log_channel.send(msg)

    @commands.guild_only()
    @commands.check(check_if_staff)
    @commands.command()
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        """[S] Unlocks speaking in current channel."""
        if not channel:
            channel = ctx.channel
        log_channel = self.bot.get_channel(config.modlog_channel)

        roles = None
        for key, lockdown_conf in config.lockdown_configs.items():
            if channel.id in lockdown_conf["channels"]:
                roles = lockdown_conf["roles"]

        if roles is None:
            roles = config.lockdown_configs["default"]["roles"]

        await self.unlock_for_staff(channel, ctx.author)

        for role in roles:
            await self.set_sendmessage(channel, role, True, ctx.author)

        safe_name = await commands.clean_content(escape_markdown=True).convert(
            ctx, str(ctx.author)
        )
        await ctx.send("🔓 Channel unlocked.")
        msg = f"🔓 **Unlock**: {ctx.channel.mention} by {safe_name}"
        await log_channel.send(msg)


async def setup(bot):
    await bot.add_cog(Lockdown(bot))
