import discord
from discord import app_commands
from discord.ext import commands

from database.db import log_command
from services import education_service
from utils.embed_builder import build_error_embed, build_lesson_embed, build_success_embed


class EducationCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="learn", description="Read a beginner Web3 lesson.")
    async def learn(self, interaction: discord.Interaction, topic: str) -> None:
        lesson = education_service.get_lesson(topic)
        if not lesson:
            log_command(str(interaction.user.id), str(interaction.guild_id), "learn", topic, "not_found")
            await interaction.response.send_message(embed=build_error_embed("Lesson not found", "Try /lessons to see available topics."), ephemeral=True)
            return
        log_command(str(interaction.user.id), str(interaction.guild_id), "learn", topic, "success")
        await interaction.response.send_message(embed=build_lesson_embed(lesson["title"], lesson["content"]))

    @app_commands.command(name="glossary", description="Look up a Web3 term.")
    async def glossary(self, interaction: discord.Interaction, term: str) -> None:
        item = education_service.get_glossary_term(term)
        if not item:
            await interaction.response.send_message(embed=build_error_embed("Term not found", "Try another term such as Wallet, Gas Fee, or DeFi."), ephemeral=True)
            return
        example = f"\n\nExample: {item.get('example')}" if item.get("example") else ""
        log_command(str(interaction.user.id), str(interaction.guild_id), "glossary", term, "success")
        await interaction.response.send_message(embed=build_success_embed(item["term"], item["definition"] + example))

    @app_commands.command(name="roadmap", description="Show a beginner Web3 learning roadmap.")
    async def roadmap(self, interaction: discord.Interaction) -> None:
        roadmap = education_service.get_beginner_roadmap()
        text = "\n".join(f"Stage {x['stage']}: {x['title']}" for x in roadmap)
        await interaction.response.send_message(embed=build_success_embed("Beginner Roadmap", text))

    @app_commands.command(name="lessons", description="List available lessons.")
    async def lessons(self, interaction: discord.Interaction) -> None:
        lessons = education_service.list_lessons()
        text = "\n".join(f"`{x['topic_slug']}` - {x['title']}" for x in lessons)
        await interaction.response.send_message(embed=build_success_embed("Lessons", text))

    @app_commands.command(name="quiz", description="Get a quiz question.")
    async def quiz(self, interaction: discord.Interaction, level: str = "beginner") -> None:
        quiz = education_service.get_quiz(level)
        if not quiz:
            await interaction.response.send_message(embed=build_error_embed("No quiz found", "Try again after seed data is loaded."), ephemeral=True)
            return
        text = f"{quiz['question']}\nA. {quiz['option_a']}\nB. {quiz['option_b']}\nC. {quiz['option_c']}\nD. {quiz['option_d']}\n\nAnswer: {quiz['correct_option']} - {quiz.get('explanation', '')}"
        await interaction.response.send_message(embed=build_success_embed("Quiz", text), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EducationCommands(bot))
