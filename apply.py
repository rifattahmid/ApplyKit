import os
import json
import config
import questionary
from scraper import scrape_job
from generator import generate_application

_LOCATIONS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locations.json")


def _load_locations() -> dict:
    if not os.path.exists(_LOCATIONS_PATH):
        print("  WARNING: locations.json not found — auto-detection disabled. Copy locations.example.json to locations.json to enable it.")
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
            if loc in country_lower or country_lower in loc:
                return profile_name
    return None


def _select_profile() -> str:
    profiles = list(config.PROFILES.keys())
    default = profiles[0]
    print("  Location not detected")
    choice = questionary.select(
        "Select country:",
        choices=profiles,
        default=default,
    ).ask()
    return choice or default


url = input("Paste job URL: ").strip()

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

# Title + company review
print(f"  Title:    {data.get('title', '')}")
print(f"  Company:  {data.get('company', 'UNKNOWN')}")
print()

proceed = questionary.select(
    "Proceed with these?",
    choices=["Yes", "No — edit title", "No — edit company", "No — edit both"],
).ask()

if proceed and proceed.startswith("No"):
    edit_both = "both" in proceed
    edit_title = "title" in proceed or edit_both
    edit_company = "company" in proceed or edit_both

    if edit_title:
        new_title = input(f"  Title [{data['title']}]: ").strip()
        if new_title:
            data["title"] = new_title

    if edit_company:
        new_company = input(f"  Company [{data.get('company', 'UNKNOWN')}]: ").strip()
        if new_company:
            data["company"] = new_company

    print()

generate_application(data)
