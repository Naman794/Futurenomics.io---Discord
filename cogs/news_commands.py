from discord import app_commands
from discord.ext import commands

from services.news_service import fetch_latest_news, save_article
from utils.embed_builder import build_news_embed


class NewsCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="news", description="Fetch latest crypto/Web3 news.")
    async def news(self, interaction, query: str = "crypto") -> None:
        await interaction.response.defer()
        articles = fetch_latest_news(query=query, limit=5)
        for article in articles:
            save_article(article)
        await interaction.followup.send(embed=build_news_embed(articles))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NewsCommands(bot))
