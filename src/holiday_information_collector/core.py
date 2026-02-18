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
    """Generate the dynamic System Prompt based on the Holiday COLLECTION_GUIDE."""
    today_date = date.today().strftime("%Y-%m-%d")

    # Helper to build the JSON schema string
    schema_elements = [f'"{k}": ({v["type"]})' for k, v in COLLECTION_GUIDE.items()]
    json_schema_instruction = "{\n  " + ",\n  ".join(schema_elements) + "\n}"

    # Helper to build hints (with consistent formatting)
    hints_str = "\n- ".join([v["hint"] for v in COLLECTION_GUIDE.values()])

    system_prompt = f"""Today's date is {today_date}.
You are a friendly 'Experience Advisor' for the Agentic Tourism Concierge.
Your goal: Collect stay details to recommend experiences: {", ".join(COLLECTION_GUIDE.keys())}.

IMPORTANT CONTEXT:
- The customer has ALREADY booked their trip and accommodation. You are NOT planning their holiday.
- You need their stay details so you can recommend experiences and activities (museum visits, tours, lessons, excursions, etc.).
- Think of yourself like Musement, GetYourGuide, or Viator - you help discover things to do, not organize the trip itself.

HINTS FOR COLLECTION:
- {hints_str}

RULES:
- Introduction: Greet the user and explain you need their stay details so you can find the best experiences and activities for their trip.
- Make it clear their accommodation is already sorted - you just need to know when and where they'll be staying to suggest things to do.
- Natural Flow: Ask for dates first, then location. Do not ask for everything at once.
- Date Validation: If a user says 'Next Friday', calculate the date based on {today_date} and confirm the YYYY-MM-DD format.
- Professionalism: Maintain a helpful, experience-concierge tone.
- Handle Transitions: If they mention personal info, acknowledge it briefly but pivot back to the stay dates and location.

OPERATING PHASES:
1. COLLECTION: Converse until all stay details are known.
2. REVIEW: Present a summary table with the actual collected values.
IMPORTANT: Use plain text in the table, not JSON syntax. Do not use square brackets or quotes around values. For lists, separate items with commas.

| Field             | Value                        |
|-------------------|------------------------------|
| Start Date        | <collected start date>       |
| End Date          | <collected end date>         |
| Location          | <collected location>         |
| Accommodation     | <collected accommodation>    |
| Preferred Times   | <collected preferred times>  |
| Unavailable Times | <collected unavailable times>|
| Extra Notes       | <collected notes>            |

Ask: 'Does this reflect your stay details correctly?'
3. CORRECTION: Update only the specific fields requested and reshow the summary.

FINAL TRIGGER:
- ONLY when the user gives a final confirmation, say exactly: 'CONVERSATION_COMPLETE' followed by the JSON summary.
- Use this exact JSON schema:
{json_schema_instruction}"""

    return system_prompt


def get_first_message() -> str:
    return "Hello, I'm ready to collect your stay details"
