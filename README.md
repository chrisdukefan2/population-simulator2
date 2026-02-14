# Population Simulator

A cohort-based demographic population simulator with a Streamlit web interface.

## Setup (Windows)

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## Features

- **10 countries** with pre-loaded demographic parameters (South Korea, Japan, USA, Germany, Nigeria, Brazil, India, China, France, UK)
- **Cohort-based simulation**: population modeled as 101 age groups (0-100) by sex
- **Interactive controls**: adjust TFR, life expectancy, mortality multiplier, net migration
- **Visualizations**: population time series, births/deaths/migration chart, side-by-side population pyramids
- **CSV export** of simulation results

## Model Assumptions & Approximations

### Fertility
- Age-specific fertility rates (ASFR) are distributed across ages 15-49 using a Beta(2,5) shape, peaking in the mid-20s.
- Total births = sum of (female population at age × ASFR at age) for ages 15-49.
- Births are split into male/female using the country's sex ratio at birth.

### Mortality
- Uses a **Gompertz-Makeham** parametric mortality model: hazard rate = α + β·exp(γ·age).
- Parameters are iteratively calibrated so the implied life expectancy matches the target.
- This is a standard actuarial approximation, **not** country-specific mortality tables.
- All individuals reaching age 100 die (100% mortality at age 100).
- A mortality multiplier slider allows scaling all mortality rates up or down.

### Migration
- Net migration is distributed across working ages (default: 20-39, or concentrated: 25-34).
- Distribution is proportional to existing population in those age groups.
- Migrants are split 50/50 male/female proportional to existing sex ratio in the age range.

### Baseline Age Distributions
- Synthetic age distributions are generated using a stable-population approximation based on each country's TFR and life expectancy.
- These are **approximations** — replace with real data from UN World Population Prospects for accuracy.

## How to Add a New Country

1. Add an entry to `data/countries.json` with the required fields:
   ```json
   {
     "name": "Country Name",
     "code": "XXX",
     "population": 10000000,
     "tfr": 1.80,
     "life_expectancy_male": 75.0,
     "life_expectancy_female": 80.0,
     "net_migration": 10000,
     "sex_ratio_at_birth": 105.0,
     "baseline_year": 2025,
     "notes": "Optional notes"
   }
   ```

2. Create an age distribution CSV at `data/age_distributions/XXX_2025.csv` with columns: `age,male,female` (ages 0-100). If no CSV is provided, a flat synthetic distribution is used as fallback.

3. No code changes required — the new country will appear in the dropdown automatically.

## Data Sources

Country parameters are approximate values based on publicly available demographic data (World Bank, UN Population Division). All values should be verified against authoritative sources for any serious analysis.
