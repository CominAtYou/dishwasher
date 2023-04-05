import json
import re
import discord
import datetime
from discord.ext.commands import Cog, Context, Bot
from discord.ext import commands
from helpers.checks import check_if_staff, check_if_bot_manager


class Messagescan(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.link_re = re.compile(
            r"https://(?:canary\.|ptb\.)?discord\.com/channels/[0-9]+/[0-9]+/[0-9]+",
            re.IGNORECASE,
        )
        self.prevmessages = {}

    @commands.guild_only()
    @commands.check(check_if_staff)
    @commands.command()
    async def snipe(self, ctx):
        if ctx.channel.id in self.prevmessages:
            lastmsg = self.prevmessages[ctx.channel.id]
            # Prepare embed msg
            embed = discord.Embed(
                color=ctx.author.color,
                description=f"{lastmsg.content}",
                timestamp=lastmsg.created_at,
            )
            embed.set_footer(
                text=f"Sniped by {ctx.author.name}#{ctx.author.discriminator}"
            )
            embed.set_author(
                name=f"💬 {lastmsg.author.name}#{lastmsg.author.discriminator} said in #{lastmsg.channel.name}...",
                icon_url=f"{lastmsg.author.display_avatar.url}",
            )
            await ctx.reply(embed=embed, mention_author=False)
        else:
            await ctx.reply(
                content="There is no message in the snipe cache for this channel.",
                mention_author=False,
            )

    @Cog.listener()
    async def on_message(self, message):
        await self.bot.wait_until_ready()

        msglinks = self.link_re.findall(message.content)

        if not msglinks:
            return

        embeds = []
        for m in msglinks:
            components = m.split("/")
            guildid = int(components[4])
            channelid = int(components[5])
            msgid = int(components[6])

            rcvguild = self.bot.get_guild(guildid)
            rcvchannel = rcvguild.get_channel_or_thread(channelid)
            rcvmessage: discord.Message = await rcvchannel.fetch_message(msgid)

            # Prepare embed msg
            embed = discord.Embed(
                color=rcvmessage.author.color,
                description=f"{rcvmessage.content}",
                timestamp=rcvmessage.created_at,
            )
            embed.set_footer(
                text=f"Quoted by {message.author.name}#{message.author.discriminator}"
            )
            embed.set_author(
                name=f"💬 {rcvmessage.author.name}#{rcvmessage.author.discriminator} said in #{rcvmessage.channel.name}...",
                icon_url=f"{rcvmessage.author.display_avatar.url}",
            )

            number_of_attachments = len(rcvmessage.attachments)

            if number_of_attachments == 1 and rcvmessage.attachments[0].content_type.startswith("image/"):
                embed.set_image(url=rcvmessage.attachments[0].url)
            elif number_of_attachments > 1:
                attachments_str = ""
                for i in range(0, 4 if number_of_attachments > 4 else number_of_attachments):
                    attachments_str += f"- [{rcvmessage.attachments[i].filename}]({rcvmessage.attachments[i].url})\n"

                # despite being comprised entirely of hyperlinks, it's quite easy to hit the field character limit of 1024 with more than like 4 links
                # so just truncate the list of attachments if there are more than 4
                remaining_attachments = number_of_attachments - 4

                embed.add_field(name=f"Attachments{' (' + str(number_of_attachments - 4) + ' not included)' if remaining_attachments > 0 else ''}", value=attachments_str, inline=False)

            embeds.append(embed)
        await message.reply(embeds=embeds, mention_author=False)

    @Cog.listener()
    async def on_message_delete(self, message):
        await self.bot.wait_until_ready()
        if message.author.bot:
            return

        self.prevmessages[message.channel.id] = message


async def setup(bot: Bot):
    await bot.add_cog(Messagescan(bot))
