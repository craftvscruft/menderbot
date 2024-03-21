import os
from typing import Optional

from llama_index.core import Settings
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.core.llms import ChatMessage, MessageRole

# from openai import Client
from llama_index.llms.openai import OpenAI  # type: ignore[import-untyped]
from tenacity import retry, stop_after_attempt, wait_random_exponential

from menderbot.config import has_llm_consent, load_config

INSTRUCTIONS = (
    """You are helpful electronic assistant with knowledge of Software Engineering."""
)

MODEL = "gpt-4-1106-preview"
TEMPERATURE = 0.5
MAX_TOKENS = 1000
FREQUENCY_PENALTY = 0
PRESENCE_PENALTY = 0.6
# limits how many questions we include in the prompt
MAX_CONTEXT_QUESTIONS = 10


__openai_client: Optional[OpenAI] = None
__key_env_var = "OPENAI_API_KEY"


def key_env_var() -> str:
    return __key_env_var


def init_openai():
    # pylint: disable-next=[global-statement]
    global __openai_client
    global __key_env_var
    if has_llm_consent():
        config = load_config()
        openai_config = config.get("apis", {}).get("openai", {})
        __key_env_var = openai_config.get("api_key_env_var", "OPENAI_API_KEY")
        organization_env_var = openai_config.get(
            "organization_env_var", "OPENAI_ORGANIZATION"
        )
        __openai_client = OpenAI(
            api_key=os.getenv(__key_env_var),
            organization=os.getenv(organization_env_var),
            base_url=openai_config.get("api_base", "https://api.openai.com/v1"),
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            top_p=1,
            frequency_penalty=FREQUENCY_PENALTY,
            presence_penalty=PRESENCE_PENALTY,
        )


init_openai()


def is_test_override() -> bool:
    return (
        os.getenv(key_env_var())
        == "sk-TEST00000000000000000000000000000000000000000000"
    )


def has_key() -> bool:
    return os.getenv(key_env_var(), "") != ""


def override_response_for_test(messages) -> str:
    del messages
    return "<LLM Output>"


def is_debug():
    return os.getenv("DEBUG_LLM", "0") == "1"


@retry(wait=wait_random_exponential(min=3, max=90), stop=stop_after_attempt(3))
def get_response(
    instructions: str, previous_questions_and_answers: list, new_question: str
) -> str:
    """Get a response from ChatCompletion

    Args:
        instructions: The instructions for the chat bot - this determines how it will behave
        previous_questions_and_answers: Chat history
        new_question: The new question to ask the bot

    Returns:
        The response text
    """
    global __openai_client
    # build the messages
    history = [
        ChatMessage(role=MessageRole.SYSTEM, content=instructions),
    ]
    # add the previous questions and answers
    for question, answer in previous_questions_and_answers[-MAX_CONTEXT_QUESTIONS:]:
        history.append(ChatMessage(role=MessageRole.USER, content=question))
        history.append(ChatMessage(role=MessageRole.ASSISTANT, content=answer))

    if is_debug():
        print("=== sending to LLM ===")
        for message in history:
            print(message.role, message.content)
        print("===")
    if is_test_override():
        return override_response_for_test(history)
    if __openai_client is None:
        raise ValueError("OpenAI client is not initialized, check consent?")
    Settings.llm = __openai_client
    chat_engine = SimpleChatEngine.from_defaults(
        chat_history=history,
    )
    # completion = __openai_client.chat.create(
    #     model=MODEL,
    #     messages=messages,

    # )
    message = ChatMessage(role=MessageRole.USER, content=new_question)
    return chat_engine.chat(message=message).choices[0].content
    # return completion.choices[0].message.content


def unwrap_codeblock(text):
    return text.strip().removeprefix("```").removesuffix("```")
