from llm_utils import get_json_response

SYSTEM_PROMPT = """
You are a Travel Search Synthesizer. Combine the User's Personal Info and Holiday Info into a structured Search Profile.

Rules:
1. 'vector_intent': Create a 1-sentence description of the ideal experience (e.g., "Relaxing historical boat tour").
2. 'excluded_terms': If medical/fears are present, list keywords to avoid (e.g., 'asthma' -> ['smoke'], 'knee pain' -> ['stairs', 'hiking']).
3. 'country': Extract the 2-letter ISO code from the location.
4. 'price_max': Convert budget to cents (e.g., 100 EUR -> 10000).

Return ONLY this JSON structure:
{
  "vector_intent": "string",
  "sql_constraints": {
    "country": "string",
    "age": integer,
    "max_pax": integer,
    "price_max": integer,
    "excluded_terms": ["list", "of", "strings"]
  }
}
"""


def synthesize_intent(personal_info, holiday_info):
    prompt = f"Personal Info: {personal_info}\nHoliday Info: {holiday_info}"

    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]

    profile = get_json_response(messages)
    return profile
