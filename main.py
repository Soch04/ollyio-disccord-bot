"""
This module contains the main function to run Ollyio.

The bot is designed to manage interactions in a Discord channel. 
It integrates the Llama3 AI model (in ChatBot class) and manages the Members 
who join the conversation with Olly. 

Using the discord.py library, the bot's command functionality is divided into 
several Cogs for organization. Within each cog is a set of functions and bot commands. 

Classes:
    ChatBot: Handles Llama3 functionality. 
    ManageMembers: Manages members who join the conversation with Olly.
    BotMain: Handles the core text communication with Olly.
    AdminCommands: Handles admin-level commands to customize bot.
    PublicCommands: Handles commands available to all members.
    BackgroundTasks: Handles the background task that kicks users from conversation on timeout.

Functions:
    main() -> None: The main function to run the bot.

Environment Variables:
    DISCORD_BOT_TOKEN (str): The bot's token.
    DISCORD_GUILD_ID (int): The ID of the guild the bot is connected to.
"""

import asyncio
import os
from pathlib import Path
import discord
from discord.ext import commands
from dotenv import load_dotenv
from bot import ChatBot, ManageMembers, BotMain, AdminCommands, PublicCommands, BackgroundTasks

# Load environment variables
dotenv_path = Path("D:/Files/Code/Python/Discord_Olly/.env")
load_dotenv(dotenv_path=dotenv_path)

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))


async def main() -> None:
    """
    The main function to run the bot.

    This function initializes the chatbot and members, creates instances of the cogs, 
    adds the cogs to the bot, and starts the bot.
    """
    chatbot = ChatBot()
    members = ManageMembers()

    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix=None, intents=intents)

    # Create instances of the cogs
    bot_cog = BotMain(bot, chatbot, members)
    admin_commands_cog = AdminCommands(bot, chatbot)
    public_commands_cog = PublicCommands(bot, bot_cog, chatbot, members)
    bg_tasks_cog = BackgroundTasks(bot, bot_cog, members)

    # Add cogs to the bot
    await bot.add_cog(bot_cog)
    await bot.add_cog(admin_commands_cog)
    await bot.add_cog(public_commands_cog)
    await bot.add_cog(bg_tasks_cog)

    # Run the bot
    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
