#!/usr/bin/env python3
"""Parse DUO examenkandidaten CSV and update JSON files with 'Aantal leerlingen per gekozen profiel'."""
import csv
import json
import os

# BRIN (VESTIGINGSCODE in DUO) -> our school slug and name
SCHOOLS = {
    "02QZ00": ("keizer-karel-college", "Keizer Karel College"),
    "02TE00": ("hermann-wesselink-college", "Hermann Wesselink College"),
    "19XY00": ("amstelveen-college", "Amstelveen College"),
    "00WD00": ("futuris", "Futuris"),
}

# Column index in DUO CSV (0-based). Header: INSTELLINGSCODE, VESTIGINGSCODE, INSTELLINGSNAAM, GEMEENTENAAM, ONDERWIJSTYPE, INSPECTIECODE, OPLEIDINGSNAAM, then per year MAN,GESLAAG MAN, SLAAG%, VROUW, GESLAAG VROUW, SLAAG%, TOTAAL, GESLAAG TOT, SLAAG%
# So TOTAAL for each year: 2019-20=14, 2020-21=23, 2021-22=32, 2022-23=41, 2023-24=50
COL_VESTIGING = 1
COL_OPLEIDINGSNAAM = 6
COL_TOTAAL_2019_20 = 14
COL_TOTAAL_2020_21 = 23
COL_TOTAAL_2021_22 = 32
COL_TOTAAL_2022_23 = 41
COL_TOTAAL_2023_24 = 50

YEARS = [
    ("2019-2020", COL_TOTAAL_2019_20),
    ("2020-2021", COL_TOTAAL_2020_21),
    ("2021-2022", COL_TOTAAL_2021_22),
    ("2022-2023", COL_TOTAAL_2022_23),
    ("2023-2024", COL_TOTAAL_2023_24),
]


def parse_value(v):
    """Convert DUO value: '<5' -> None or int."""
    v = (v or "").strip().strip('"')
    if not v or v == "<5":
        return None
    try:
        return int(v)
    except ValueError:
        return None


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    raw_path = os.path.join(base, "duo_examen_raw.csv")
    if not os.path.exists(raw_path):
        print("Run: curl -sL 'https://duo.nl/open_onderwijsdata/images/examenkandidaten-en-geslaagden-2019-2024.csv' | grep -E '\"02QZ\"|\"02TE\"|\"19XY\"|\"00WD\"' > duo_examen_raw.csv")
        return 1

    # Parse CSV (semicolon, quoted)
    rows = []
    with open(raw_path, "r", encoding="utf-8") as f:
        for line in f:
            row = list(csv.reader([line], delimiter=";", quotechar='"'))[0]
            if len(row) <= COL_TOTAAL_2023_24:
                continue
            vest = (row[COL_VESTIGING] or "").strip().strip('"')
            if vest not in SCHOOLS:
                continue
            opleiding = (row[COL_OPLEIDINGSNAAM] or "").strip().strip('"')
            rows.append((vest, opleiding, row))

    # Build per school: year -> profile -> count
    data = {brin: {} for brin in SCHOOLS}
    for vest, opleiding, row in rows:
        for year_name, col in YEARS:
            if year_name not in data[vest]:
                data[vest][year_name] = {}
            val = parse_value(row[col])
            if val is not None:
                data[vest][year_name][opleiding] = val
            # keep <5 as null or omit; we can add a note. Optionally store as "<5"
            elif row[col].strip().strip('"') == "<5":
                data[vest][year_name][opleiding] = "<5"  # DUO privacy

    # Update each school JSON
    for brin, (slug, name) in SCHOOLS.items():
        json_path = os.path.join(base, f"{slug}_profielen.json")
        if not os.path.exists(json_path):
            continue
        with open(json_path, "r", encoding="utf-8") as f:
            js = json.load(f)
        js["aantal_leerlingen_per_gekozen_profiel"] = {
            "eenheid": "leerlingen (examenkandidaten)",
            "bron_duo": "DUO Open Onderwijsdata - Examenkandidaten en geslaagden 2019-2024",
            "examenjaren": list(YEARS[i][0] for i in range(len(YEARS))),
            "profielen_per_examenjaar": data.get(brin, {}),
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(js, f, indent=2, ensure_ascii=False)
        print(f"Updated {json_path}")

    return 0


if __name__ == "__main__":
    exit(main())
