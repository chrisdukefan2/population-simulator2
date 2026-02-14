"""Fertility and mortality helper functions.

Approximations used:
- Fertility: Beta-distribution-shaped ASFR across ages 15-49, scaled to match TFR.
- Mortality: Gompertz-Makeham model calibrated to target life expectancy.
  This is a standard actuarial approximation, not country-specific mortality tables.
"""

import numpy as np

MAX_AGE = 100  # ages 0..100 inclusive (101 buckets)


def build_asfr(tfr: float) -> np.ndarray:
    """Build age-specific fertility rates for ages 0..100.

    Uses a Beta-distribution shape over ages 15-49 (shifted/scaled)
    so that sum of ASFR[15..49] = TFR.

    Returns:
        Array of length 101 where asfr[age] is the expected number of
        births per woman of that age in one year.
    """
    asfr = np.zeros(MAX_AGE + 1)
    fertile_ages = np.arange(15, 50)

    # Map 15-49 to 0-1 range, use Beta(2, 5) shape (peak around early-mid 20s)
    t = (fertile_ages - 15) / 34.0
    weights = t ** (2 - 1) * (1 - t) ** (5 - 1)  # Beta(2,5) unnormalized

    # Normalize so weights sum to TFR
    weights = weights / weights.sum() * tfr

    asfr[15:50] = weights
    return asfr


def build_mortality_rates(life_expectancy: float, mortality_multiplier: float = 1.0) -> np.ndarray:
    """Build age-specific mortality rates (probability of dying in a given year).

    Uses the Gompertz-Makeham model: mu(x) = alpha + beta * exp(gamma * x)
    Parameters are calibrated iteratively so that the implied life expectancy
    (integral of survival curve) approximately matches the target.

    Args:
        life_expectancy: Target life expectancy at birth.
        mortality_multiplier: Scaling factor on mortality rates (1.0 = default).

    Returns:
        Array of length 101 where mortality[age] is probability of dying at that age.
    """
    ages = np.arange(MAX_AGE + 1, dtype=float)

    # Gompertz-Makeham: hazard mu(x) = alpha + beta * exp(gamma * x)
    alpha = 0.0005  # background mortality (accidents, etc.)
    gamma = 0.085    # rate of aging

    # Iteratively calibrate beta to match life expectancy
    beta = 0.00005
    for _ in range(80):
        hazard = alpha + beta * np.exp(gamma * ages)
        # Survival: S(x) = exp(-cumulative_hazard)
        cum_hazard = np.cumsum(hazard)
        survival = np.exp(-cum_hazard)
        # Life expectancy ≈ sum of survival probabilities (discrete approx)
        implied_le = survival.sum()
        beta *= implied_le / life_expectancy

    # Final hazard and convert to probability of dying: q(x) = 1 - exp(-mu(x))
    hazard = (alpha + beta * np.exp(gamma * ages)) * mortality_multiplier
    mortality = 1.0 - np.exp(-hazard)
    mortality = np.clip(mortality, 0.0, 1.0)

    # Force mortality at age 100 to be high (cap the population)
    mortality[MAX_AGE] = 1.0

    return mortality


def distribute_migration(net_migration: int, male_pop: np.ndarray, female_pop: np.ndarray,
                         concentrated: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Distribute net migration across age groups.

    Args:
        net_migration: Total net migrants (positive = immigration).
        male_pop: Current male population by age.
        female_pop: Current female population by age.
        concentrated: If True, concentrate in ages 25-34; otherwise spread across 20-39.

    Returns:
        Tuple of (male_migrants, female_migrants) arrays of length 101.
    """
    male_mig = np.zeros(MAX_AGE + 1)
    female_mig = np.zeros(MAX_AGE + 1)

    if net_migration == 0:
        return male_mig, female_mig

    if concentrated:
        age_lo, age_hi = 25, 34
    else:
        age_lo, age_hi = 20, 39

    # Distribute proportional to existing population in the age range
    male_weight = male_pop[age_lo:age_hi + 1].astype(float)
    female_weight = female_pop[age_lo:age_hi + 1].astype(float)

    total_weight = male_weight.sum() + female_weight.sum()
    if total_weight == 0:
        # Fallback: uniform distribution
        n_ages = age_hi - age_lo + 1
        male_weight = np.ones(n_ages)
        female_weight = np.ones(n_ages)
        total_weight = male_weight.sum() + female_weight.sum()

    male_mig[age_lo:age_hi + 1] = net_migration * (male_weight / total_weight)
    female_mig[age_lo:age_hi + 1] = net_migration * (female_weight / total_weight)

    return male_mig, female_mig
