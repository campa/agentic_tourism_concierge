import json

from matcher import screen_products
from synthesizer import synthesize_intent


def main():
    # 1. Example input from the 'personal_information_collector'
    # This represents 'Who' the user is.
    personal_info = {
        "full_name": "Mario Rossi",
        "age": 72,
        "languages": ["it", "en"],
        "activity_level": "sedentary",
        "sports": ["golf"],
        "accessibility": ["no stairs", "elevator required"],
        "diet": ["gluten-free"],
        "interests": ["history", "art", "classical music"],
        "fears": ["heights", "vertigo"],
        "medical": ["recent knee surgery", "asthma"],
    }

    # 2. Example input from the 'holiday_information_collector'
    # This represents 'What' they want to do.
    holiday_info = {
        "holiday_begin_date": "2025-10-20",
        "holiday_end_date": "2025-10-27",
        "location": "Venice, IT",
        "accommodation": "Hotel near St. Marks",
        "preferred_date_times": ["2025-10-22T10:00", "2025-10-23T15:00"],
        "not_available_date_times": ["2025-10-25T09:00"],
        "notes": "Traveling with my wife, looking for romantic but very easy-going experiences.",
    }

    print("--- 🧠 Synthesizing Search Profile ---")
    # Step A: Convert raw human data into a structured search profile
    # The LLM will notice 'knee surgery' + 'vertigo' and add safety exclusions.
    search_profile = synthesize_intent(personal_info, holiday_info)

    print(f"Synthesized Intent: {search_profile['vector_intent']}")
    print(f"SQL Constraints: {json.dumps(search_profile['sql_constraints'], indent=2)}")

    print("\n--- 🔍 Querying Flattened Product Catalog ---")
    # Step B: Search the flattened OCTO database using the profile
    # This will filter for Senior tickets in Italy with NO 'stairs' or 'climbing'.
    results = screen_products(search_profile)

    if not results.empty:
        print(f"✅ Found {len(results)} matching experiences:")
        for _, row in results.iterrows():
            print(f"- {row['title']} (Option: {row['option_name']})")
            print(
                f"  Price: {row['price_amount'] / 100} {row['currency']} | Age: {row['min_age']}-{row['max_age']}"
            )
    else:
        print("❌ No experiences matched the criteria.")


if __name__ == "__main__":
    main()
