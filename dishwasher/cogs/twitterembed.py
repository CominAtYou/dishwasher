import discord
from discord.ext.commands import Cog, Bot
import re
from urllib import parse
from requests_oauthlib import OAuth1Session
from datetime import datetime
from config import twitter_keys


class TwitterEmbed(Cog):
    bot: Bot
    twitter_link_regex = re.compile(r"https://twitter\.com/[A-z0-9]+/status/[0-9]+", re.IGNORECASE)
    session = OAuth1Session(twitter_keys["api_key"], client_secret=twitter_keys["api_secret"], resource_owner_key=twitter_keys["consumer_key"], resource_owner_secret=twitter_keys["consumer_secret"])

    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        twitter_links = self.twitter_link_regex.findall(message.content)
        if not twitter_links:
            return

        await message.edit(suppress=True)

        for link in twitter_links:
            url = parse.urlparse(link)
            tweet_id = url.path.split("/")[-1]

            req = self.session.get(f"https://api.twitter.com/1.1/statuses/show.json?id={tweet_id}&tweet_mode=extended")
            if req.status_code != 200:
                print("Failed to get tweet: %s", req.text)
                break

            tweet = req.json()
            if "errors" in tweet:
                print("Failed to get tweet: %s", tweet["errors"])
                break

            embed = discord.Embed(
                description=tweet["full_text"],
                color=0x1DA0F2,
                timestamp=datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S %z %Y")
            )

            embed.set_author(name=f'{tweet["user"]["name"]} (@{tweet["user"]["screen_name"]})', url=f"https://twitter.com/{tweet['user']['screen_name']}", icon_url=tweet["user"]["profile_image_url_https"])
            embed.add_field(name="Likes", value=tweet["favorite_count"])
            embed.add_field(name="Retweets", value=tweet["retweet_count"])
            embed.set_footer(text="Twitter", icon_url="https://abs.twimg.com/icons/apple-touch-icon-192x192.png")
            embed.set_image(url=tweet["entities"]["media"][0]["media_url_https"])

            await message.reply(embed=embed, mention_author=False)

async def setup(bot: Bot):
    await bot.add_cog(TwitterEmbed(bot))
