"""Population Simulator - Streamlit UI.

Cohort-based demographic simulation with interactive controls and visualizations.
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from simulator.data import get_country_names, get_country, load_age_distribution, get_pyramid_url, get_available_years
from simulator.model import run_simulation, SimulationParams

st.set_page_config(page_title="Population Simulator", layout="wide")
st.title("Population Simulator")

# ── Sidebar: Country selection and parameters ──────────────────────────

st.sidebar.header("Country & Parameters")

country_names = get_country_names()
default_idx = next((i for i, n in enumerate(country_names) if "South Korea" in n), 0)
selected_country = st.sidebar.selectbox("Country", country_names, index=default_idx)

country = get_country(selected_country)

# Store defaults for reset
defaults = {
    "tfr": country["tfr"],
    "le_male": country["life_expectancy_male"],
    "le_female": country["life_expectancy_female"],
    "net_migration": country["net_migration"],
    "mortality_mult": 1.0,
}

# Initialize session state for reset functionality
if "reset_counter" not in st.session_state:
    st.session_state.reset_counter = 0
if "prev_country" not in st.session_state:
    st.session_state.prev_country = selected_country

# Bump reset counter when country changes so sliders pick up new defaults
if st.session_state.prev_country != selected_country:
    st.session_state.prev_country = selected_country
    st.session_state.reset_counter += 1
    st.rerun()

st.sidebar.subheader("Simulation Period")
start_year = st.sidebar.number_input("Start year", min_value=1950, max_value=2100,
                                     value=country["baseline_year"])
num_years = st.sidebar.slider("Number of years to simulate", min_value=10, max_value=200, value=50)

st.sidebar.subheader("Demographic Parameters")

# Use a key suffix tied to reset_counter so sliders reset to defaults
rc = st.session_state.reset_counter

tfr = st.sidebar.slider("Total Fertility Rate (TFR)", min_value=0.5, max_value=8.0,
                         value=defaults["tfr"], step=0.01, key=f"tfr_{rc}")
le_male = st.sidebar.slider("Life Expectancy (Male)", min_value=40.0, max_value=100.0,
                             value=defaults["le_male"], step=0.1, key=f"le_m_{rc}")
le_female = st.sidebar.slider("Life Expectancy (Female)", min_value=40.0, max_value=100.0,
                               value=defaults["le_female"], step=0.1, key=f"le_f_{rc}")
mortality_mult = st.sidebar.slider("Mortality Multiplier", min_value=0.5, max_value=2.0,
                                   value=defaults["mortality_mult"], step=0.05, key=f"mort_{rc}")

# Net migration - scale range based on country population
max_mig = max(abs(country["net_migration"]) * 5, 100000)
net_migration = st.sidebar.slider("Net Migration (per year)", min_value=-int(max_mig),
                                  max_value=int(max_mig),
                                  value=country["net_migration"],
                                  step=1000, key=f"mig_{rc}")

st.sidebar.subheader("Migration Distribution")
concentrated = st.sidebar.toggle("Concentrate migration in ages 25-34",
                                 value=False, key=f"conc_{rc}")

st.sidebar.subheader("Historical Data")
show_historical = st.sidebar.toggle("Show historical data", value=True, key=f"hist_{rc}")
hist_years = 0
if show_historical:
    hist_years = st.sidebar.slider("Historical years to display", min_value=0, max_value=75,
                                   value=25, key=f"hist_yrs_{rc}")

# Buttons
col_run, col_reset = st.sidebar.columns(2)
run_clicked = col_run.button("Run Simulation", type="primary", use_container_width=True)
if col_reset.button("Reset to Defaults", use_container_width=True):
    st.session_state.reset_counter += 1
    st.rerun()

# ── Load baseline data ─────────────────────────────────────────────────

male_pop_init, female_pop_init = load_age_distribution(country["code"], country["baseline_year"])

# ── Population Pyramid Link ────────────────────────────────────────────

pyramid_url = get_pyramid_url(country["code"], start_year)

# ── Run simulation ─────────────────────────────────────────────────────

if run_clicked or "sim_result" not in st.session_state or st.session_state.get("last_country") != selected_country:
    params = SimulationParams(
        tfr=tfr,
        life_expectancy_male=le_male,
        life_expectancy_female=le_female,
        net_migration=net_migration,
        sex_ratio_at_birth=country["sex_ratio_at_birth"],
        mortality_multiplier=mortality_mult,
        concentrated_migration=concentrated,
        start_year=start_year,
        num_years=num_years,
    )
    result = run_simulation(male_pop_init, female_pop_init, params)
    st.session_state.sim_result = result
    st.session_state.last_country = selected_country

result = st.session_state.sim_result

# ── Load historical data ──────────────────────────────────────────────

hist_data = {"years": [], "total": [], "children": [], "working": [], "elderly": []}
if show_historical and hist_years > 0:
    available = get_available_years(country["code"])
    hist_start = start_year - hist_years
    hist_range = [y for y in available if hist_start <= y < start_year]
    for y in hist_range:
        m, f = load_age_distribution(country["code"], y)
        hist_data["years"].append(y)
        hist_data["total"].append(int(m.sum() + f.sum()))
        hist_data["children"].append(int(m[:18].sum() + f[:18].sum()))
        hist_data["working"].append(int(m[18:65].sum() + f[18:65].sum()))
        hist_data["elderly"].append(int(m[65:].sum() + f[65:].sum()))

# ── Display ────────────────────────────────────────────────────────────

# Country info
st.markdown(f"**{selected_country}** ({country['code']}) | "
            f"Baseline pop: {country['population']:,.0f} | "
            f"[Population Pyramid (external)]({pyramid_url})")
if country.get("notes"):
    st.caption(country["notes"])

# ── Population over time ───────────────────────────────────────────────

st.subheader("Population Over Time")

children_series = [int((yr.male_pop[:18].sum() + yr.female_pop[:18].sum())) for yr in result.years]
working_series = [int((yr.male_pop[18:65].sum() + yr.female_pop[18:65].sum())) for yr in result.years]
elderly_series = [int((yr.male_pop[65:].sum() + yr.female_pop[65:].sum())) for yr in result.years]

has_hist = len(hist_data["years"]) > 0

fig_pop = go.Figure()

# Historical traces (solid lines)
if has_hist:
    # Connect historical to simulation by overlapping the first sim point
    h_years = hist_data["years"] + [result.year_list[0]]
    fig_pop.add_trace(go.Scatter(
        x=h_years, y=hist_data["total"] + [result.population_series[0]],
        mode="lines", name="Total (Historical)",
        line=dict(width=3, color="#2c3e50"),
        legendgroup="total",
    ))
    fig_pop.add_trace(go.Scatter(
        x=h_years, y=hist_data["working"] + [working_series[0]],
        mode="lines", name="Working Age (Historical)",
        line=dict(width=2, color="#3498db"),
        legendgroup="working",
    ))
    fig_pop.add_trace(go.Scatter(
        x=h_years, y=hist_data["elderly"] + [elderly_series[0]],
        mode="lines", name="Elderly (Historical)",
        line=dict(width=2, color="#e74c3c"),
        legendgroup="elderly",
    ))
    fig_pop.add_trace(go.Scatter(
        x=h_years, y=hist_data["children"] + [children_series[0]],
        mode="lines", name="Children (Historical)",
        line=dict(width=2, color="#2ecc71"),
        legendgroup="children",
    ))

# Simulation traces (dashed if historical shown, solid otherwise)
dash_style = "dash" if has_hist else None
fig_pop.add_trace(go.Scatter(
    x=result.year_list, y=result.population_series,
    mode="lines", name="Total Population" + (" (Simulated)" if has_hist else ""),
    line=dict(width=3, color="#2c3e50", dash=dash_style),
    legendgroup="total", showlegend=not has_hist,
))
fig_pop.add_trace(go.Scatter(
    x=result.year_list, y=working_series,
    mode="lines", name="Working Age (18-64)" + (" (Simulated)" if has_hist else ""),
    line=dict(width=2, color="#3498db", dash=dash_style),
    legendgroup="working", showlegend=not has_hist,
))
fig_pop.add_trace(go.Scatter(
    x=result.year_list, y=elderly_series,
    mode="lines", name="Elderly (65+)" + (" (Simulated)" if has_hist else ""),
    line=dict(width=2, color="#e74c3c", dash=dash_style),
    legendgroup="elderly", showlegend=not has_hist,
))
fig_pop.add_trace(go.Scatter(
    x=result.year_list, y=children_series,
    mode="lines", name="Children (0-17)" + (" (Simulated)" if has_hist else ""),
    line=dict(width=2, color="#2ecc71", dash=dash_style),
    legendgroup="children", showlegend=not has_hist,
))

# Add vertical line at simulation start if historical is shown
if has_hist:
    fig_pop.add_vline(x=start_year, line_dash="dot", line_color="gray",
                      annotation_text="Simulation Start", annotation_position="top")

fig_pop.update_layout(
    xaxis_title="Year",
    yaxis_title="Population",
    height=450,
    margin=dict(t=30, b=40),
)
st.plotly_chart(fig_pop, use_container_width=True)

# ── Births / Deaths / Migration ────────────────────────────────────────

st.subheader("Demographic Components (per year)")

# Skip baseline year (index 0) which has 0s
years_comp = result.year_list[1:]
births = result.births_series[1:]
deaths = result.deaths_series[1:]
migration = result.migration_series[1:]

fig_comp = go.Figure()
fig_comp.add_trace(go.Scatter(x=years_comp, y=births, name="Births",
                              line=dict(color="#2ecc71", width=2)))
fig_comp.add_trace(go.Scatter(x=years_comp, y=deaths, name="Deaths",
                              line=dict(color="#e74c3c", width=2)))
fig_comp.add_trace(go.Scatter(x=years_comp, y=migration, name="Net Migration",
                              line=dict(color="#3498db", width=2, dash="dash")))
fig_comp.update_layout(
    xaxis_title="Year",
    yaxis_title="People",
    height=400,
    margin=dict(t=30, b=40),
)
st.plotly_chart(fig_comp, use_container_width=True)

# ── Population Pyramids ────────────────────────────────────────────────

st.subheader("Population Pyramids: Baseline vs Final Year")

baseline = result.years[0]
final = result.years[-1]


def make_pyramid(male_pop, female_pop, title):
    """Create a horizontal bar chart population pyramid."""
    ages = np.arange(101)

    # Aggregate into 5-year bins for readability
    bin_labels = []
    male_bins = []
    female_bins = []
    for start in range(0, 101, 5):
        end = min(start + 4, 100)
        label = f"{start}-{end}" if end < 100 else "100+"
        bin_labels.append(label)
        male_bins.append(male_pop[start:end + 1].sum())
        female_bins.append(female_pop[start:end + 1].sum())

    male_bins = np.array(male_bins)
    female_bins = np.array(female_bins)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=bin_labels,
        x=-male_bins,
        orientation="h",
        name="Male",
        marker_color="#3498db",
        hovertemplate="%{y}: %{customdata:,.0f}<extra>Male</extra>",
        customdata=male_bins,
    ))
    fig.add_trace(go.Bar(
        y=bin_labels,
        x=female_bins,
        orientation="h",
        name="Female",
        marker_color="#e74c3c",
        hovertemplate="%{y}: %{x:,.0f}<extra>Female</extra>",
    ))

    max_val = max(male_bins.max(), female_bins.max()) * 1.1
    fig.update_layout(
        title=title,
        barmode="overlay",
        bargap=0.05,
        xaxis=dict(
            range=[-max_val, max_val],
            tickvals=np.linspace(-max_val, max_val, 7),
            ticktext=[f"{abs(v):,.0f}" for v in np.linspace(-max_val, max_val, 7)],
            title="Population",
        ),
        yaxis=dict(title="Age Group"),
        height=500,
        margin=dict(t=40, b=40),
    )
    return fig


col1, col2 = st.columns(2)
with col1:
    fig_base = make_pyramid(baseline.male_pop, baseline.female_pop,
                            f"Baseline ({baseline.year})")
    st.plotly_chart(fig_base, use_container_width=True)

with col2:
    fig_final = make_pyramid(final.male_pop, final.female_pop,
                             f"Final ({final.year})")
    st.plotly_chart(fig_final, use_container_width=True)

# ── Summary Statistics ─────────────────────────────────────────────────

st.subheader("Summary")

start_pop = result.years[0].total_population
end_pop = result.years[-1].total_population
change = end_pop - start_pop
pct_change = (change / start_pop * 100) if start_pop > 0 else 0

col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Start Population", f"{start_pop:,.0f}")
col_b.metric("End Population", f"{end_pop:,.0f}")
col_c.metric("Change", f"{change:+,.0f}", delta=f"{pct_change:+.1f}%")
col_d.metric("Simulation Years", f"{num_years}")

# ── Export ─────────────────────────────────────────────────────────────

st.subheader("Export Results")

# Build historical rows if available
hist_rows = []
if has_hist:
    for i, y in enumerate(hist_data["years"]):
        m, f = load_age_distribution(country["code"], y)
        row = {
            "Year": y,
            "Source": "Historical",
            "Total Population": hist_data["total"][i],
            "Children (0-17)": hist_data["children"][i],
            "Working Age (18-64)": hist_data["working"][i],
            "Elderly (65+)": hist_data["elderly"][i],
            "Births": "",
            "Deaths": "",
            "Net Migration": "",
        }
        for bin_start in range(0, 101, 5):
            bin_end = min(bin_start + 4, 100)
            label = f"{bin_start}-{bin_end}" if bin_end < 100 else "100+"
            row[f"Male {label}"] = int(m[bin_start:bin_end + 1].sum())
            row[f"Female {label}"] = int(f[bin_start:bin_end + 1].sum())
        hist_rows.append(row)

# Build simulation rows
sim_rows = []
for i, yr in enumerate(result.years):
    row = {
        "Year": result.year_list[i],
        "Source": "Simulated",
        "Total Population": result.population_series[i],
        "Children (0-17)": children_series[i],
        "Working Age (18-64)": working_series[i],
        "Elderly (65+)": elderly_series[i],
        "Births": result.births_series[i],
        "Deaths": result.deaths_series[i],
        "Net Migration": result.migration_series[i],
    }
    for bin_start in range(0, 101, 5):
        bin_end = min(bin_start + 4, 100)
        label = f"{bin_start}-{bin_end}" if bin_end < 100 else "100+"
        row[f"Male {label}"] = int(yr.male_pop[bin_start:bin_end + 1].sum())
        row[f"Female {label}"] = int(yr.female_pop[bin_start:bin_end + 1].sum())
    sim_rows.append(row)

export_data = pd.DataFrame(hist_rows + sim_rows)

csv_data = export_data.to_csv(index=False)

file_start = hist_data["years"][0] if has_hist else start_year
st.download_button(
    label="Download CSV",
    data=csv_data,
    file_name=f"simulation_{country['code']}_{file_start}_{start_year + num_years}.csv",
    mime="text/csv",
)
