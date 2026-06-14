import os
import re
import json
import config
import questionary
from classifier import classify_job
from scraper import scrape_job
from generator import generate_application, clean_job_title


# =============================================================================
# Paths
# =============================================================================

_LOCATIONS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locations.json")


# =============================================================================
# Location And Profile Selection
# =============================================================================

def _load_locations() -> dict:
    if not os.path.exists(_LOCATIONS_PATH):
        print("  WARNING: locations.json not found - auto-detection disabled. Copy locations.example.json to locations.json to enable it.")
        return {}
    with open(_LOCATIONS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _sync_new_countries(locations: dict):
    """Warn and print config.py snippet for any country in locations.json with no profile."""
    known = set(config.PROFILES.keys())
    new_countries = [c for c in locations if c not in known]
    if not new_countries:
        return
    for country in new_countries:
        print(f"\n  WARNING: '{country}' is in locations.json but has no profile in config.py.")
        print(f"  Add this block to the PROFILES dict in config.py:\n")
        print(f'    "{country}": {{')
        print(f'        "OUTPUT_BASE":   r"C:\\Path\\To\\Applications\\{country}",')
        print(f'        "TEMPLATE_BASE": r"C:\\Path\\To\\Templates\\{country}",')
        print(f'    }},')
    print()
    raise SystemExit(1)


def _detect_profile(country: str | None, locations: dict) -> str | None:
    if not country:
        return None
    country_lower = country.lower()
    for profile_name, loc_list in locations.items():
        for loc in loc_list:
            if re.search(r'\b' + re.escape(loc) + r'\b', country_lower):
                return profile_name
    return None


def _select_profile() -> str:
    profiles = list(config.PROFILES.keys())
    configured_default = getattr(config, "DEFAULT_PROFILE", None)
    default = configured_default if configured_default in profiles else profiles[0]
    print("  Location not detected")
    choice = questionary.select(
        "Select country:",
        choices=profiles,
        default=default,
    ).ask()
    return choice or default


# =============================================================================
# CLI Loop
# =============================================================================

def _run_once():
    try:
        url = input("Paste job URL (or q to quit): ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return False
    if url.lower() in ("q", "quit", "exit", ""):
        return False

    try:
        return _process(url)
    except KeyboardInterrupt:
        print("\n  Cancelled. Ready for next URL.\n")
        return True
    except Exception as e:
        print(f"\n  ERROR: {e}\n  Moving on to next URL.\n")
        return True


# =============================================================================
# Application Flow
# =============================================================================

def _process(url):
    data = scrape_job(url)
    print()

    # Profile selection
    if hasattr(config, "PROFILES") and config.PROFILES:
        locations = _load_locations()
        _sync_new_countries(locations)
        detected_profile = _detect_profile(data.get("country"), locations)
        if detected_profile:
            profile_name = detected_profile
            print(f"  Country:  {profile_name}")
        else:
            profile_name = _select_profile()
        profile = config.PROFILES[profile_name]
        config.OUTPUT_BASE   = profile["OUTPUT_BASE"]
        config.TEMPLATE_BASE = profile["TEMPLATE_BASE"]
        print()

    data["title"] = clean_job_title(data["title"])
    category = classify_job(data["title"], data.get("description", ""))

    # Final review: title, company, category
    print(f"  Title:    {data.get('title', '')}")
    print(f"  Company:  {data.get('company', 'UNKNOWN')}")
    posting_context = data.get("posting_context", "direct_employer")
    posting_company = data.get("posting_company")
    if posting_company:
        print(f"  Posted by: {posting_company}")
    if posting_context != "direct_employer":
        print(f"  Posting:  {posting_context.replace('_', ' ')}")
    print(f"  Category: {category}")
    print()

    proceed = questionary.select(
        "Proceed with these?",
        choices=["Yes", "No - edit title", "No - edit company", "No - edit title and company", "No - edit category", "No - edit all"],
    ).ask()

    if proceed and proceed.startswith("No"):
        edit_all = "all" in proceed
        edit_title    = "title"    in proceed or edit_all
        edit_company  = "company"  in proceed or edit_all
        edit_category = "category" in proceed or edit_all

        if edit_title:
            new_title = input(f"  Title [{data['title']}]: ").strip()
            if new_title:
                data["title"] = new_title

        if edit_company:
            new_company = input(f"  Company [{data.get('company', 'UNKNOWN')}]: ").strip()
            if new_company:
                data["company"] = new_company

        if edit_category:
            available = sorted([
                f for f in os.listdir(config.TEMPLATE_BASE)
                if os.path.isdir(os.path.join(config.TEMPLATE_BASE, f))
            ])
            category = questionary.select(
                "Select category:",
                choices=available,
                default=category if category in available else available[0],
            ).ask() or category

        print()

    generate_application(data, category=category)
    print()
    return True


if __name__ == "__main__":
    while _run_once():
        pass
