import json

import chainlit as cl

from common.llm_utils import extract_json, get_ai_response
from common.logging_config import get_logger
from core import get_first_message, get_system_instructions

# Init - Module level vars
logger = get_logger("personal_information_collector_app")


@cl.on_chat_start
async def start():
    logger.debug("Agent started")
    history = [{"role": "system", "content": get_system_instructions()}]
    history.append({"role": "user", "content": get_first_message()})

    response_text = get_ai_response(history)
    history.append({"role": "assistant", "content": response_text})

    cl.user_session.set("history", history)
    logger.debug(f"""history: {history}""")
    await cl.Message(content=response_text).send()


@cl.on_message
async def main(message: cl.Message):
    history = cl.user_session.get("history")
    history.append({"role": "user", "content": message.content})

    raw_response = get_ai_response(history)
    clean_text, json_data = extract_json(raw_response)

    if json_data:
        await cl.Message(content=clean_text).send()

        await cl.Message(
            content="--- [System] Data Collection Finished. ---",
            elements=[
                cl.Text(
                    name="Traveler Profile JSON",
                    content=json.dumps(json_data, indent=2),
                    display="inline",
                )
            ],
        ).send()
    else:
        await cl.Message(content=raw_response).send()

    history.append({"role": "assistant", "content": raw_response})
    cl.user_session.set("history", history)
