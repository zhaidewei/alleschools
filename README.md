## AlleSchools (alleschools.nl) — Dutch school comparison

This repository consumes **DUO Open Onderwijsdata** and, optionally, **CBS postcode‑level WOZ data** to:

- For **secondary schools (VO)**: compute each school’s coordinates on a 2D plane of **“VWO pass share × science pass share”**.
- For **primary schools (PO)**: compute each school’s coordinates on **“VWO‑advice share × average WOZ (postcode PC4)”**.
- Serve an interactive, shareable visualization locally or as a static site (Vercel‑ready).  

Brand: **AlleSchools** ([alleschools.nl](https://alleschools.nl)).

---

## 1. Data pipeline overview

High‑level pipeline for both VO (secondary) and PO (primary):

| Step | Input | Script / action | Output |
|------|-------|-----------------|--------|
| Fetch VO exams | DUO CSV URL | `python -m alleschools.cli fetch --vo` | `raw_data/duo_examen_raw_all.csv` (+ `raw_data/duo_vestigingen_vo.csv`) |
| Compute VO coordinates | Raw VO inputs under `raw_data/` | `python -m alleschools.cli vo` (or `etl --vo`) | `generated/schools_xy_coords.csv`, `generated/excluded_schools.json`, JSON/GeoJSON/long‑table exports, `run_report_vo.json` |
| Fetch PO school advice | DUO CSV URLs per school year | `python -m alleschools.cli fetch --po` | `raw_data/duo_schooladviezen_YYYY_YYYY.csv` (per year) |
| Fetch WOZ by postcode | CBS PC4 Geopackage zips | `python -m alleschools.cli fetch --cbs-woz` (or `fetch --all`) | `raw_data/cbs_woz_per_postcode_year.csv` (pc4, year, woz_waarde) |
| Compute PO coordinates | Raw PO + WOZ inputs under `raw_data/` | `python -m alleschools.cli po` (or `etl --po`) | `generated/schools_xy_coords_po.csv`, `generated/excluded_schools_po.json`, JSON/GeoJSON/long‑table exports, `run_report_po.json` |
| Serve / build front‑end | Outputs under `generated/` (+ `view_xy.html`) | `python3 view_xy_server.py` or `python3 view_xy_server.py --static` | Local HTTP server on `http://localhost:8082` or static `public/index.html` |

You can use VO only, PO only, or both; the front‑end can toggle between the two layers.

---

## 2. VO (secondary schools): from DUO exams CSV to `schools_xy_coords.csv`

### 2.1 Fetch DUO exam data (VO)

- **Source**: DUO Open Onderwijsdata →  
  “Voortgezet onderwijs” → “Examens vmbo, havo en vwo” →  
  **Examenkandidaten en geslaagden** (CSV 2019–2024).  
- **Recommended**: use the unified CLI to download VO inputs into `raw_data/`:

```bash
python -m alleschools.cli fetch --vo
```

This writes (by default):

- `raw_data/duo_examen_raw_all.csv` – raw exams dataset for all secondary schools;  
- `raw_data/duo_vestigingen_vo.csv` – VO campuses with BRIN / postcode mapping.

These raw files are consumed by both:

- the legacy script `calc_xy_coords.py`, and  
- the refactored VO pipeline via `python -m alleschools.cli vo` / `python -m alleschools.cli etl --vo`.

---

### 2.2 Compute VO coordinates

- **Script**: `calc_xy_coords.py`
- **Input**:
  - Primary: `duo_examen_raw_all.csv` (the full DUO exams CSV).
  - Fallback: `duo_examen_raw.csv` (a small sample; e.g. only a few schools).
  - Optional: `duo_vestigingen_vo.csv` (school address + postcode by BRIN / VESTIGINGSCODE).
- **Output**:
  - `schools_xy_coords.csv` – for each BRIN (secondary school campus):
    - `BRIN`
    - `vestigingsnaam`
    - `gemeente`
    - `postcode`
    - `type` – `HAVO/VWO` or `VMBO`
    - `X_linear`, `Y_linear` – linear coordinates (axes are linear only; log scale has been removed)
    - `candidates_total` – total exam candidates over 5 years (all types), used for dot size.
  - `excluded_schools.json` – HAVO/VWO schools excluded because they have too few candidates (see below).

#### VO postcode source

The exams CSV (`duo_examen_raw_all.csv`) does **not** contain postcodes.  
`calc_xy_coords.py` (and the refactored VO pipeline) read DUO’s **Alle vestigingen VO** CSV  
([direct CSV](https://duo.nl/open_onderwijsdata/images/02.-alle-vestigingen-vo.csv)) into `duo_vestigingen_vo.csv`:

- It maps `VESTIGINGSCODE` to `POSTCODE`.
- For each BRIN in the exams CSV, it looks up the postcode via `VESTIGINGSCODE`.
- If `duo_vestigingen_vo.csv` is missing, you can (re)generate it together with the exams CSV via:

```bash
python -m alleschools.cli fetch --vo
```

#### VO coordinate definitions

- **X (horizontal)** – **VWO pass share**, 0–100%:
  - \( X = \frac{\text{VWO passed}}{\text{total exam candidates (all tracks: HAVO+VWO+VMBO+… )}} \times 100 \)
  - Uses **passed** counts (geslaagden), not candidates, so pure‑VWO schools stand out.
- **Y (vertical)** – **science pass share**, 0–100%:
  - For HAVO/VWO:
    - Science = profiles **N&T**, **N&G**, and **N&T/N&G** (bèta profiles).
    - \( Y = \frac{\text{science passed}}{\text{total exam candidates (all tracks)}} \times 100 \)
  - For VMBO‑only schools:
    - X is fixed at **0**.
    - Y is **techniek share within VMBO** (candidates in techniek / all VMBO candidates).
- **Time weighting** (2019–2020 → 2023–2024):
  - 5 school years are included, with weights:
    - `WEIGHTS = [0.2, 0.4, 0.6, 0.8, 1.0]`
  - More recent years count more.
- **Minimum HAVO/VWO sample**:
  - `MIN_HAVO_VWO_TOTAL = 20`.
  - If the 5‑year total HAVO+VWO exam candidates for a school is **< 20**, it:
    - is **not** written to `schools_xy_coords.csv`;
    - goes into `excluded_schools.json` instead (to avoid extreme, tiny‑sample points like 100/100).
Run:

```bash
python3 calc_xy_coords.py
```

---

## 3. PO (primary schools): from DUO school advice + CBS WOZ to `schools_xy_coords_po.csv`

The primary‑school (PO) layer combines **DUO school advice (schooladviezen)** with **CBS WOZ by postcode**.

### 3.1 Fetch DUO schooladviezen (PO)

- **Source**: DUO Open Onderwijsdata →  
  “Primair onderwijs” → “Aantal leerlingen” → **Schooladviezen**  
  ([overview page](https://duo.nl/open_onderwijsdata/primair-onderwijs/aantal-leerlingen/schooladviezen.jsp)).
- **Recommended**: use the unified CLI to download all required school years into `raw_data/`:

```bash
python -m alleschools.cli fetch --po
```

This downloads multiple school years and saves them as:

- `raw_data/duo_schooladviezen_2019_2020.csv`
- …
- up to `raw_data/duo_schooladviezen_2024_2025.csv`

Each CSV contains, per BRIN campus, the counts of pupils receiving each type of advice (`VWO`, `HAVO_VWO`, `HAVO`, `VMBO_*`, `VSO`, `PRO`, etc.), along with postcode and municipality.

### 3.2 Fetch CBS WOZ by postcode (PC4)

- **Source**: CBS “Gegevens per postcode (PC4)” –  
  [overview page (Dutch)](https://www.cbs.nl/nl-nl/dossier/nederland-regionaal/geografische-data/gegevens-per-postcode)
- **Recommended**: use the unified CLI (which internally uses `alleschools.fetch_cbs_woz`) to download and preprocess WOZ data into `raw_data/`:

```bash
python -m alleschools.cli fetch --cbs-woz
# or fetch everything (VO + PO + CBS) in one go:
python -m alleschools.cli fetch --all
```

This will:

- Download the relevant CBS PC4 zip files for multiple years, e.g. `2025-cbs_pc4_2024_v1.zip`, `2025-cbs_pc4_2023_v2.zip`, etc.
- Extract the Geopackage (.gpkg) and read the table containing:
  - `postcode`
  - `gemiddelde_woz_waarde_woning`
- Filter out CBS “missing / not yet published” codes and negative WOZ values.
- Write a simplified CSV:
  - `raw_data/cbs_woz_per_postcode_year.csv` with columns: `pc4`, `year`, `woz_waarde` (in **thousands of euros**).

> Note: At the time of writing, CBS publishes WOZ per postcode for a limited set of years  
> (e.g. 2021–2023, with 2024 in progress). The script is designed to be re‑run as new years appear.

### 3.3 Compute PO coordinates

- **Script**: `calc_xy_coords_po.py`
- **Input**:
  - `duo_schooladviezen_YYYY_YYYY.csv` for 2019–2025 school years.
  - `cbs_woz_per_postcode_year.csv` (pc4‑level WOZ per year).
- **Output**:
  - `schools_xy_coords_po.csv` – for each primary‑school BRIN:
    - `BRIN`
    - `vestigingsnaam`
    - `gemeente`
    - `postcode`
    - `type` – `Bo` or `Sbo` (special primary); anything else is normalized to `Bo`.
    - `X_linear` – weighted average VWO‑equivalent advice share (%).
    - `Y_linear` – weighted average WOZ (thousand euros).
    - `pupils_total` – total advised pupils across years.
  - `excluded_schools_po.json` – PO schools excluded due to too few pupils.

#### PO coordinate definitions

For each school and each school year, `calc_xy_coords_po.py`:

- Parses DUO advice counts (per BRIN) including:
  - `VWO`, `HAVO_VWO`, `HAVO`, `VMBO_*`, `VSO`, `PRO`, `ADVIES_NIET_MOGELIJK`, etc.
- Computes:
  - `total` = total number of pupils with any advice that year.
  - `vwo_equiv` = `VWO + 0.5 × HAVO_VWO + 0.1 × HAVO`.
- For each BRIN:
  - Sums advice counts across years with weights:
    - `WEIGHTS = [0.2, 0.4, 0.6, 0.8, 1.0, 1.2]` (latest years weighted more).
  - **X (horizontal)** – VWO‑equivalent advice share, 0–100%:
    - \( X_{\text{year}} = 100 \times \frac{\text{vwo\_equiv}}{\text{total}} \)
    - `X_linear` = weighted average of `X_year`.
  - **Y (vertical)** – average WOZ value for the school’s postcode (PC4), unit = **thousand euros**:
    - For each year, finds `woz_waarde` for the given `pc4` and reference year.
    - Years with missing WOZ (e.g. future years not yet published) are simply skipped.
    - `Y_linear` = weighted average of available WOZ values.

#### Minimum pupils and exclusions (PO)

- `MIN_PUPILS_TOTAL = 10`.
- If a school has **fewer than 10 total advised pupils** across all years:
  - It is excluded from `schools_xy_coords_po.csv`.
  - It is recorded in `excluded_schools_po.json` instead.

Run:

```bash
python3 calc_xy_coords_po.py
```

---

## 4. Serving: local visualization and static site

### 4.1 Local HTTP server

- **Script**: `view_xy_server.py`
  - Loads VO data:
    - `schools_xy_coords.csv`
    - `excluded_schools.json`
  - Optionally loads PO data (if present):
    - `schools_xy_coords_po.csv`
    - `excluded_schools_po.json`
  - Injects both datasets into `view_xy.html` (as JS variables).
  - Starts an HTTP server on port `8082` and opens the browser.

**Run:**

```bash
python3 view_xy_server.py
# Then open http://localhost:8082/view_xy.html (the script also tries to open it automatically)
```

### 4.2 Front‑end features (`view_xy.html` + `view_xy_logic.js`)

- **Layers**:
  - Toggle between **Secondary (VO)** and **Primary (PO)** in the top‑left switch.
- **Axes** (linear only; log scale has been removed):
  - VO:
    - X = VWO pass share (%), 0–100.
    - Y = science pass share (%), 0–100.
  - PO:
    - X = VWO‑advice share (%), 0–100.
    - Y = average WOZ per PC4 (thousand euros).
- **Dot size**:
  - VO: proportional to `candidates_total` (5‑year sum of exam candidates).
  - PO: proportional to `pupils_total` (total pupils with advice).
- **School search**:
  - Free‑text search box; multiple terms separated by commas, e.g.:
    - `mae,zand,nov,maar`
  - Each term is **case‑insensitive** and partially matched against:
    - school name,
    - acronym of the name (e.g. “HWC” from “Hermann Wesselink College”),
    - BRIN code,
    - municipality name,
    - postcode (spaces removed).
  - Matching dots are highlighted; non‑matching dots are faded.
  - **Only when the search box is non‑empty**, matching schools show labels above their dots:
    - labels include highlighted substrings that matched the search terms.
- **Municipality filter**:
  - A text filter `gemeente` (comma‑separated) to limit which municipalities appear:
    - Empty = all municipalities.
    - Example: `AMSTELVEEN,AMSTERDAM`.
  - A checkbox list under the chart lets you individually (de)select municipalities:
    - Only the **selected** municipalities remain visible in the chart.
- **Legend behavior (aligned with current code)**:
  - By default, each municipality has a distinct color, deterministically derived from its name.
  - When there is **no search**, all legend entries show in full color.
  - When there **is a search**, legend entries for municipalities **with at least one matching school** stay in full color; others are **dimmed** to visually de‑emphasize them.
- **URL parameters & sharing**:
  - When opening the page, you can pass:
    - `q` – initial school search query.
    - `gemeente` – initial municipality filter.
  - Example:
    - `?q=mae,zand&gemeente=gra,zoe,voor`
  - The page will:
    - pre‑fill the search box,
    - pre‑fill the municipality filter,
    - select the matching municipalities in the checkbox list.
  - Share buttons:
    - Copy a link that preserves `q` and `gemeente`.
    - Share to X / Facebook with the same parameters embedded.
- **Additional UI features**:
  - Language toggle: **EN / 中文 / NL**.
  - Theme toggle: light / dark (remembered in `localStorage`).
  - “Download picture”: exports the chart area as a PNG via `html2canvas`.

### 4.3 Static build for Vercel (and other static hosts)

To generate a static HTML file for deployment:

```bash
python3 view_xy_server.py --static
# Writes public/index.html
```

The generated `public/index.html` is a fully static page containing the injected VO and PO data.

#### Deploying to Vercel

This repository is preconfigured for **Vercel static hosting**:

1. Push the repo to GitHub/GitLab/Bitbucket, or import it into Vercel.
2. Vercel reads `vercel.json` in the project root:
   - **buildCommand**: `bash rerun_data.sh && python3 view_xy_server.py --static`
   - **outputDirectory**: `public`
3. `rerun_data.sh` uses the unified CLI (`python -m alleschools.cli full --all` + schema validation) to:
   - fetch / refresh raw inputs into `raw_data/`,
   - recompute all VO/PO outputs into `generated/` (linear coordinates only; if you have older outputs that included log-scale fields, a full rerun is recommended so meta/points match the current schema).
   - and only then build the static HTML.

For local preview of the static build:

```bash
python3 view_xy_server.py --static
python3 -m http.server 8082 --directory public
```

---

## 5. BRIN and data sources (VO)

### 5.1 What is BRIN?

- **BRIN**: a unique identifier for schools and campuses in the Dutch education system.  
  It stands for **BasisRegister Instellingen**.
- **Structure**: 4‑digit institution code + 2‑digit campus code = 6 characters total, e.g. `02QZ00`.
  DUO, AlleCijfers, and others use BRIN to refer to individual campuses.

### 5.2 Where to get full BRIN / school lists

- **Basisgegevens instellingen** (organisations registry):  
  [Info page](https://duo.nl/open_onderwijsdata/onderwijs-algemeen/basisgegevens/basisgegevens-instellingen.jsp)  
  (zip contains BRIN‑level organisation data).
- **Alle vestigingen VO** (all secondary campuses):  
  [Info page](https://duo.nl/open_onderwijsdata/voortgezet-onderwijs/adressen/vestigingen.jsp)  
  [CSV](https://duo.nl/open_onderwijsdata/images/02.-alle-vestigingen-vo.csv) with:
  - BRIN / VESTIGINGSCODE,
  - school name,
  - address,
  - municipality (`GEMEENTENAAM`),
  - etc.

General DUO open data entry point: <https://duo.nl/open_onderwijsdata/>

---

## 6. How the VO data source was chosen

- **Initial requirement**: for each school, per profile and per year:
  - number of exam candidates,
  - number of passes.
- **Attempt**: scrape AlleCijfers HTML:
  - The relevant “per gekozen profiel” (per chosen profile) numbers turned out to be loaded via front‑end JavaScript, not present in the static HTML.
- **Conclusion**: switch to DUO Open Onderwijsdata:
  - In DUO → Voortgezet onderwijs → Examens, the **Examenkandidaten en geslaagden** CSV provides:
    - `INSTELLINGSCODE`, `VESTIGINGSCODE` (BRIN),
    - `OPLEIDINGSNAAM` (profile name),
    - per year: exam candidates, passes, and percentages.
  - This satisfies the requirement: **school + profile + year** counts.
- **This repository**:
  - Downloads that DUO CSV as `duo_examen_raw_all.csv`.
  - `calc_xy_coords.py` aggregates by BRIN and education type, computes X/Y, and writes `schools_xy_coords.csv`.

---

## 7. “Elite index” and coordinate system (VO)

### 7.1 Possible “elite index” definitions

Conceptually, an “elite index” could combine:

| Dimension        | Meaning                         | Data source                                      |
|-----------------|---------------------------------|--------------------------------------------------|
| Academic level  | VWO vs HAVO emphasis           | VWO share = VWO / (HAVO + VWO)                  |
| Subject mix     | Science (N&T, N&G) emphasis    | Science share (N&T / N&G) from existing CSV     |
| Graduation rate | Pass rate                      | DUO CSV also contains `GESLAAGDEN` and rates    |

Example formulations:

- **Option 1**: single‑dimension: “elite index = VWO share” or “elite index = science share”.
- **Option 2 (recommended)**:  
  **elite index = 0.6 × VWO share + 0.4 × science share**.
- **Option 3**: add pass rate:
  - e.g. `0.4 × VWO + 0.3 × science + 0.3 × pass_rate` (after normalization).

This project chooses not to collapse the dimensions into one number. Instead:

- **X = VWO pass share**
- **Y = science pass share**

so you can visually interpret “academic level × science focus” directly in 2D. Internally, it is consistent with Option 2 in spirit.

### 7.2 Current VO implementation

- **X axis**:
  - VWO pass share (%) = VWO passed / all exam candidates (HAVO + VWO + VMBO …).
- **Y axis**:
  - Science pass share (%) = science passed / all exam candidates.
  - Science = N&T + N&G + N&T/N&G profiles for HAVO/VWO.
  - For VMBO‑only schools:
    - X = 0,
    - Y = techniek share within VMBO.
- **Composite profiles**:
  - `N&T/N&G`, `E&M/C&M`, etc. are grouped according to DUO’s `OPLEIDINGSNAAM`.
  - `<5` values in DUO CSV (privacy) are treated as `2` via `parse_int()`.

---

## 8. Finding secondary schools by municipality

If you want a list of all VO campuses in a municipality:

- **Web**:  
  `https://allecijfers.nl/middelbare-scholen-overzicht/{gemeente-slug}/`  
  (e.g. `amstelveen`, `amsterdam`).
- **Batch / programmatic (via DUO)**:

```bash
curl -sL "https://duo.nl/open_onderwijsdata/images/02.-alle-vestigingen-vo.csv" -o vestigingen_vo.csv
awk -F';' 'NR==1 {print; next} toupper($11)==toupper("Amstelveen") {print}' vestigingen_vo.csv > amstelveen_vo.csv
```

In this CSV, column 11 (`$11`) is `GEMEENTENAAM`.

---

## 9. Data anomalies and sanity checks (VO)

### 9.1 IJburg College (100, 100)

- **Observation**: In an earlier run, BRIN `28DH01` (IJburg College) appeared at `X_linear = 100`, `Y_linear = 100`.
- **Reason**:
  - In `duo_examen_raw_all.csv`, this campus had only one line: “VWO – N&G”, with extremely small counts (`<5`).
  - This results in:
    - VWO share = 100%,
    - Science share = 100%.
  - This is **not a calculation bug**; it reflects an extremely small sample.
- **Handling**:
  - `calc_xy_coords.py` uses `MIN_HAVO_VWO_TOTAL = 20`:
    - HAVO/VWO total exam candidates (5‑year sum) below 20 → school is excluded from the main CSV and written to `excluded_schools.json`.

### 9.2 HAVO/VWO schools with X = 100

- **Observation**: Some HAVO/VWO schools have `X_linear = 100`.
- **Conclusion**:
  - This is **not** a data‑processing error.
  - It means the DUO data for that campus has **only VWO passes and no HAVO passes**.
  - Typical examples:
    - St. Ignatiusgymnasium
    - Het Amsterdams Lyceum
    - Stedelijk Gymnasium Haarlem

### 9.3 Points at X = 0, Y ≈ 100% (mostly VMBO)

- **Observation**: Many points cluster around **X = 0, Y = 100%**.
- **Explanation**:
  - These are almost always **VMBO‑only schools**:
    - **X = 0**: VMBO schools do not contribute to VWO pass share.
    - **Y ≈ 100%**: Y = techniek share within VMBO.
      - 100% indicates a campus that only offers techniek (technical / vocational) pathways.
  - Typical schools:
    - Maritieme Academie Harlingen (maritime),
    - Mediacollege Amsterdam (media),
    - Grafisch Lyceum Rotterdam (design),
    - STC (shipping / logistics),
    - SiNTLUCAS (design),
    - etc.

---

## 10. Development and testing

- **Back‑end / pipeline unit tests**:
  - Core parsing and classification logic in `calc_xy_coords.py` and `calc_xy_coords_po.py` is covered by **pytest** tests.
- **Front‑end logic unit tests**:
  - Pure chart logic (search term parsing, matching, name highlighting, municipality colors, filters) lives in `view_xy_logic.js`.
  - Tested with Node’s built‑in test runner:
    - `node --test tests/view_xy_logic.test.js`
  - `view_xy.html` imports the same logic via:
    - `<script src="view_xy_logic.js"></script>`
- **Dependencies**:
  - Install development dependencies:

```bash
pip install -r requirements-dev.txt
# or create a venv first:
# python3 -m venv .venv
# .venv/bin/pip install -r requirements-dev.txt
```

- **Run tests**:

```bash
./run_tests.sh        # runs pytest + Node tests
# or:
pytest tests/ -v
node --test tests/view_xy_logic.test.js
```

- **pre‑commit**:
  - Configured to run tests before each commit.
  - First‑time setup:

```bash
pip install -r requirements-dev.txt
pre-commit install
```

After that, each `git commit` triggers `pytest tests/ -v` (and the Node tests via `run_tests.sh`), and only completes if they all pass.

---

## 11. File overview

Cleaned‑up file list (grouped by purpose):

### 11.1 VO data pipeline (secondary schools)

| File | Description |
|------|-------------|
| `raw_data/duo_examen_raw_all.csv` | Raw DUO exams data (all secondary schools), typically generated via `python -m alleschools.cli fetch --vo`. |
| `raw_data/duo_examen_raw.csv` | Optional small sample (e.g. for quick experiments); used only if `duo_examen_raw_all.csv` is missing. |
| `raw_data/duo_vestigingen_vo.csv` | DUO VO campuses with BRIN, names, addresses, and postcodes; used to add postcodes to the VO coordinates (also fetched by `python -m alleschools.cli fetch --vo`). |
| `calc_xy_coords.py` | Legacy script to compute VO coordinates (VWO pass share × science share) from DUO exams CSV → `schools_xy_coords.csv`, `excluded_schools.json`. The refactored pipeline instead runs via `python -m alleschools.cli vo` / `etl --vo` and writes into `generated/`. |
| `schools_xy_coords.csv` | VO school coordinates (legacy script): BRIN, name, municipality, postcode, type, `X_linear`, `Y_linear`, `candidates_total`. Refactored pipeline outputs linear only. |
| `excluded_schools.json` | VO schools excluded from the chart due to too few HAVO/VWO candidates (5‑year total below threshold). |

### 11.2 PO + WOZ pipeline (primary schools)

| File | Description |
|------|-------------|
| `raw_data/duo_schooladviezen_YYYY_YYYY.csv` | Per‑year DUO school advice CSVs (input to both `calc_xy_coords_po.py` and the refactored PO pipeline). Usually generated via `python -m alleschools.cli fetch --po`. |
| `raw_data/cbs_woz_per_postcode_year.csv` | Simplified CBS WOZ dataset: `pc4`, `year`, `woz_waarde` (thousand euros), used to compute PO Y coordinates. Generated via `python -m alleschools.cli fetch --cbs-woz` (or `fetch --all`). |
| `pc4_2023_v2.xlsx`, `pc4_2024_v1.xlsx` | Intermediate CBS PC4 files (may be historical artefacts; kept for reference). |
| `calc_xy_coords_po.py` | Legacy script to compute PO coordinates (VWO‑advice share × WOZ) from DUO school advice + CBS WOZ → `schools_xy_coords_po.csv`, `excluded_schools_po.json`. The refactored pipeline instead runs via `python -m alleschools.cli po` / `etl --po` and writes into `generated/`. |
| `schools_xy_coords_po.csv` | PO school coordinates (legacy script): BRIN, name, municipality, postcode, type, `X_linear`, `Y_linear`, `pupils_total`. Refactored pipeline outputs linear only. |
| `excluded_schools_po.json` | PO schools excluded due to too few pupils (total advice count below threshold). |

### 11.3 Front‑end and serving

| File | Description |
|------|-------------|
| `view_xy.html` | Front‑end HTML template (chart canvas + controls + multi‑language copy). Data is injected by `view_xy_server.py`. |
| `view_xy_logic.js` | Pure front‑end logic for the scatter plot (search/filter/coloring), shared between the browser and Node tests. |
| `view_xy_server.py` | Local HTTP server and static builder. Reads VO/PO CSV/JSON, injects them into `view_xy.html`, serves or writes `public/index.html`. |
| `vercel.json` | Vercel configuration (build command and output directory for static deployment). |

### 11.4 Tests and tooling

| File | Description |
|------|-------------|
| `tests/test_calc_xy_coords.py` | Pytest unit tests for VO coordinate calculation helpers. |
| `tests/test_calc_xy_coords_po.py` | Pytest unit tests for PO coordinate calculation helpers (e.g. WOZ lookup). |
| `tests/view_xy_logic.test.js` | Node tests for `view_xy_logic.js` (search, matching, colors, filters, labels). |
| `run_tests.sh` | Helper script to run all tests (pytest + Node) – used by pre‑commit. |
| `.pre-commit-config.yaml` | pre‑commit configuration (runs tests before committing). |
| `requirements-dev.txt` | Development dependencies (pytest, pre‑commit, etc.). |

### 11.5 Refactor and advanced pipeline (alleschools)

The `refactor/` directory and the internal `alleschools` Python package describe and implement a more modular data pipeline and schema‑driven exports. The simple script‑based flow documented above will remain available; the refactored pipeline adds a richer set of outputs and a proper CLI.

Key components:

| File / module | Description |
|---------------|-------------|
| `refactor/README.md` | High‑level refactor goals: separating data pipeline vs. visualization, and defining a stable data contract between them. |
| `refactor/SCHEMA.md` | Canonical schema for **points data** (JSON) and **meta + i18n** (JSON). Front‑ends and BI tools should depend on this, not on raw DUO/CBS files. |
| `refactor/UI_DESIGN.md` | UI/UX design for a schema‑driven front‑end that consumes the `SCHEMA.md` data/meta contract. |
| `refactor/P0_P1_P2_plan.md` | Implementation roadmap for the refactor (P0/P1/P2 stages: modularization, richer exports, schema validator, privacy rules, etc.). |
| `config.yaml` | Central configuration for inputs, outputs, thresholds, weights, and quality rules per layer (`vo` / `po`). |
| `alleschools/*` | Internal package for loaders, indicators, exporters, pipelines, CLI entrypoints, and schema validator; see `refactor/P0_P1_P2_plan.md` for the current status. |
| `schools_xy_coords_geo.json` | Example GeoJSON export for VO coordinates, produced by the refactored exporters for map tooling (geometry may be null or populated depending on PC4→lat/lon lookup). |
| `run_report_po.json` / `run_report_vo.json` | Structured **run reports** emitted by the refactored pipelines. Each report records the effective config snapshot, input files, generated outputs (CSV/JSON/GeoJSON/long table), basic row/column counts, data‑quality summary, and the schema version used (matching the meta JSON). |
| `data_quality_report_po.json` / `data_quality_report_vo.json` | Optional **data quality reports** produced by the quality module, referenced from the run reports. They typically contain checks such as duplicate BRINs, missing postcodes, very small sample sizes, and other anomalies. |

For up‑to‑date details on the refactor (JSON points/meta outputs, GeoJSON/long‑table exporters, CLI entrypoints, schema validator), refer to the documents under `refactor/` and the `alleschools` modules. As those pieces evolve, `refactor/SCHEMA.md` remains the single source of truth for the data contract.

### 11.6 Miscellaneous

| File | Description |
|------|-------------|
| `LICENSE` | Project license (MIT). |
| `README.md` | This document. |

