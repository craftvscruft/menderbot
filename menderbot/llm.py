import os

import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

INSTRUCTIONS = (
    """You are helpful electronic assistant with knowledge of Software Engineering."""
)

TEMPERATURE = 0.5
MAX_TOKENS = 500
FREQUENCY_PENALTY = 0
PRESENCE_PENALTY = 0.6
# limits how many questions we include in the prompt
MAX_CONTEXT_QUESTIONS = 10


def is_test_override() -> bool:
    return (
        os.getenv("OPENAI_API_KEY")
        == "sk-TEST00000000000000000000000000000000000000000000"
    )


def override_response_for_test(messages) -> str:
    del messages
    return "<LLM Output>"


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
    # build the messages
    messages = [
        {"role": "system", "content": instructions},
    ]
    # add the previous questions and answers
    for question, answer in previous_questions_and_answers[-MAX_CONTEXT_QUESTIONS:]:
        messages.append({"role": "user", "content": question})
        messages.append({"role": "assistant", "content": answer})
    # add the new question
    messages.append({"role": "user", "content": new_question})

    if is_test_override():
        return override_response_for_test(messages)
    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        top_p=1,
        frequency_penalty=FREQUENCY_PENALTY,
        presence_penalty=PRESENCE_PENALTY,
    )
    return completion.choices[0].message.content


def unwrap_codeblock(text):
    return text.strip().removeprefix("```").removesuffix("```")
