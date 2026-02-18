"""
Synthesizer module for transforming user input into structured search profiles.

Transforms personal_info and holiday_info into separate hard_constraints
and soft_preferences for the hybrid multi-phase screening system.
"""

from common.geocoding import geocode
from common.llm_utils import get_json_response
from common.logging_config import get_logger
from product_synthesizer.types import (
    HardConstraints,
    SemanticExclusions,
    SoftPreferences,
    SynthesizerError,
    SynthesizerOutput,
)

logger = get_logger("product_synthesizer")

# Expansion mappings for constraint terms to related exclusion terms
ACCESSIBILITY_EXPANSIONS: dict[str, list[str]] = {
    "stairs": ["stairs", "steps", "climbing", "steep"],
    "steps": ["stairs", "steps", "climbing", "steep"],
    "walking": ["walking", "hiking", "trekking", "long walk"],
    "standing": ["standing", "queue", "waiting in line"],
    "wheelchair": ["stairs", "steps", "climbing", "steep", "uneven terrain"],
    "mobility": ["stairs", "steps", "climbing", "steep", "hiking", "walking tour"],
}

DIET_EXPANSIONS: dict[str, list[str]] = {
    "gluten": ["wheat", "bread", "pasta", "flour", "gluten", "barley", "rye"],
    "gluten-free": ["wheat", "bread", "pasta", "flour", "gluten", "barley", "rye"],
    "dairy": ["milk", "cheese", "cream", "butter", "dairy", "lactose"],
    "dairy-free": ["milk", "cheese", "cream", "butter", "dairy", "lactose"],
    "vegan": ["meat", "fish", "dairy", "eggs", "honey", "animal"],
    "vegetarian": ["meat", "fish", "poultry", "seafood"],
    "nut": ["nuts", "peanuts", "almonds", "cashews", "walnuts", "tree nuts"],
    "shellfish": ["shellfish", "shrimp", "crab", "lobster", "oyster", "mussel"],
    "kosher": ["pork", "shellfish", "non-kosher"],
    "halal": ["pork", "alcohol", "non-halal"],
}

MEDICAL_EXPANSIONS: dict[str, list[str]] = {
    "asthma": ["smoke", "dust", "fumes", "pollution", "smoky"],
    "heart": ["strenuous", "intense", "extreme", "high altitude"],
    "back": ["bumpy", "rough terrain", "long sitting", "uncomfortable seats"],
    "knee": ["stairs", "steps", "climbing", "hiking", "steep"],
    "allergy": ["pollen", "dust", "animals", "pets"],
    "epilepsy": ["strobe", "flashing lights", "disco"],
    "vertigo": ["heights", "spinning", "rotating", "cable car"],
}

FEAR_EXPANSIONS: dict[str, list[str]] = {
    "heights": ["tower", "rooftop", "cliff", "balcony", "high", "observation deck", "skyscraper"],
    "water": ["boat", "swimming", "diving", "snorkeling", "water", "sea", "ocean"],
    "enclosed": ["cave", "tunnel", "underground", "confined", "small space"],
    "crowds": ["crowded", "busy", "packed", "popular", "tourist hotspot"],
    "flying": ["helicopter", "plane", "paragliding", "skydiving"],
    "animals": ["zoo", "safari", "wildlife", "animal encounter"],
    "dark": ["cave", "underground", "night tour", "dark"],
}

SYSTEM_PROMPT = """You are a Travel Search Synthesizer. Transform the user's Personal Info and Holiday Info into a structured Search Profile with separate hard_constraints and soft_preferences.

RULES:
1. hard_constraints are NON-NEGOTIABLE filters - products violating these MUST be excluded
2. soft_preferences influence RANKING but don't exclude products
3. Extract country as 2-letter ISO code (e.g., "IT" for Italy, "ES" for Spain)
4. Extract city name separately for geocoding (will be resolved to coordinates externally)
5. For semantic_exclusions, expand constraint terms to related terms:
   - accessibility "no stairs" -> ["stairs", "steps", "climbing", "steep"]
   - diet "gluten-free" -> ["wheat", "bread", "pasta", "flour", "gluten"]
   - medical "asthma" -> ["smoke", "dust", "fumes", "pollution"]
   - fears "heights" -> ["tower", "rooftop", "cliff", "balcony", "high"]
6. Build preference_text as a natural sentence describing the ideal experience

Return ONLY this JSON structure:
{
  "hard_constraints": {
    "country": "XX",
    "city": "city name for geocoding",
    "accommodation_address": "address if provided",
    "holiday_begin_date": "YYYY-MM-DD or null",
    "holiday_end_date": "YYYY-MM-DD or null",
    "not_available_date_times": ["ISO datetime strings"],
    "age": integer or null,
    "max_pax": integer or null,
    "semantic_exclusions": {
      "accessibility": ["expanded", "terms"],
      "diet": ["expanded", "terms"],
      "medical": ["expanded", "terms"],
      "fears": ["expanded", "terms"]
    }
  },
  "soft_preferences": {
    "preference_text": "natural sentence describing ideal experience",
    "interests": ["list", "of", "interests"],
    "activity_level": "sedentary|moderate|active or null",
    "sports": ["list", "of", "sports"],
    "languages": ["list", "of", "languages"],
    "notes": "any additional notes or null"
  }
}"""


def _expand_exclusion_terms(terms: list[str], expansion_map: dict[str, list[str]]) -> list[str]:
    """Expand constraint terms to related exclusion terms using the expansion map."""
    expanded = set()
    for term in terms:
        term_lower = term.lower().strip()
        if term_lower in expansion_map:
            expanded.update(expansion_map[term_lower])
        else:
            for key, values in expansion_map.items():
                if key in term_lower or term_lower in key:
                    expanded.update(values)
                    break
            else:
                expanded.add(term_lower)
    return list(expanded)


def _extract_city_from_location(location: str) -> str | None:
    """Extract city name from a location string."""
    if not location:
        return None
    parts = location.split(",")
    if parts:
        return parts[0].strip()
    return location.strip()


def synthesize_profile(
    personal_info: dict, holiday_info: dict
) -> SynthesizerOutput | SynthesizerError:
    """
    Transform user input into structured search profile.

    Uses LLM to extract and categorize constraints/preferences.
    Uses geocoding to resolve locations to coordinates.

    Args:
        personal_info: User's personal information (accessibility, diet, medical, fears, interests)
        holiday_info: Holiday details (location, dates, accommodation, etc.)

    Returns:
        SynthesizerOutput with hard_constraints and soft_preferences, or
        SynthesizerError if LLM fails to parse the response.
    """
    prompt = f"Personal Info: {personal_info}\nHoliday Info: {holiday_info}"
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]

    try:
        llm_response = get_json_response(messages)
    except Exception as e:
        logger.error(f"LLM call failed with exception: {e}")
        return SynthesizerError(
            error=True,
            error_type="llm_exception",
            error_message=f"LLM call failed: {str(e)}",
            raw_response=None,
        )

    if llm_response is None:
        logger.error("LLM returned None - failed to parse JSON response")
        return SynthesizerError(
            error=True,
            error_type="llm_parse_error",
            error_message="LLM failed to return valid JSON response",
            raw_response=None,
        )

    if not isinstance(llm_response, dict):
        logger.error(f"LLM response is not a dict: {type(llm_response)}")
        return SynthesizerError(
            error=True,
            error_type="invalid_response_type",
            error_message=f"Expected dict response, got {type(llm_response).__name__}",
            raw_response=str(llm_response),
        )

    llm_hard = llm_response.get("hard_constraints", {})
    llm_soft = llm_response.get("soft_preferences", {})

    # Process semantic exclusions with expansion
    llm_exclusions = llm_hard.get("semantic_exclusions", {})
    semantic_exclusions: SemanticExclusions = {
        "accessibility": _expand_exclusion_terms(
            llm_exclusions.get("accessibility", []), ACCESSIBILITY_EXPANSIONS
        ),
        "diet": _expand_exclusion_terms(llm_exclusions.get("diet", []), DIET_EXPANSIONS),
        "medical": _expand_exclusion_terms(llm_exclusions.get("medical", []), MEDICAL_EXPANSIONS),
        "fears": _expand_exclusion_terms(llm_exclusions.get("fears", []), FEAR_EXPANSIONS),
    }

    # Resolve city to coordinates
    city = llm_hard.get("city")
    target_coords = None
    if city:
        try:
            target_coords = geocode(city)
            if target_coords is None:
                logger.warning(f"Geocoding failed for city '{city}'")
        except Exception as e:
            logger.warning(f"Geocoding exception for city '{city}': {e}")

    # Resolve accommodation to coordinates
    accommodation = llm_hard.get("accommodation_address")
    accommodation_city = _extract_city_from_location(accommodation) if accommodation else None
    accommodation_coords = None
    if accommodation_city:
        try:
            accommodation_coords = geocode(accommodation_city)
        except Exception as e:
            logger.warning(f"Geocoding exception for accommodation '{accommodation_city}': {e}")

    hard_constraints: HardConstraints = {
        "country": llm_hard.get("country"),
        "target_latitude": target_coords["latitude"] if target_coords else None,
        "target_longitude": target_coords["longitude"] if target_coords else None,
        "accommodation_latitude": accommodation_coords["latitude"]
        if accommodation_coords
        else None,
        "accommodation_longitude": accommodation_coords["longitude"]
        if accommodation_coords
        else None,
        "holiday_begin_date": llm_hard.get("holiday_begin_date"),
        "holiday_end_date": llm_hard.get("holiday_end_date"),
        "not_available_date_times": llm_hard.get("not_available_date_times", []),
        "age": llm_hard.get("age"),
        "max_pax": llm_hard.get("max_pax"),
        "semantic_exclusions": semantic_exclusions,
    }

    soft_preferences: SoftPreferences = {
        "preference_text": llm_soft.get("preference_text", ""),
        "interests": llm_soft.get("interests", []),
        "activity_level": llm_soft.get("activity_level"),
        "sports": llm_soft.get("sports", []),
        "languages": llm_soft.get("languages", []),
        "notes": llm_soft.get("notes"),
    }

    return SynthesizerOutput(
        hard_constraints=hard_constraints,
        soft_preferences=soft_preferences,
    )
