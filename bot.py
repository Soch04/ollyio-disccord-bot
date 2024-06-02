import functools
import time
import enum
import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord import ui
from chatbot import ChatBot


def admin_command(func):
    """
    Decorator to check if the user has administrator permissions.

    Args:
        func (function): The function to be decorated.

    Returns:
        function: The decorated function.
    """
    @functools.wraps(func)
    async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need administrator permissions to use this command!",
                ephemeral=True,
            )
            return
        await func(self, interaction, *args, **kwargs)

    return wrapper


class DisplayCode(enum.IntEnum):
    """
    Enum class to represent different response types through Discord.

    Attributes:
        CONFRIM (int): Confirmation response.
        CANCEL (int): Cancel response.
        EXECUTE (int): Execute response.
        JOIN (int): Join response.
        JOIN_ERROR (int): Join error response.
        LEAVE (int): Leave response.
        SHOW_INSTRUCTIONS (int): Show instructions response.
        RESET_INSTRUCTIONS (int): Reset instructions response.
        KICK_MEMBER (int): Kick member response.
        RESPONSE (int): General response.
    """

    CONFRIM = 0
    CANCEL = 1
    EXECUTE = 2
    JOIN = 3
    JOIN_ERROR = 4
    LEAVE = 5
    SHOW_INSTRUCTIONS = 6
    RESET_INSTRUCTIONS = 9
    KICK_MEMBER = 7
    RESPONSE = 8


class Member:
    """
    Class to represent a member who has used the join-conversation command in the Discord server.

    Attributes:
        name (str): The name of the member.
        start_time (int): The start time since member's last activity.
        max_time (int): The maximum allowed time for the member's activity.
        end_time (int): The end time of the member's activity (which is the start_time + max_time).
    """
    def __init__(self, name: str):
        self.name = name
        self.start_time: int = round(time.time())
        self.max_time: int = 60 * 10  # 600 seconds (10 minutes)
        self.end_time: int = self.max_time + self.start_time

    def set_start_time(self) -> None:
        """
        Set the start_time to current time. 
        For each time it's called, it runs closer towards the end time.
        """
        self.start_time = round(time.time())

    def set_end_time(self) -> None:
        """
        Resets the timer. Sets the end time as the new start time, 
        and adds a set # (max_time) of seconds to the end time.
        """
        remainder = self.end_time - self.start_time
        self.start_time = self.end_time
        self.end_time = (self.start_time + self.max_time) - remainder

    def get_time(self) -> int:
        """
        Returns time left for user before kick.

        Returns:
            int: The remaining time before the user is kicked.
        """
        return self.end_time - self.start_time

    def check_time(self) -> bool:
        """
        Check if member's start time is less than the end time limit.

        Returns:
            bool: True if the start time did not exceed the end time, False otherwise.
        """
        return self.start_time < self.end_time


class ManageMembers:
    """
    Class to store Members who have used the join-conversation command.

    Attributes:
        conversation_members (list[Member]): List of members in the conversation.
        member_limit (int): Maximum number of members allowed in the conversation.
    """
    def __init__(self):
        self.conversation_members: list[Member] = []
        self.member_limit = 5

    def find_member(self, member_name: str) -> bool:
        """
        Check if a member exists in the conversation.

        Args:
            member_name (str): The name of the member to find.

        Returns:
            bool: True if the member is found, False otherwise.
        """
        for member in self.conversation_members:
            if member.name == member_name:
                return True
        return False

    def get_member(self, member_name: str) -> Member | None:
        """
        Get a member from the conversation.

        Args:
            member_name (str): The name of the member to get.

        Returns:
            Member | None: The member if found, None otherwise.
        """
        for member in self.conversation_members:
            if member.name == member_name:
                return member
        return None

    def add_member(self, member: Member) -> bool:
        """
        Add a member to the conversation.

        Args:
            member (Member): The member to add.

        Returns:
            bool: True if the member was added successfully, False otherwise.
        """
        if len(self.conversation_members) < self.member_limit:
            self.conversation_members.append(member)
            return True
        return False

    def remove_member(self, member_name: str) -> bool:
        """
        Remove a member from the conversation.

        Args:
            member_name (str): The name of the member to remove.

        Returns:
            bool: True if the member was removed successfully, False otherwise.
        """
        for member in self.conversation_members:
            if member.name == member_name:
                self.conversation_members.remove(member)
            return True
        return False

    def get_space(self) -> int:
        """
        Get the number of members in the conversation.

        Returns:
            int: The number of members in the conversation.
        """
        return len(self.conversation_members)

    def get_space_left(self) -> str:
        """
        Get the remaining space in the conversation in string format.

        Returns:
            str: The remaining space in the conversation in the format 
            "Space left: {current} / {limit}".
        """
        return f"Space left: {len(self.conversation_members)} / {self.member_limit}"


class LoadDisplays:
    """
    Load the embed messages for the Discord bot to use based on a given enum variable.
    """

    @staticmethod
    async def member_notification(
        bot: commands.Bot,
        interaction: discord.Interaction,
        name,
        members: ManageMembers,
        display_code: DisplayCode,
    ) -> None:
        if display_code == DisplayCode.JOIN:
            user = await bot.fetch_user(interaction.user.id)
            embed = discord.Embed(
                title=f"{name} has joined the conversation!",
                description="```Begin messages with a '>'```",
            )
            embed.set_footer(text=members.get_space_left())
            embed.set_thumbnail(url=user.avatar.url)
            await interaction.response.send_message(embed=embed)

        if display_code == DisplayCode.LEAVE:
            user = await bot.fetch_user(interaction.user.id)
            embed = discord.Embed(title=f"{name} has left the conversation!")
            embed.set_footer(text=members.get_space_left())
            embed.set_thumbnail(url=user.avatar.url)
            await interaction.response.send_message(embed=embed)

        if display_code == DisplayCode.KICK_MEMBER:
            user = await bot.fetch_user(interaction.user.id)
            embed = discord.Embed(title=f"{name} was kicked due to inactivity!")
            embed.set_footer(text=members.get_space_left())
            embed.set_thumbnail(url=user.avatar.url)
            await interaction.response.send_message(embed=embed)

    @staticmethod
    async def general_notification(
        interaction: discord.Interaction,
        display_code: DisplayCode,
    ) -> None:
        if display_code == DisplayCode.RESET_INSTRUCTIONS:
            embed = discord.Embed(
                title=f"{interaction.user} has edited Olly's instructions!",
                description="```Use **/view-instructions** to see the changes!```",
            )
            embed.set_author(name=interaction.user, icon_url=interaction.user.avatar)
            await interaction.response.send_message(embed=embed)

        elif display_code == DisplayCode.EXECUTE:
            embed=discord.Embed(
                title=f"{interaction.user} has deleted Olly's conversation history!",
                description= "Olly won't remember any prior conversation."
            )
            embed.set_author(name=interaction.user, icon_url=interaction.user.avatar)
            await interaction.response.send_message(embed=embed)

    @staticmethod
    async def edit_bot(
        interaction: discord.Interaction, chatbot: ChatBot, display_code: DisplayCode
    ) -> None:
        if display_code == DisplayCode.SHOW_INSTRUCTIONS:
            embed = discord.Embed(
                title=f"{chatbot.name}'s instructions:",
                description=f"```{chatbot.instructions}```",
            )
            embed.set_footer(
                text="use /edit-instructions to modify, or /reset-instructions to reset to default."
            )
            await interaction.response.send_message(embed=embed, view=None)

    @staticmethod
    async def bot_response(
        content: str, prompt: str, display_code: DisplayCode
    ) -> None:
        if display_code == DisplayCode.RESPONSE:
            embed = discord.Embed(
                color=discord.Color.light_gray(), title="", description=f"{content}"
            )
            embed.set_footer(text=prompt)
            return embed


class EditInstructions(ui.Modal, title="Edit Olly's instructions"):
    """
    A class to represent the modal for editing the instructions of a ChatBot.

    Attributes:
    -----------
    chatbot : ChatBot
        The ChatBot instance whose instructions are to be edited.
    personality : ui.TextInput
        The TextInput field for the personality of the ChatBot.
    goals : ui.TextInput
        The TextInput field for the goals of the ChatBot.
    restrictions : ui.TextInput
        The TextInput field for the restrictions of the ChatBot.
    """
    def __init__(self, chatbot: ChatBot):
        super().__init__()
        self.chatbot = chatbot

    personality = ui.TextInput(
        label="Personality",
        style=discord.TextStyle.paragraph,
        placeholder="You are helpful, collaborative, fun loving...",
        required=False,
        max_length=500,
    )
    goals = ui.TextInput(
        label="Goals",
        style=discord.TextStyle.paragraph,
        placeholder="Your goal is to facilitate conversation...",
        required=False,
        max_length=500,
    )
    restrictions = ui.TextInput(
        label="Restrictions",
        style=discord.TextStyle.paragraph,
        placeholder="Don't respond to negative comments about...",
        required=False,
        max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        self.chatbot.edit_instructions(
            self.personality.value, self.goals.value, self.restrictions.value
        )
        await LoadDisplays.edit_bot(
            interaction, self.chatbot, DisplayCode.SHOW_INSTRUCTIONS
        )


# Define the Bot class (Cog for bot commands)
class BotMain(commands.Cog):
    """
    Constructs all the necessary attributes for the BotMain object.

    Parameters:
    -----------
    bot : commands.Bot
        The bot instance.
    chatbot : ChatBot
        The ChatBot instance.
    members : ManageMembers
        The ManageMembers instance.
    """

    def __init__(
        self, bot: commands.Bot, chatbot: ChatBot, members: ManageMembers
    ) -> None:
        self.bot = bot
        self.chatbot = chatbot
        self.members = members
        self.home_channel_id = None

    def check_if_home(self, channel_id: int) -> bool:
        """
        Checks if the given channel is the home channel.

        Parameters:
        -----------
        channel_id : int
            The ID of the channel to check.

        Returns:
        --------
        bool
            True if the given channel is the home channel, False otherwise.
        """
        if self.home_channel_id == channel_id:
            return True
        elif self.home_channel_id is None:
            return None
        return False

    @app_commands.command(
        name="set-home",
        description="Set Olly's home channel to wherever you use this slash command.",
    )
    @admin_command
    async def set_home(
        self,
        interaction: discord.Interaction,
    ):
        """
        Sets the home channel to the channel where this command is used.

        Parameters:
        -----------
        interaction : discord.Interaction
            The interaction that triggered the command.
        """
        # Set the home channel ID to the current channel
        self.home_channel_id = interaction.channel.id
        await interaction.response.send_message(
            f"Home channel set to {interaction.channel.mention}"
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Handles the event when a message is sent in the server.
        The AI chatbot will respond to the message with the prefix.

        Parameters:
        -----------
        message : discord.Message
            The message that was sent.
        """
        if (message.author == self.bot.user) or (
            self.check_if_home(message.channel.id) is False
        ):
            return  # Return if bot or channel is not home

        if message.content.startswith(">"):
            if self.check_if_home(message.channel.id) is None:
                await message.channel.send(
                    content="Your server needs to set a home channel for conversations. Use **/set-home**"
                )
                return  # Return if no home set

            elif self.members.find_member(message.author.name):
                # Reset the inactivity timer on the member who sent the message
                self.members.get_member(message.author.name).set_end_time()
                await message.add_reaction("✅")
                prompt: str = (
                    "**"
                    + message.author.name
                    + "**"
                    + " said: "
                    + '"'
                    + message.content[1:]
                    + '"'
                )
                response = self.chatbot.generate_response(prompt)

                # Split reponse into seperate messages if it exceeds text limit
                text_limit = 2000
                if len(response) > text_limit:
                    parsed_response: list = [
                        response[i : i + text_limit]
                        for i in range(0, len(response), text_limit)
                    ]
                    for response in parsed_response:
                        await message.reply(
                            embed=await LoadDisplays.bot_response(
                                response, prompt, DisplayCode.RESPONSE
                            )
                        )
                else:
                    await message.reply(
                        embed=await LoadDisplays.bot_response(
                            response, prompt, DisplayCode.RESPONSE
                        )
                    )

            else:  # If user in not in member list (the conversation)
                try:
                    await message.author.send(
                        "You must use the /join-conversation command to participate."
                    )
                except discord.errors.Forbidden:
                    # The user has DMs disabled
                    await message.channel.send(
                        f"{message.author.mention}, you must use the /join-conversation command to participate.",
                        delete_after=10,
                    )
                return

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Handles the event when the bot is ready.
        """
        print(f"Logged in as {self.bot.user.name}")
        # Assign default instructions from .txt file.
        self.chatbot.read_instructions()
        # TODO remove when publishing
        synced = await self.bot.tree.sync()
        print("Synced... " + str(len(synced)) + " commands")


# Define the AdminCommands class (Cog for admin commands)
class AdminCommands(commands.Cog):
    """
    A cog for the Discord bot's admin commands.

    Attributes:
    -----------
    bot : BotMain
        The BotMain instance.
    chatbot : ChatBot
        The ChatBot instance.
    """
    def __init__(self, bot: BotMain, chatbot: ChatBot) -> None:
        self.bot = bot
        self.chatbot = chatbot

    @app_commands.command(
        name="reset-conversation-history",
        description="[ADMIN] Resets Olly's memory from all messages",
    )
    @admin_command
    async def reset_conversation(self, interaction: discord.Interaction):
        """
        Resets the conversation history of the ChatBot.

        Parameters:
        -----------
        interaction : discord.Interaction
            The interaction that triggered the command.
        """
        self.chatbot.reset_conversation_history()
        await LoadDisplays.general_notification(interaction, DisplayCode.EXECUTE)

    @app_commands.command(
        name="edit-instructions",
        description="[ADMIN] Edit Olly's instructions",
    )
    @admin_command
    async def edit_instructions(self, interaction: discord.Interaction):
        """
        Opens the modal for editing the instructions of the ChatBot.

        Parameters:
        -----------
        interaction : discord.Interaction
            The interaction that triggered the command.
        """
        await interaction.response.send_modal(EditInstructions(self.chatbot))

    @app_commands.command(
        name="reset-instructions",
        description="[ADMIN] Return Olly's instructions to default",
    )
    @admin_command
    async def reset_instructions(
        self,
        interaction: discord.Interaction,
    ):
        """
        Resets the instructions of the ChatBot to their default values.

        Parameters:
        -----------
        interaction : discord.Interaction
            The interaction that triggered the command.
        """
        self.chatbot.reset_instructions()
        await LoadDisplays.edit_bot(
            interaction, self.chatbot, DisplayCode.SHOW_INSTRUCTIONS
        )


# Define the PublicCommands class (Cog for public commands)
class PublicCommands(commands.Cog):
    """
    A cog for the Discord Bot's public commands.

    Attributes:
    -----------
    bot : commands.Bot
        The bot instance.
    bot_main : BotMain
        The BotMain instance.
    chatbot : ChatBot
        The ChatBot instance.
    members : ManageMembers
        The ManageMembers instance.
    """
    def __init__(
        self,
        bot: commands.Bot,
        bot_main: BotMain,
        chatbot: ChatBot,
        members: ManageMembers,
    ) -> None:
        self.bot = bot
        self.bot_main = bot_main
        self.chatbot = chatbot
        self.members = members

    # Join conversation command
    @app_commands.command(
        name="join-conversation", description="Join the conversation!"
    )
    async def join_conversation(self, interaction: discord.Interaction):
        """
        Handles the command to join the conversation so that 
        the member can communicate with the ChatBot.

        Parameters:
        -----------
        interaction : discord.Interaction
            The interaction that triggered the command.
        """
        if interaction.channel.id == self.bot_main.home_channel_id:
            user_name = interaction.user.name
            if self.members.find_member(user_name):
                await interaction.response.send_message(
                    "You're already in the conversation!", ephemeral=True
                )
            else:
                new_member = Member(user_name)
                if self.members.add_member(new_member):
                    await LoadDisplays.member_notification(
                        self.bot, interaction, user_name, self.members, DisplayCode.JOIN
                    )
                else:
                    await interaction.response.send_message(
                        "Conversation is full, try again later", ephemeral=True
                    )
        else:
            await interaction.response.send_message(
                "You need to set a home channel (/set-home) to use this command!"
            )

    # Leave conversation command
    @app_commands.command(
        name="leave-conversation", description="Leave the conversation!"
    )
    async def leave_conversation(self, interaction: discord.Interaction):
        """
        Handles the command to leave the conversation and disable communication with the ChatBot.

        Parameters:
        -----------
        interaction : discord.Interaction
            The interaction that triggered the command.
        """
        user_name = interaction.user.name
        if self.members.remove_member(user_name):
            await LoadDisplays.member_notification(
                self.bot, interaction, user_name, self.members, DisplayCode.LEAVE
            )
        else:
            await interaction.response.send_message(
                "You are not part of the conversation.", ephemeral=True
            )

    @app_commands.command(
        name="view-instructions",
        description="View Olly's current instructions",
    )
    async def view_instruction(self, interaction: discord.Interaction):
        """
        Handles the command to view the current instructions of the ChatBot.

        Parameters:
        -----------
        interaction : discord.Interaction
            The interaction that triggered the command.
        """
        await LoadDisplays.edit_bot(
            interaction, self.chatbot, DisplayCode.SHOW_INSTRUCTIONS
        )


class BackgroundTasks(commands.Cog):
    """
    A cog for background tasks.

    Attributes:
    -----------
    bot : commands.Bot
        The bot instance.
    bot_main : BotMain
        The BotMain instance.
    members : ManageMembers
        The ManageMembers instance.
    """
    def __init__(
        self, bot: commands.Bot, bot_main: BotMain, members: ManageMembers
    ) -> None:
        self.bot = bot
        self.members = members
        self.bot_main = bot_main
        self.check_members.start()

    async def cog_unload(self) -> None:
        """
        Cancels the check_members task when the cog is unloaded.
        """
        self.check_members.cancel()

    @tasks.loop(minutes=1)
    async def check_members(self):
        """
        Checks the members who have used /join-conversation and 
        kicks them after a set elapsed time.
        """
        # Don't run the loop if no one is in conversation.
        if self.members.get_space() == 0:
            return
        for member in self.members.conversation_members:
            member.set_start_time()
            if member.check_time():
                return
            else:
                self.members.conversation_members.remove(member)

                embed = discord.Embed(
                    title=f"⚠️ **{member.name}** was kicked due to inactivity!"
                )
                embed.set_footer(text=self.members.get_space_left())

                channel = self.bot.get_channel(self.bot_main.home_channel_id)
                await channel.send(embed=embed)
