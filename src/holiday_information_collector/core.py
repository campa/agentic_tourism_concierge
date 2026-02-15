from datetime import date

from common.logging_config import get_logger

# Constants
LIST_OF_STRINGS = "list of strings"

# Constants

# TO_BE: New COLLECTION_GUIDE for Holiday Info
COLLECTION_GUIDE = {
    "holiday_begin_date": {"hint": "Holiday Start Date (YYYY-MM-DD)", "type": "string"},
    "holiday_end_date": {"hint": "Holiday End Date (YYYY-MM-DD)", "type": "string"},
    "location": {"hint": "Destination Location (City/Country)", "type": "string"},
    "accommodation": {
        "hint": "Type of Accommodation (Hotel, Airbnb, Camping, etc.)",
        "type": "string",
    },
    "preferred_date_times": {
        "hint": "Specific dates/times you'd love to book activities (YYYY-MM-DDTHH:MM)",
        "type": LIST_OF_STRINGS,
    },
    "not_available_date_times": {
        "hint": "Dates/times you are busy or unavailable (YYYY-MM-DDTHH:MM)",
        "type": LIST_OF_STRINGS,
    },
    "notes": {"hint": "Extra notes or special requests for the trip", "type": "string (optional)"},
}

# Init - Module level vars
logger = get_logger("holiday_information_collector_core")


# Functions
def get_system_instructions() -> str:
    """Generate the dynamic System Prompt based on the NEW Holiday COLLECTION_GUIDE."""
    today_date = date.today().strftime("%Y-%m-%d")

    # Helper to build the JSON schema string
    schema_elements = [f'"{k}": ({v["type"]})' for k, v in COLLECTION_GUIDE.items()]
    json_schema_instruction = "{\n  " + ",\n  ".join(schema_elements) + "\n}"

    # Helper to build hints
    hints_str = "\n".join([f"- {v['hint']}" for v in COLLECTION_GUIDE.values()])

    # TO BE: Updated Prompt for Holiday Intake
    system_prompt = f"""
            "role": "system",
            "content":"
            Today's date is {today_date}.
            You are a friendly 'Holiday Planning Assistant' for the Agentic Tourism Concierge.
            Your goal: Collect holiday logistics: {", ".join(COLLECTION_GUIDE.keys())}.

            HINTS FOR COLLECTION:
            {hints_str}

            RULES:
            - Introduction: Greet the user and explain you're gathering the logistics to sync their calendar with local holiday activities.
            - Natural Flow: Ask for dates first, then location. Do not ask for everything at once.
            - Date Validation: If a user says 'Next Friday', calculate the date based on {today_date} and confirm the YYYY-MM-DD format.
            - Professionalism: Maintain a helpful, travel-concierge tone.
            - Handle Transitions: If they mention personal info, acknowledge it briefly but pivot back to the holiday dates and location.

            OPERATING PHASES:
            1. COLLECTION: Converse until all logistical data points are known.
            2. REVIEW: Present a compact two-column summary.
                ┌─────────────────────┬──────────────────────────────┐
                │ Start Date          │ [holiday_begin_date]         │
                │ End Date            │ [holiday_end_date]           │
                │ Location            │ [location]                   │
                │ Accommodation       │ [accommodation]              │
                │ Preferred Times     │ [preferred_date_times]       │
                │ Unavailable Times   │ [not_available_date_times]   │
                │ Extra Notes         │ [notes]                      │
                └─────────────────────┴──────────────────────────────┘

               Ask: 'Does this reflect your travel plans correctly?'
            3. CORRECTION: Update only the specific fields requested and reshow the table.

            FINAL TRIGGER:
            - ONLY when the user gives a final confirmation, say exactly: 'CONVERSATION_COMPLETE' followed by the JSON summary.

            JSON OUTPUT SCHEMA:
            {json_schema_instruction}
            "
            """
    return system_prompt


def get_first_message() -> str:
    return "Hello, I'm ready to start the holiday intake"
