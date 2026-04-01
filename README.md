# DönerBI - Berlin Döner Standortanalyse

Interaktives Business-Intelligence-Dashboard zur datengestützten Standortbewertung für Döner-Restaurants in Berlin. Entwickelt im Rahmen eines BI-Projekts an der HWR Berlin (Sommersemester 2026).

---

## Projektüberblick

Das System analysiert alle **542 Planungsräume (PLR)** Berlins anhand von fünf gewichteten Scores und gibt eine datenbasierte Standortempfehlung. Grundlage sind kombinierte Daten aus der Google Places API, amtlicher Statistik (Senatsverwaltung, Amt für Statistik Berlin-Brandenburg) und IHK-Gewerbedaten.

**Kernfrage:** Welcher Berliner Planungsraum bietet die besten Rahmenbedingungen für ein neues Döner-Restaurant?

---

## Dashboard starten

```bash
pip install -r requirements.txt
streamlit run dashboard_v2.py
```

> Voraussetzung: Die Data-Pipeline muss vorher einmal vollständig durchgelaufen sein (s. u.), sodass `Data_Pipeline/berlin_masterdata.db` existiert. Die Datenbank liegt produktionsbereit im GitHub.

---

## Projektstruktur

```
BI_Projekt/
├── dashboard_v2.py                  # Streamlit-Dashboard (Hauptdatei)
├── Logo.png                         # Branding
├── requirements.txt
└── Data_Pipeline/
    ├── nb_01_kebab-stores_google-places-api.ipynb   # Döner-Daten via Google Places API
    ├── nb_02_infrastruktur_aggregate-api.ipynb      # Infrastrukturdaten via Google Places API
    ├── nb_03_merge-masterdata.ipynb                 # Zusammenführung aller Daten
    ├── nb_04_analyse.ipynb                          # EDA, Regression, NLP, k-Means
    ├── _file_name_config.txt                        # Pfad-Konfiguration für nb_03
    ├── berlin_masterdata.db                         # Generierte SQLite-Datenbank (nach Pipeline)
    ├── berlin_masterdata.csv                        # Generiertes CSV (nach Pipeline)
    ├── lor_planungsraeume_2021.geojson              # LOR-Geometrien (Amt f. Statistik BBB)
    ├── lor_bevoelkerungs-daten_2024.csv             # Bevölkerung nach PLR (Stand 31.12.2024)
    ├── lor_Medianeinkommen_31-12-2023.xlsx          # Medianeinkommen nach PLR (Amt f. Statistik BBB)
    ├── lor_monitoring_soziale-stadtentwicklung_2023.xlsx  # MSS-Index 2023 (Senatsverwaltung)
    ├── lor_IHKBerlin_Gewerbedaten_cleaned.csv       # Gastro-Gewerbedaten (IHK Berlin)
    ├── dataset_berlin_doener_clean.csv              # Döner-Shops (aus nb_01)
    ├── dataset_infrastruktur.json                   # Roh-Infrastrukturdaten (aus nb_02)
    └── lor_infrastruktur.csv                        # Aggregierte Infrastruktur nach PLR (aus nb_02)
```

---

## Data-Pipeline

Die Notebooks müssen in dieser Reihenfolge ausgeführt werden:

| Notebook | Inhalt | Output |
|---|---|---|
| `nb_01` | Döner- und Kebab-Restaurants via Google Places API abrufen und bereinigen | `dataset_berlin_doener_clean.csv` |
| `nb_02` | Infrastruktur-POIs (ÖPNV, Schulen, Unis, Büros, Nachtleben) je PLR aggregieren | `lor_infrastruktur.csv` |
| `nb_03` | Alle Rohdaten auf PLR-Ebene zusammenführen, Feature Engineering, Export | `berlin_masterdata.db`, `berlin_masterdata.csv` |
| `nb_04` | Explorative Analyse, Regressionsmodell, NLP-Auswertung, k-Means-Clustering | Analyse-Outputs, PNG-Grafiken |

> Für nb_01 und nb_02 wird ein gültiger **Google Places API Key** benötigt, der in der `.env` Datei hinterlegt werden muss.

---

## Scoring-Modell

Der **Standort-Score** ist eine gewichtete Summe aus fünf Sub-Scores (0–100), wobei einige Attribute invers in den Score reinspielen:

| # | Score | Beschreibung |
|---|---|---|
| S1 | **Nachfrage** | Einwohnerdichte, Anteil 18–35-Jährige, ÖPNV, Nachtleben, Büros, Öffnungszeiten |
| S2 | **Marktlücke** | Einwohner/Laden-Verhältnis, geringe Gastrodichte, geringe Bewertungsqualität der Konkurrenz |
| S3 | **Wettbewerb** | Invertierter Wettbewerbs-Index, geringer Fastfood-Anteil |
| S4 | **Infrastruktur** | ÖPNV, Universitäten, Schulen, Büros |
| S5 | **Sozio** | Kaufkraft (Medianeinkommen + MSS-Status) oder Gentrification-Flag |

Standardgewichtung: Nachfrage 30 % · Marktlücke 30 % · Wettbewerb 20 % · Infrastruktur 10 % · Sozio 10 %

Alle Scores werden per Min-Max-Normalisierung auf [0, 100] skaliert.

---

## Dashboard-Seiten

| Seite | Inhalt |
|---|---|
| **Berlin Übersicht** | Karte aller 1.346 Dönerläden, farbkodiert nach Ø-Bewertung, KPI-Übersicht |
| **Standort-Pitch** | Radar-Chart + Choropleth-Karte für die Top-Empfehlungen mit Standardgewichtung |
| **Scoring Lab** | Interaktive Gewichtungsslider, Top-15-Ranking, verknüpfte Karte (Klick → Highlight) |
| **Marktanalyse** | Marktlücken-Karte & Ranking, Wettbewerbsanalyse nach Bezirk, Infrastruktur-Heatmap |
| **Erfolgsprofil** | NLP-Radar (Top vs. Bottom Döner) + Regressions-Koeffizientenplot |
| **PLR-Vergleich** | Radar-Chart-Vergleich von bis zu drei Planungsräumen |
| **Konzepte & Daten** | Score-Formeln, Analysemethoden M1–M5, Datenquellen, Limitierungen |

---

## Datenquellen

| Datensatz | Quelle | Stand |
|---|---|---|
| Döner-/Kebab-Restaurants Berlin | Google Places API | 2023/2024 |
| Infrastruktur-POIs (ÖPNV, Schulen etc.) | Google Places API | 2023/2024 |
| LOR-Planungsräume Geometrie | Amt für Statistik Berlin-Brandenburg | 2021 |
| Bevölkerung nach PLR | Amt für Statistik Berlin-Brandenburg | 31.12.2024 |
| Medianeinkommen nach PLR | Amt für Statistik Berlin-Brandenburg | 31.12.2023 |
| Monitoring Soziale Stadtentwicklung (MSS) | Senatsverwaltung für Stadtentwicklung | 2023 |
| Gastro-Gewerbedaten | IHK Berlin | 2023 |

---

## Technologie-Stack

- **Python 3.10+**
- **Streamlit** — Dashboard-Framework
- **Plotly** — Interaktive Karten und Charts (Choropleth, Scatter, Radar, Bar)
- **Pandas / NumPy** — Datenverarbeitung
- **SQLite** — Lokale Datenhaltung
- **Jupyter Notebooks** — Data-Pipeline

---

## Bekannte Limitierungen

- Fastfood-Klassifikation durch Google Places ist nicht vollständig konsistent
- Bevölkerungsdaten teilweise auf Basis älterer Erhebungen
- Döner-Definition basiert auf Labels "Döner" / "Kebab" — atypische Betriebe können fehlen
- ÖPNV-Counts addieren alle `transit_station`-Typen kumulativ (S-Bahn, U-Bahn, Tram, Bus, Fähre)
- Mietkosten nicht im Score enthalten
- Gentrification-Flag ist binär (MSS-Dynamik-basiert), keine kontinuierliche Messung

---

*HWR Berlin · BI-Projekt · 2026*
