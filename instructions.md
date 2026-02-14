Instruction set for Claude Code

Objective



Build a web-based population simulator that uses real country parameters and displays:



simulated population over time



births/deaths/net migration per year



a population pyramid (baseline and simulated)



a country dropdown (start with South Korea, expand to ~10 countries)



Tech choices



Python backend + simulation



Streamlit frontend (fast to iterate)



Store country parameters in a local data file (CSV/JSON) so adding countries is easy.



No paid APIs required.



Key requirements

Country selection



A dropdown with initially 10 countries (include South Korea).



Selecting a country loads:



initial population (total)



total fertility rate (TFR)



life expectancy at birth (or average lifespan proxy)



net migration (people/year)



optional: sex ratio at birth, baseline age distribution year, etc.



Population pyramid



Show baseline pyramid for the country (and year), sourced from populationpyramid.net.



Implementation approach:



Prefer embedding the pyramid image in the app using a predictable URL format (or display a link + image if available).



If direct scraping becomes brittle, fallback to “open in new tab” link + cached image per country.



Simulation model (v1)



A real “cohort” model, not just a single number:



Represent population as age cohorts (0…100+), split by sex (optional but preferred).



Annual timestep simulation for N years:



Aging: everyone moves up one age each year



Deaths: apply age-specific mortality rates (approximate from life expectancy if full mortality table isn’t available)



Births: apply births based on female cohorts of childbearing ages (e.g., 15–49) and TFR



Net migration: distribute across working ages (e.g., 20–39) by default; allow user to adjust distribution



Output:



total population by year



births/deaths/migration by year



updated age pyramid each year (at least final year; optionally animate)



UI controls



Country dropdown



Start year (baseline year shown in pyramid), end year / number of years



Adjustable sliders (override defaults):



TFR



life expectancy (or mortality scaling)



net migration per year



Buttons:



“Run Simulation”



“Reset to Country Defaults”



Charts:



population over time line chart



births/deaths/migration stacked or separate chart



baseline pyramid + final-year pyramid side-by-side



Data handling



Maintain a local countries.json (or CSV) with parameters for ~10 countries.



Baseline age distribution data:



Best: ship a local age-distribution dataset (even coarse 5-year bins) for those 10 countries.



If you don’t want to manage that manually: implement a light “data ingestion” step that fetches age distribution from a public source (only if reliable and legally usable). If you do this, make it optional and cache results locally.



Performance + caching



Sim should run in <1s for a typical run (100 years, ages 0–100, both sexes).



Cache country data loads and pyramid image URLs.



Model details (make reasonable defaults explicit)

Cohort representation



Ages 0–100 inclusive, with a 101st “100+” bucket OR cap at 100.



Two arrays: male\[age], female\[age] (ints or floats)



Births calculation (v1 approximation)



Use a fertility age distribution across 15–49 (normalized weights).



Convert TFR to annual births:



births\_per\_year = sum(female\[a] \* ASFR\[a]) for a in 15..49



where ASFR is constructed so that total births across lifetime aligns with TFR.



Split births into male/female using sex ratio at birth (default ~105 males per 100 females).



Mortality (v1 approximation)



If no mortality tables:



Use a parametric mortality curve (e.g., Gompertz-like) scaled to roughly match life expectancy.



Keep it transparent: document that it’s an approximation.



Allow “mortality multiplier” slider to tweak death rates.



Migration distribution



Default allocate net migrants to ages 20–39 proportional to existing cohort sizes (or uniform).



Optionally allow a toggle: “concentrate migration in 25–34” vs “broad working age”.



File structure (create this)



app.py (Streamlit UI)



simulator/



model.py (cohort simulation engine)



demography.py (fertility/mortality helpers)



data.py (load countries + baseline distributions + caching)



data/



countries.json



age\_distributions/ (one file per country, e.g. KOR\_2025.csv)



pyramid\_cache/ (optional cached images)



requirements.txt



Step-by-step implementation plan



Create Streamlit skeleton with country dropdown and parameter panel.



Implement countries.json loader and default parameter injection.



Implement cohort simulation engine (aging, births, deaths, migration).



Add baseline age distribution loading (from local data files).



Add charts: population over time, components, pyramids.



Add populationpyramid.net embedding/link + image display + caching.



Add tests or at least a “sanity check” module:



population changes match births-deaths+migration (within rounding)



cohorts remain non-negative



Add “export results” (CSV download) (nice-to-have).



Acceptance criteria (Claude should self-check)



App runs locally with streamlit run app.py



Selecting South Korea loads defaults and shows baseline pyramid



Running simulation produces:



a line chart of population over time



births/deaths/migration series



final pyramid different from baseline if parameters change



Adding a new country requires only updating countries.json + its baseline age distribution file (no code changes)



Initial data stub (to include)



Put 10 countries in countries.json with placeholders if necessary.



For South Korea, include reasonable defaults (and clearly mark if approximate).



For baseline age distribution:



If you don’t have it yet, generate a synthetic distribution as a temporary placeholder, but design the loader so real data files override it.



Development constraints / notes



Keep dependencies minimal.



If populationpyramid.net blocks direct image embedding, fallback gracefully to:



show a clickable link + a cached image if available.



Document all approximations in a README.



Deliverables



Complete runnable repo with above structure



README with:



setup instructions (Windows)



model assumptions



how to add a new country

