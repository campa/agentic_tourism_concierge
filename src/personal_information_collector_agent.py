from datetime import date

import ollama

from logging_config import setup_logging

# Constants
LIST_OF_STRINGS = "list of strings"

COLLECTION_GUIDE = {
    "full_name": {"hint": "Full Name", "type": "string"},
    "age": {"hint": "Age", "type": "integer"},
    "languages": {"hint": "Spoken Languages", "type": "list of ISO 639 language codes as strings"},
    "activity_level": {
        "hint": "Physical Activity Level (sedentary | moderate | active | athletic)",
        "type": "enum string",
    },
    "sports": {"hint": "Liked Sports", "type": LIST_OF_STRINGS},
    "accessibility": {"hint": "Accessibility Needs", "type": LIST_OF_STRINGS},
    "diet": {"hint": "Dietary Preferences", "type": LIST_OF_STRINGS},
    "interests": {"hint": "Personal Interests", "type": LIST_OF_STRINGS},
    "barriers": {
        "hint": "Issues or Fears or Hated that could limit activities",
        "type": LIST_OF_STRINGS,
    },
    "fears": {
        "hint": "Fears, worries or dislikes that could limit activities",
        "type": LIST_OF_STRINGS,
    },
    "medical": {
        "hint": "Allergies, medical conditions, or environmental sensitivities (like smoke)",
        "type": LIST_OF_STRINGS,
    },
}


def chat_agent():
    # Setup logging
    logger = setup_logging()

    today_date = date.today().strftime("%Y-%m-%d")

    # Helper to build the JSON schema string for the prompt
    schema_elements = [f'"{k}": ({v["type"]})' for k, v in COLLECTION_GUIDE.items()]
    json_schema_instruction = "{\n  " + ",\n  ".join(schema_elements) + "\n}"

    # Helper to build the hints for the conversation
    hints_str = "\n".join([f"- {v['hint']}" for v in COLLECTION_GUIDE.values()])

    # Start with the system instructions
    messages = [
        {
            "role": "system",
            "content": f"""
            Today's date is {today_date}.
            You are a friendly Travel Intake Assistant for 'Agentic Tourism'.
            Your goal: Collect this info: {", ".join(COLLECTION_GUIDE.keys())}.

            HINTS FOR COLLECTION:
            {hints_str}

            RULES:
            - Start by introducing yourself warmly and explain you are here to collect info to better plan a personalized holidays activites.
            - Natural Flow: Ask for only 1 or 2 items at a time. Do not overwhelm the user.
            - Acknowledgment: Briefly acknowledge the user's answers (e.g., "That sounds like a great activity level!").
            - Safety Disclaimer: When discussing medical or physical limitations, mention that you are an AI and this info is only for activity safety.
            - Handle Out-of-Scope Topics Neutrally: If a user mentions hobbies, substances, or activities that are illegal, controversial, or outside the scope
              of travel planning, do not lecture, moralize, or offer health advice. Simply acknowledge that you've noted their preferences and immediately
              transition to the next data point in your list. Example: "I've noted that. Now, to help with the rest of conversation what are your personal
              dietary preferences?"
            - Categorize Sensitivities as Medical: If a user mentions a sensitivity (like smoke, dust, or noise) or a preference related to their physical comfort,
              record it under the "medical" or "health" category.
            - Avoid Medical Diagnosis: Never provide a medical name (like 'Anosmia') or health advice for a symptom. Simply record exactly what the user said.
            - Persist Data: During the Review Phase, ensure that if a user corrected one part of a field, you do not delete the parts they didn't ask to change.

            OPERATING PHASES:
            1. COLLECTION: Converse until all data points are known.
            2. REVIEW: Once all info is gathered, present a tidy bulleted list of everything you've recorded.
               Ask: "Is this all correct, or would you like to change anything?"
               If a piece of information was not provided, mark it as 'Not specified'
            3. CORRECTION: If the user wants to fix something, update your record and show the revised list.
               When a user fixes a detail, update only the specific part mentioned. Retain all other previously collected information in that category.
               Show the full updated list immediately.

            FINAL TRIGGER:
            - ONLY when the user gives a final "Yes" or "Confirm", say exactly: "CONVERSATION_COMPLETE" followed by the JSON summary.
            - Immediately follow with the data in this exact JSON schema:
            {json_schema_instruction}
            """,
        }
    ]

    logger.info("Agent Started")

    # --- FIX: We send a 'user' prompt to trigger the 'assistant' intro ---
    # The user doesn't see this 'Hello', it just wakes up the agent.
    first_input = {"role": "user", "content": "Hello, I'm ready to start the intake."}
    messages.append(first_input)

    response = ollama.chat(model="llama3.1:8b", messages=messages)
    assistant_msg = response["message"]["content"]

    # Add the intro to history and print it
    messages.append({"role": "assistant", "content": assistant_msg})
    print(f"Agent: {assistant_msg}")

    # --- Now enter the normal loop ---
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit"]:
            logger.info("User requested to quit")
            break

        logger.debug(f"User input: {user_input}")
        messages.append({"role": "user", "content": user_input})

        # Get LLM Response
        response = ollama.chat(model="llama3.1:8b", messages=messages)
        assistant_msg = response["message"]["content"]
        messages.append({"role": "assistant", "content": assistant_msg})

        if "CONVERSATION_COMPLETE" in assistant_msg:
            # Display everything except the completion tag
            clean_display = assistant_msg.split("CONVERSATION_COMPLETE")[0].strip()
            print(f"\nAgent: {clean_display}")
            logger.info("Data collection completed successfully")
            print("\n--- [System] Data Collection Finished. Moving to Step 2... ---")
            break
        else:
            print(f"Agent: {assistant_msg}")


if __name__ == "__main__":
    chat_agent()
