"""One-time script to generate synthetic age distribution CSVs for all 10 countries.
These are approximate distributions shaped by each country's demographic profile.
Replace with real data from UN World Population Prospects when available.
"""
import json
import csv
import os
import numpy as np

def generate_age_distribution(population, life_exp_m, life_exp_f, tfr, sex_ratio_birth):
    """Generate a synthetic age distribution using a simplified stable population model."""
    ages = np.arange(101)  # 0 to 100

    # Higher TFR -> younger population (wider base)
    # Lower life expectancy -> steeper decline at old ages
    # Use a combination of exponential decay and birth-rate weighting

    # Growth rate proxy from TFR (replacement is ~2.1)
    growth_rate = (tfr - 2.1) * 0.008  # rough annual growth rate proxy

    # Build survival curves using Gompertz-like model
    def survival_curve(life_exp):
        # Gompertz parameters calibrated to life expectancy
        # S(x) = exp(-a/b * (exp(bx) - 1))
        b = 0.085
        # Solve for a such that integral of S(x) ≈ life_exp
        # Iterative approach
        a = 0.00005
        for _ in range(50):
            sx = np.exp(-a / b * (np.exp(b * ages) - 1))
            integral = sx.sum()
            a *= integral / life_exp
        sx = np.exp(-a / b * (np.exp(b * ages) - 1))
        return sx

    surv_m = survival_curve(life_exp_m)
    surv_f = survival_curve(life_exp_f)

    # Stable population: c(x) = b * exp(-r*x) * l(x)
    # where b is birth rate, r is growth rate, l(x) is survival
    weight = np.exp(-growth_rate * ages)

    male_dist = surv_m * weight
    female_dist = surv_f * weight

    # Normalize to total population with sex ratio at birth
    sr = sex_ratio_birth / 100.0  # males per female
    male_frac = sr / (1 + sr)  # at birth, but we apply to whole pop roughly

    total_raw = male_dist.sum() + female_dist.sum()
    male_pop = (male_dist / total_raw) * population * (male_dist.sum() / total_raw)
    female_pop = (female_dist / total_raw) * population * (female_dist.sum() / total_raw)

    # Re-scale to hit target population
    current_total = male_pop.sum() + female_pop.sum()
    scale = population / current_total
    male_pop = np.round(male_pop * scale).astype(int)
    female_pop = np.round(female_pop * scale).astype(int)

    # Adjust rounding error on age 30
    diff = population - (male_pop.sum() + female_pop.sum())
    male_pop[30] += diff

    return male_pop, female_pop


def main():
    with open("data/countries.json", "r") as f:
        data = json.load(f)

    os.makedirs("data/age_distributions", exist_ok=True)

    for country in data["countries"]:
        code = country["code"]
        year = country["baseline_year"]
        pop = country["population"]
        le_m = country["life_expectancy_male"]
        le_f = country["life_expectancy_female"]
        tfr = country["tfr"]
        sr = country["sex_ratio_at_birth"]

        male_pop, female_pop = generate_age_distribution(pop, le_m, le_f, tfr, sr)

        filename = f"data/age_distributions/{code}_{year}.csv"
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["age", "male", "female"])
            for age in range(101):
                writer.writerow([age, male_pop[age], female_pop[age]])

        total = male_pop.sum() + female_pop.sum()
        print(f"{country['name']} ({code}): generated {total:,} total population")


if __name__ == "__main__":
    main()
