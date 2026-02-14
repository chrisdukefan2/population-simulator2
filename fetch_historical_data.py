"""Fetch historical age distribution data from populationpyramid.net.

Downloads data for all configured countries from 1950-2024 and saves
as single-year age CSVs compatible with the simulator.
"""

import csv
import io
import os
import time
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data" / "age_distributions"

CODE3_TO_NUMERIC = {
    "KOR": "410",
    "JPN": "392",
    "USA": "840",
    "DEU": "276",
    "NGA": "566",
    "BRA": "076",
    "IND": "356",
    "CHN": "156",
    "FRA": "250",
    "GBR": "826",
    "WLD": "900",
}

API_URL = "https://www.populationpyramid.net/api/pp/{code}/{year}/?csv=1"

YEAR_START = 1950
YEAR_END = 2024


def parse_5year_bins(csv_text: str) -> list[tuple[str, int, int]]:
    """Parse API CSV response into list of (age_label, male, female) tuples."""
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []
    for row in reader:
        age_label = row["Age"].strip()
        male = int(row["M"])
        female = int(row["F"])
        rows.append((age_label, male, female))
    return rows


def expand_to_single_years(bins: list[tuple[str, int, int]]) -> list[tuple[int, int, int]]:
    """Convert 5-year bins to single-year ages (0-100).

    Each bin's population is distributed evenly across its years.
    The 100+ bin maps entirely to age 100.
    """
    single = {}
    for label, male, female in bins:
        if label == "100+":
            single[100] = (male, female)
        else:
            parts = label.split("-")
            start = int(parts[0])
            end = int(parts[1])
            span = end - start + 1
            m_per_year = male / span
            f_per_year = female / span
            for age in range(start, end + 1):
                if age <= 100:
                    single[age] = (round(m_per_year), round(f_per_year))

    # Ensure all ages 0-100 are present
    result = []
    for age in range(101):
        m, f = single.get(age, (0, 0))
        result.append((age, m, f))
    return result


def fetch_and_save(code3: str, year: int) -> bool:
    """Fetch data for one country/year and save as CSV. Returns True if successful."""
    out_path = DATA_DIR / f"{code3}_{year}.csv"
    if out_path.exists():
        return True  # already fetched

    numeric = CODE3_TO_NUMERIC[code3]
    url = API_URL.format(code=numeric, year=year)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PopulationSimulator/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            csv_text = resp.read().decode("utf-8")
    except Exception as e:
        print(f"  FAILED {code3} {year}: {e}")
        return False

    bins = parse_5year_bins(csv_text)
    single_years = expand_to_single_years(bins)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["age", "male", "female"])
        for age, m, fe in single_years:
            writer.writerow([age, m, fe])

    return True


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    countries = list(CODE3_TO_NUMERIC.keys())
    total = len(countries) * (YEAR_END - YEAR_START + 1)
    done = 0
    failed = 0

    for code3 in countries:
        print(f"\n{code3}:")
        for year in range(YEAR_START, YEAR_END + 1):
            done += 1
            out_path = DATA_DIR / f"{code3}_{year}.csv"
            if out_path.exists():
                continue  # skip already fetched

            ok = fetch_and_save(code3, year)
            if not ok:
                failed += 1
            else:
                print(f"  {year}", end="", flush=True)

            # Small delay to be respectful
            time.sleep(0.15)
        print()

    print(f"\nDone. {done} total, {failed} failed.")


if __name__ == "__main__":
    main()
