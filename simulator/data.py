"""Data loading: countries, baseline age distributions, and caching."""

import json
import os
import csv
from functools import lru_cache
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MAX_AGE = 100

_FLAGS = {
    "KOR": "🇰🇷",
    "JPN": "🇯🇵",
    "USA": "🇺🇸",
    "DEU": "🇩🇪",
    "NGA": "🇳🇬",
    "BRA": "🇧🇷",
    "IND": "🇮🇳",
    "CHN": "🇨🇳",
    "FRA": "🇫🇷",
    "GBR": "🇬🇧",
    "WLD": "🌍",
}


def _flag_emoji(code3: str) -> str:
    return _FLAGS.get(code3, "")


@lru_cache(maxsize=1)
def load_countries() -> dict:
    """Load countries.json and return a dict mapping display name (with flag) -> country data."""
    path = DATA_DIR / "countries.json"
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    countries = {}
    for c in raw["countries"]:
        flag = _flag_emoji(c["code"])
        display_name = f"{flag} {c['name']}" if flag else c["name"]
        c["display_name"] = display_name
        countries[display_name] = c
    return countries


def get_country_names() -> list[str]:
    """Return sorted list of country display names (with flag emoji)."""
    return sorted(load_countries().keys())


def get_country(name: str) -> dict:
    """Return country data dict for a given display name."""
    return load_countries()[name]


def load_age_distribution(country_code: str, year: int) -> tuple[np.ndarray, np.ndarray]:
    """Load baseline age distribution from CSV.

    Args:
        country_code: ISO 3-letter code (e.g., 'KOR').
        year: Baseline year.

    Returns:
        Tuple of (male_pop, female_pop) arrays of length 101.
    """
    filename = f"{country_code}_{year}.csv"
    path = DATA_DIR / "age_distributions" / filename

    if not path.exists():
        # Fallback: generate a flat synthetic distribution
        return _generate_synthetic_distribution(country_code)

    male_pop = np.zeros(MAX_AGE + 1)
    female_pop = np.zeros(MAX_AGE + 1)

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            age = int(row["age"])
            if 0 <= age <= MAX_AGE:
                male_pop[age] = int(row["male"])
                female_pop[age] = int(row["female"])

    return male_pop, female_pop


def _generate_synthetic_distribution(country_code: str) -> tuple[np.ndarray, np.ndarray]:
    """Generate a flat fallback distribution (used if CSV is missing)."""
    # Try to find the country to get total population
    countries = load_countries()
    pop = 1_000_000  # default
    for c in countries.values():
        if c["code"] == country_code:
            pop = c["population"]
            break

    per_age = pop / (2 * (MAX_AGE + 1))
    male_pop = np.full(MAX_AGE + 1, per_age)
    female_pop = np.full(MAX_AGE + 1, per_age)
    return male_pop, female_pop


def get_available_years(country_code: str) -> list[int]:
    """Return sorted list of years for which age distribution data exists."""
    age_dir = DATA_DIR / "age_distributions"
    prefix = f"{country_code}_"
    years = []
    for f in age_dir.iterdir():
        if f.name.startswith(prefix) and f.suffix == ".csv":
            try:
                year = int(f.stem.split("_")[1])
                years.append(year)
            except (IndexError, ValueError):
                continue
    return sorted(years)


def get_pyramid_url(country_code: str, year: int) -> str:
    """Return a populationpyramid.net URL for the given country and year."""
    # populationpyramid.net uses lowercase 3-letter codes
    code_lower = country_code.lower()
    return f"https://www.populationpyramid.net/{code_lower}/{year}/"
