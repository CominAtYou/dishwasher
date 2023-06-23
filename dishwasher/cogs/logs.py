import discord
from discord.ext.commands import Cog
import json
import re
import config
import datetime
import os
from helpers.checks import check_if_staff
from helpers.userlogs import userlog, get_userlog
from helpers.sv_config import get_config
from helpers.embeds import (
    stock_embed,
    slice_embed,
    mod_embed,
    createdat_embed,
    joinedat_embed,
)


class Logs2(Cog):
    """
    An advanced logging mechanism, which logs to threads. Logs many changes.
    """

    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_member_join(self, member):
        await self.bot.wait_until_ready()
        if not get_config(member.guild.id, "logs", "ulog_thread"):
            return
        ulog = await self.bot.fetch_channel(
            get_config(member.guild.id, "logs", "ulog_thread")
        )

        invite_used = await self.bot.get_used_invites(member)

        embeds = []
        embed = stock_embed(self.bot)
        embed.color = discord.Color.lighter_gray()
        embed.title = "📥 User Joined"
        embed.description = f"{member.mention} ({member.id})"
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_author(
            name=member,
            icon_url=member.display_avatar.url,
        )
        createdat_embed(embed, member)
        embed.add_field(name="📨 Invite used:", value=invite_used, inline=True)

        embeds.append(embed)

        warns = get_userlog(member.guild.id)
        try:
            if warns[str(member.id)]["warns"]:
                embed = stock_embed(self.bot)
                embed.color = discord.Color.red()
                embed.title = "⚠️ This user has warnings!"
                for idx, warn in enumerate(warns[str(member.id)]["warns"]):
                    timestamp = datetime.datetime.strptime(
                        warn["timestamp"], "%Y-%m-%d %H:%M:%S"
                    ).strftime("%s")
                    embed.add_field(
                        name=f"Warn {idx + 1}: <t:{timestamp}:f> (<t:{timestamp}:R>)",
                        value=f"__Issuer:__ <@{warn['issuer_id']}> ({warn['issuer_id']})\n"
                        f"\n__Reason:__ {warn['reason']}",
                        inline=False,
                    )
                embeds.append(embed)
        except KeyError:  # if the user is not in the file
            pass

        await ulog.send(embeds=embeds)

    @Cog.listener()
    async def on_message_edit(self, before, after):
        await self.bot.wait_until_ready()
        if (
            after.author.bot
            or not after.guild
            or before.clean_content == after.clean_content
            or not get_config(after.guild.id, "logs", "ulog_thread")
        ):
            return
        ulog = await self.bot.fetch_channel(
            get_config(after.guild.id, "logs", "ulog_thread")
        )

        embed = stock_embed(self.bot)
        embed.color = discord.Color.light_gray()
        embed.title = "📝 Message Edit"
        embed.description = f"{after.author.mention} ({after.author.id}) in {after.channel.mention} [[Jump]({after.jump_url})]"
        embed.set_author(
            name=self.bot.escape_message(after.author),
            icon_url=after.author.display_avatar.url,
        )

        beforename = (
            f"❌ Before on <t:{before.created_at.astimezone().strftime('%s')}:f>"
        )
        if len(before.clean_content) > 1024:
            slice_embed(embed, before.clean_content, beforename)
        else:
            embed.add_field(
                name=beforename,
                value=f">>> {before.clean_content}",
                inline=False,
            )
        aftername = f"⭕ After on <t:{after.edited_at.astimezone().strftime('%s')}:f>"
        if len(after.clean_content) > 1024:
            slice_embed(embed, after.clean_content, aftername)
        else:
            embed.add_field(
                name=aftername,
                value=f">>> {after.clean_content}",
                inline=False,
            )

        await ulog.send(embed=embed)

    @Cog.listener()
    async def on_message_delete(self, message):
        await self.bot.wait_until_ready()
        if (
            message.author.bot
            or not message.guild
            or not get_config(message.guild.id, "logs", "ulog_thread")
        ):
            return
        ulog = await self.bot.fetch_channel(
            get_config(message.guild.id, "logs", "ulog_thread")
        )

        embed = stock_embed(self.bot)
        embed.color = discord.Color.dark_gray()
        embed.title = "🗑️ Message Delete"
        embed.description = f"{message.author.mention} ({message.author.id}) in {message.channel.mention}"
        embed.set_author(
            name=message.author,
            icon_url=message.author.display_avatar.url,
        )
        name = f"🧾 Sent on <t:{message.created_at.astimezone().strftime('%s')}:f>:"
        if len(message.clean_content) > 1024:
            slice_embed(embed, message.clean_content, name)
        else:
            embed.add_field(
                name=name,
                value=f">>> {message.clean_content}",
                inline=False,
            )

        await ulog.send(embed=embed)

    @Cog.listener()
    async def on_member_remove(self, member):
        await self.bot.wait_until_ready()
        ulog = get_config(member.guild.id, "logs", "ulog_thread")
        mlog = get_config(member.guild.id, "logs", "mlog_thread")
        if not ulog and not mlog:
            return

        cutoff_ts = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            seconds=5
        )

        alog = [
            entry
            async for entry in member.guild.audit_logs(
                limit=1, action=discord.AuditLogAction.ban
            )
        ]
        if alog and alog[0].created_at >= cutoff_ts and alog[0].target.id == member.id:
            return

        alog = [
            entry
            async for entry in member.guild.audit_logs(
                limit=1, action=discord.AuditLogAction.kick
            )
        ]
        if alog and alog[0].target.id == member.id:
            if not alog[0].created_at <= cutoff_ts:
                if alog[0].user.id != self.bot.user.id:
                    userlog(
                        member.guild.id,
                        member.id,
                        alog[0].user,
                        "Kicked by external method.",
                        "kicks",
                    )
                    if not mlog:
                        return
                    mlog = await self.bot.fetch_channel(mlog)

                    user = member
                    staff = alog[0].user
                    reason = alog[0].reason

                    embed = stock_embed(self.bot)
                    embed.color = discord.Color.from_str("#FFFF00")
                    embed.title = "👢 Kick"
                    embed.description = f"{user.mention} was kicked by {staff.mention} [External Method]"
                    mod_embed(embed, user, staff, reason)

                    await mlog.send(embed=embed)
                return

        if not ulog:
            return
        ulog = await self.bot.fetch_channel(ulog)

        embed = stock_embed(self.bot)
        embed.color = discord.Color.darker_gray()
        embed.title = "📥 User Left"
        embed.description = f"{member.mention} ({member.id})"
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_author(
            name=member,
            icon_url=member.display_avatar.url,
        )
        createdat_embed(embed, member)
        joinedat_embed(embed, member)

        await ulog.send(embed=embed)

    @Cog.listener()
    async def on_member_ban(self, guild, member):
        await self.bot.wait_until_ready()

        alog = [
            entry
            async for entry in guild.audit_logs(
                limit=1, action=discord.AuditLogAction.ban
            )
        ]
        if alog[0].user.id == self.bot.user.id or alog[0].target.id != member.id:
            return

        userlog(
            guild.id,
            member.id,
            alog[0].user,
            "Banned by external method.",
            "bans",
        )

        mlog = get_config(guild.id, "logs", "mlog_thread")
        if not mlog:
            return
        mlog = await self.bot.fetch_channel(mlog)

        user = member
        staff = alog[0].user
        reason = alog[0].reason

        embed = stock_embed(self.bot)
        embed.color = discord.Color.from_str("#FF0000")
        embed.title = "⛔ Ban"
        embed.description = (
            f"{user.mention} was banned by {staff.mention} [External Method]"
        )
        mod_embed(embed, user, staff, reason)

        await mlog.send(embed=embed)

    @Cog.listener()
    async def on_member_unban(self, guild, user):
        await self.bot.wait_until_ready()
        mlog = get_config(guild.id, "logs", "mlog_thread")
        if not mlog:
            return
        mlog = await self.bot.fetch_channel(mlog)

        alog = [
            entry
            async for entry in guild.audit_logs(
                limit=1, action=discord.AuditLogAction.unban
            )
        ]
        if alog[0].user.id == self.bot.user.id:
            return

        user = user
        staff = alog[0].user
        reason = alog[0].reason

        embed = stock_embed(self.bot)
        embed.color = discord.Color.from_str("#00FF00")
        embed.title = "🎁 Unban"
        embed.description = (
            f"{user.mention} was unbanned by {staff.mention} [External Method]"
        )
        mod_embed(embed, user, staff, reason)

        await mlog.send(embed=embed)

    @Cog.listener()
    async def on_member_update(self, member_before, member_after):
        await self.bot.wait_until_ready()
        ulog = get_config(member_after.guild.id, "logs", "ulog_thread")
        if not ulog:
            return
        ulog = await self.bot.fetch_channel(ulog)

        embed = stock_embed(self.bot)
        embed.color = member_after.color
        embed.title = "ℹ️ Member Update"
        embed.description = f"{member_after.mention} ({member_after.id})"
        embed.set_author(
            name=member_after,
            icon_url=member_after.display_avatar.url,
        )

        # Roles
        if member_before.roles != member_after.roles:
            roles = []
            for role in member_after.guild.roles:
                if role == member_after.guild.default_role:
                    continue
                if role in member_before.roles and role in member_after.roles:
                    roles.append(role.mention)
                elif role in member_before.roles and role not in member_after.roles:
                    roles.append("> ~~" + role.mention + "~~")
                elif role not in member_before.roles and role in member_after.roles:
                    roles.append("> " + role.mention)
                else:
                    continue

            embed.add_field(
                name="🎨 Role Change",
                value="\n".join(reversed(roles)),
                inline=False,
            )

        # Usernames
        if str(member_before) != str(member_after):
            embed.add_field(
                name="📝 Username Change",
                value=f"❌ {member_before}\n⬇️\n⭕ {member_after}",
                inline=False,
            )

        # Nicknames
        if member_before.nick != member_after.nick:
            if not member_before.nick:
                fname = "🏷 Nickname Added"
            elif not member_after.nick:
                fname = "🏷 Nickname Removed"
            else:
                fname = "🏷 Nickname Changed"
            embed.add_field(
                name=fname,
                value=f"❌ {member_before.nick}\n⬇️\n⭕ {member_after.nick}",
                inline=False,
            )

        if embed.fields:
            await ulog.send(embed=embed)

    @Cog.listener()
    async def on_guild_update(self, guild_before, guild_after):
        await self.bot.wait_until_ready()
        slog = get_config(guild_after.id, "logs", "slog_thread")
        if not slog:
            return
        slog = await self.bot.fetch_channel(slog)

        embed = stock_embed(self.bot)
        embed.color = discord.Color.from_str("#FFCC00")
        embed.title = "🏡 Server Update"
        embed.description = (
            f"{guild_after.name} with `{guild_after.member_count}` members."
        )
        embed.set_author(
            name=guild_after.name,
            icon_url=guild_after.icon.url,
        )

        # Server Names
        if guild_before.name != guild_after.name:
            embed.add_field(
                name="📝 Name Change",
                value=f"❌ {guild_before.name}\n⬇️\n⭕ {guild_after.name}",
                inline=False,
            )

        # Server Banners
        try:
            if guild_before.banner.url != guild_after.banner.url:
                if guild_after.banner:
                    text = "The new banner is below."
                    embed.set_image(url=guild_after.banner.url)
                else:
                    text = "The banner was removed."
                embed.add_field(
                    name="🎨 Banner Change",
                    value=text,
                    inline=False,
                )
        except:
            pass

        if embed.fields:
            await slog.send(embed=embed)

    @Cog.listener()
    async def on_guild_channel_create(self, channel):
        await self.bot.wait_until_ready()
        slog = get_config(channel.guild.id, "logs", "slog_thread")
        if not slog:
            return
        slog = await self.bot.fetch_channel(slog)

        embed = stock_embed(self.bot)
        embed.color = discord.Color.from_str("#00FFFF")
        embed.title = "🏠 Channel Created"
        embed.description = f"`{str(channel.category)}/`#{channel.name} ({channel.id}) [{channel.mention}]"
        embed.set_author(
            name=channel.guild.name,
            icon_url=channel.guild.icon.url,
        )

        await slog.send(embed=embed)

    @Cog.listener()
    async def on_guild_channel_delete(self, channel):
        await self.bot.wait_until_ready()
        slog = get_config(channel.guild.id, "logs", "slog_thread")
        if not slog:
            return
        slog = await self.bot.fetch_channel(slog)

        embed = stock_embed(self.bot)
        embed.color = discord.Color.from_str("#FF00FF")
        embed.title = "🏚️ Channel Deleted"
        embed.description = f"`{str(channel.category)}/`#{channel.name} ({channel.id})"
        embed.set_author(
            name=channel.guild.name,
            icon_url=channel.guild.icon.url,
        )

        await slog.send(embed=embed)

    @Cog.listener()
    async def on_guild_channel_update(self, channel_before, channel_after):
        await self.bot.wait_until_ready()
        slog = get_config(channel_after.guild.id, "logs", "slog_thread")
        if not slog:
            return
        slog = await self.bot.fetch_channel(slog)

        embed = stock_embed(self.bot)
        embed.color = discord.Color.from_str("#FFFF00")
        embed.title = "🏘️ Channel Update"
        embed.description = (
            f"{channel_after.name} ({channel_after.id}) [{channel_after.mention}]"
        )
        embed.set_author(
            name=channel_after.guild.name,
            icon_url=channel_after.guild.icon.url,
        )

        # Names
        if channel_before.name != channel_after.name:
            embed.add_field(
                name="📝 Name Change",
                value=f"❌ {channel_before.name}\n⬇️\n⭕ {channel_after.name}",
                inline=False,
            )

        # Topics
        try:
            if channel_before.topic != channel_after.topic:
                embed.add_field(
                    name="✍️ Topic Change",
                    value=f"❌ {channel_before.topic}\n⬇️\n⭕ {channel_after.topic}",
                    inline=False,
                )
        except:
            pass

        # Permissions
        if channel_before.overwrites != channel_after.overwrites:
            output = []
            for entry in list(channel_before.overwrites.items()):
                if entry[0] not in channel_after.overwrites:
                    output.append(f"- {entry[0]}")
                for perm, value in dict(entry[1]).items():
                    if value != dict(channel_after.overwrites_for(entry[0]))[perm]:
                        if entry[0] in channel_after.overwrites:
                            output.append(f"{entry[0]}")
                        output.append(
                            f"{perm}\n- {value}\n+ {dict(channel_after.overwrites_for(entry[0]))[perm]}"
                        )
            for entry in list(channel_after.overwrites.items()):
                if entry[0] in channel_before.overwrites:
                    continue
                output.append(f"+ {entry[0]}")
                for perm, value in dict(entry[1]).items():
                    if value != dict(channel_before.overwrites_for(entry[0]))[perm]:
                        output.append(
                            f"{perm}\n- {dict(channel_before.overwrites_for(entry[0]))[perm]}\n+ {value}"
                        )

            embed.add_field(
                name="🔒 Permission Change",
                value="```diff\n" + "\n".join(output) + "```",
                inline=False,
            )

        if embed.fields:
            await slog.send(embed=embed)

    @Cog.listener()
    async def on_guild_role_create(self, role):
        await self.bot.wait_until_ready()
        slog = get_config(role.guild.id, "logs", "slog_thread")
        if not slog:
            return
        slog = await self.bot.fetch_channel(slog)

        embed = stock_embed(self.bot)
        embed.color = role.color
        embed.title = "🏷️ Role Created"
        embed.description = f"{role.name} ({role.id}) [<@&{role.id}>]"
        embed.set_author(
            name=role.guild.name,
            icon_url=role.guild.icon.url,
        )

        await slog.send(embed=embed)

    @Cog.listener()
    async def on_guild_role_delete(self, role):
        await self.bot.wait_until_ready()
        slog = get_config(role.guild.id, "logs", "slog_thread")
        if not slog:
            return
        slog = await self.bot.fetch_channel(slog)

        embed = stock_embed(self.bot)
        embed.color = role.color
        embed.title = "🔥 Role Deleted"
        embed.description = f"{role} ({role.id}) [{role.mention}]"
        embed.set_author(
            name=role.guild.name,
            icon_url=role.guild.icon.url,
        )

        await slog.send(embed=embed)

    @Cog.listener()
    async def on_guild_role_update(self, role_before, role_after):
        await self.bot.wait_until_ready()
        slog = get_config(role_after.guild.id, "logs", "slog_thread")
        if not slog:
            return
        slog = await self.bot.fetch_channel(slog)

        embed = stock_embed(self.bot)
        embed.color = role_after.color
        embed.title = "🖋️ Role Update"
        embed.description = f"{role_after} ({role_after.id}) [{role_after.mention}]"
        embed.set_author(
            name=role_after.guild.name,
            icon_url=role_after.guild.icon.url,
        )

        # Names
        if role_before.name != role_after.name:
            embed.add_field(
                name="📝 Name Change",
                value=f"❌ {role_before}\n⬇️\n⭕ {role_after}",
                inline=False,
            )

        # Colors
        if role_before.color != role_after.color:
            embed.add_field(
                name="🌈 Color Change",
                value=f"❌ {str(role_before.color)}\n⬇️\n⭕ {str(role_after.color)}",
                inline=False,
            )

        # Icons
        try:
            if role_before.icon != role_after.icon:
                if role_after.icon:
                    text = "The new icon is to the side."
                    embed.set_thumbnail(url=role_after.icon.url)
                else:
                    text = "The icon was removed."
                embed.add_field(
                    name="ℹ️ Icon Change",
                    value=text,
                    inline=False,
                )
        except:
            pass

        # Hoists
        if role_before.hoist != role_after.hoist:
            embed.add_field(
                name="🆙 Hoist Change",
                value=f"❌ {str(role_before.hoist)}\n⬇️\n⭕ {str(role_after.hoist)}",
                inline=False,
            )

        # Mentions
        if role_before.mentionable != role_after.mentionable:
            embed.add_field(
                name="1️⃣ Mentionable Change",
                value=f"❌ {str(role_before.mentionable)}\n⬇️\n⭕ {str(role_after.mentionable)}",
                inline=False,
            )

        if embed.fields:
            await slog.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Logs2(bot))
