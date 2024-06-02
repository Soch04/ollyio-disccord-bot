import json
import requests


class ChatBot:
    """
    A class to represent a ChatBot.

    Attributes:
    -----------
    url : str
        The URL of the local API for generating responses.
    headers : dict
        The headers for the API requests.
    name : str
        The name of the ChatBot.
    commands : str
        The initial commands for the ChatBot.
    personality : str
        The personality of the ChatBot.
    goal : str
        The goal of the ChatBot.
    restriction : str
        The restrictions for the ChatBot.
    instructions : str
        The instructions for the ChatBot.
    conversation_history : list
        The history of the conversation.
    conversation_length : int
        The maximum length of the conversation history.
    """
    def __init__(self):
        self.url = "http://localhost:11434/api/generate"
        self.headers = {"Content-Type": "applications/json"}

        self.name = "Olly" # Currently unused, but may have a use later.

        self.commands = (
            'You are in a Discord server. You will be introduced to many server residents'
            'who begin their text prompts with their "name" and said: "content."'
            'You should address them by their displayed name unless they say otherwise.'
            'The following instructions, if any, are set by the individual server owners'
            'and you should follow it with care,'
            'even if it\'s ridiculous.'
        )

        # Split as it is editable by the user
        self.personality: str = ""
        self.goal: str = ""
        self.restriction: str  = ""

        self.instructions: str = ""

        self.conversation_history = [self.commands + self.instructions]
        self.conversation_length: int = 31

    def read_instructions(self) -> None:
        """
        Reads the default instructions from a file and sets the 
        personality, goal, and restrictions of the ChatBot.
        """
        with open('default_instructions.txt', 'r', encoding="utf-8") as file:
            lines = file.readlines()

        self.personality = lines[0].strip()
        self.goal = lines[1].strip()
        self.restriction = lines[2].strip()

        self.instructions = (
            "PERSONALITY: "
            + self.personality
            + "\n\nGOAL: "
            + self.goal
            + "\n\nRESTRICTION: "
            + self.restriction
        )

    # prompt is user's text
    def generate_response(self, prompt: str) -> str:
        """
        Generates a response to a given prompt using the local API.

        Parameters:
        -----------
        prompt : str
            The prompt to generate a response for.

        Returns:
        --------
        str
            The generated response.
        """
        self.conversation_history.append(prompt)

        full_prompt = "\n".join(self.conversation_history)

        data = {"model": "llama3", "prompt": full_prompt, "stream": False}

        response = requests.post(self.url, headers=self.headers, data=json.dumps(data))

        if response.status_code == 200:
            response_text = response.text
            data = json.loads(response_text)
            actual_reponse = data["response"]
            self.conversation_history.append(actual_reponse)

            # Manage the conversation_history length.
            if len(self.conversation_history) >= self.conversation_length:
                # remove the most recent prompt in the list, exclusing the initial prompt.
                del self.conversation_history[1]

            return actual_reponse

        else:
            print("Error:", response.status_code, response.text)
            return "(No Response)"

    def reset_conversation_history(self) -> None:
        """
        Resets the conversation history to the initial commands and instructions.
        """
        self.conversation_history = [self.commands + self.instructions]

    def edit_instructions(
        self,
        personality: str | None = None,
        goal: str | None = None,
        restriction: str | None = None,
    ) -> None:
        """
        Edits the instructions of the ChatBot.

        Parameters:
        -----------
        personality : str, optional
            The new personality for the ChatBot.
        goal : str, optional
            The new goal for the ChatBot.
        restriction : str, optional
            The new restrictions for the ChatBot.
        """

        self.instructions = (
            "PERSONALITY: "
            + personality
            + "\n\nGOAL: "
            + goal
            + "\n\nRESTRICTION: "
            + restriction
        )

        # Apply changes
        self.reset_conversation_history()

    def reset_instructions(self) -> None:
        """
        Resets the instructions of the ChatBot to their default values.
        """
        self.read_instructions()
