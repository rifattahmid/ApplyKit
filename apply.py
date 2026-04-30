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

# Company confirmation
detected_company = data.get("company", "UNKNOWN")
company_input = input(f"Company name [{detected_company}]: ").strip()
data["company"] = company_input if company_input else detected_company

generate_application(data)
