"""Cohort-based population simulation engine.

Represents population as two arrays (male, female) of length 101 (ages 0-100).
Each annual timestep: age cohorts, apply mortality, calculate births, add migration.
"""

import numpy as np
from dataclasses import dataclass, field

from simulator.demography import (
    build_asfr,
    build_mortality_rates,
    distribute_migration,
    MAX_AGE,
)


@dataclass
class SimulationParams:
    """Parameters for a simulation run."""
    tfr: float
    life_expectancy_male: float
    life_expectancy_female: float
    net_migration: int
    sex_ratio_at_birth: float = 105.0  # males per 100 females
    mortality_multiplier: float = 1.0
    concentrated_migration: bool = False
    start_year: int = 2025
    num_years: int = 50


@dataclass
class YearResult:
    """Results for a single simulation year."""
    year: int
    total_population: int
    male_pop: np.ndarray
    female_pop: np.ndarray
    births: int
    deaths: int
    net_migration: int


@dataclass
class SimulationResult:
    """Complete simulation output."""
    years: list[YearResult] = field(default_factory=list)

    @property
    def year_list(self) -> list[int]:
        return [y.year for y in self.years]

    @property
    def population_series(self) -> list[int]:
        return [y.total_population for y in self.years]

    @property
    def births_series(self) -> list[int]:
        return [y.births for y in self.years]

    @property
    def deaths_series(self) -> list[int]:
        return [y.deaths for y in self.years]

    @property
    def migration_series(self) -> list[int]:
        return [y.net_migration for y in self.years]


def run_simulation(
    male_pop_init: np.ndarray,
    female_pop_init: np.ndarray,
    params: SimulationParams,
) -> SimulationResult:
    """Run cohort-based population simulation.

    Args:
        male_pop_init: Initial male population by single year of age (length 101).
        female_pop_init: Initial female population by single year of age (length 101).
        params: Simulation parameters.

    Returns:
        SimulationResult with yearly data.
    """
    male_pop = male_pop_init.astype(float).copy()
    female_pop = female_pop_init.astype(float).copy()

    asfr = build_asfr(params.tfr)
    mort_m = build_mortality_rates(params.life_expectancy_male, params.mortality_multiplier)
    mort_f = build_mortality_rates(params.life_expectancy_female, params.mortality_multiplier)

    sr_male_frac = params.sex_ratio_at_birth / (100.0 + params.sex_ratio_at_birth)

    result = SimulationResult()

    # Record baseline year
    result.years.append(YearResult(
        year=params.start_year,
        total_population=int(male_pop.sum() + female_pop.sum()),
        male_pop=male_pop.copy(),
        female_pop=female_pop.copy(),
        births=0,
        deaths=0,
        net_migration=0,
    ))

    for i in range(params.num_years):
        year = params.start_year + i + 1

        # --- Deaths ---
        male_deaths = male_pop * mort_m
        female_deaths = female_pop * mort_f
        male_pop -= male_deaths
        female_pop -= female_deaths

        # Ensure non-negative
        male_pop = np.maximum(male_pop, 0)
        female_pop = np.maximum(female_pop, 0)

        total_deaths = int(round(male_deaths.sum() + female_deaths.sum()))

        # --- Births ---
        # Births from female cohorts ages 15-49
        total_births_float = (female_pop[15:50] * asfr[15:50]).sum()
        total_births = int(round(total_births_float))
        male_births = total_births * sr_male_frac
        female_births = total_births - male_births

        # --- Aging: shift everyone up one year ---
        # Age 100 absorbs age 99 + existing 100 (already had mortality applied)
        male_pop[MAX_AGE] = male_pop[MAX_AGE] + male_pop[MAX_AGE - 1]
        female_pop[MAX_AGE] = female_pop[MAX_AGE] + female_pop[MAX_AGE - 1]
        # Shift ages 1..99
        male_pop[1:MAX_AGE] = male_pop[0:MAX_AGE - 1]
        female_pop[1:MAX_AGE] = female_pop[0:MAX_AGE - 1]
        # New births enter age 0
        male_pop[0] = male_births
        female_pop[0] = female_births

        # --- Migration ---
        male_mig, female_mig = distribute_migration(
            params.net_migration, male_pop, female_pop, params.concentrated_migration
        )
        male_pop += male_mig
        female_pop += female_mig

        # Ensure non-negative after migration (negative net migration could cause this)
        male_pop = np.maximum(male_pop, 0)
        female_pop = np.maximum(female_pop, 0)

        total_pop = int(round(male_pop.sum() + female_pop.sum()))

        result.years.append(YearResult(
            year=year,
            total_population=total_pop,
            male_pop=male_pop.copy(),
            female_pop=female_pop.copy(),
            births=total_births,
            deaths=total_deaths,
            net_migration=params.net_migration,
        ))

    return result
