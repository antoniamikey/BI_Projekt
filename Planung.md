# Berlin Döner-Standortanalyse — Projektplan
## Ziel
Datengetriebene Standortanalyse für neue Dönerläden in Berlin.
Endprodukte: Interaktives Dashboard + 10-Minuten-Pitch-Präsentation (als Dashboard-Seite).

---

## Datenquellen

### 1. Dönerläden
- **Quelle:** Google Places Text Search API
- **Notebook:** `nb_01_kebab-stores_google-places-api.ipynb`
- **Inhalt:** 1.346 Dönerläden mit Standort, Rating, Bewertungsanzahl, Services, Öffnungszeiten, Preisniveau, Reviews
- **Output:** `dataset_berlin_doener_clean.csv` (für Merge), `dataset_berlin_doener.json` (für NLP + Öffnungszeiten-Extraktion)
- **Status:** ✅ Fertig, Daten vorhanden

### 2. LOR-Planungsräume Geodaten (seit 2021, 542 Stück)
- **Quelle:** ODIS Berlin
- **URL GeoJSON:** https://daten.odis-berlin.de/de/dataset/lor_planungsgraeume_2021/
- **Datei:** `lor_planungsraeume_2021.geojson`
- **Inhalt:** Polygone aller 542 Planungsräume mit Schlüssel + Name (EPSG:25833 / UTM Zone 33N)
- **Verwendung:** Basis-Geometrie, Point-in-Polygon für Dönerladen-Zuordnung, Choropleth-Karten
- **Status:** ✅ Fertig, Daten vorhanden

### 3. Einwohner nach Planungsraum (31.12.2024)
- **Quelle:** Amt für Statistik Berlin-Brandenburg
- **URL:** https://daten.berlin.de/datensaetze/einwohnerinnen-und-einwohner-in-berlin-in-lor-planungsraumen-am-31-12-2024
- **Datei:** `lor_bevoelkerungs-daten_2024.csv`
- **Inhalt:** Einwohner nach Altersjahren pro Planungsraum
- **Verwendung:** Einwohnerdichte, Altersstruktur (junge Bevölkerung = Döner-Zielgruppe)
- **Status:** ✅ Fertig, Daten vorhanden (541/542 PLR — 1 PLR fehlt, wird als NULL behandelt)

### 4. Einwohner mit Migrationshintergrund nach Planungsraum
<!-- ENTSCHEIDUNG: Diese Datenquelle wird NICHT verwendet — bitte hier stehen lassen als Dokumentation -->
- **Quelle:** Amt für Statistik Berlin-Brandenburg
- **Inhalt:** Einwohner mit/ohne Migrationshintergrund pro Planungsraum
- **Hinweis:** Letzter verfügbarer Stand 2020, nutzt altes LOR-System (447 PLR, nicht mappbar auf neues 542-PLR-System).
- **→ `anteil_migration` entfällt aus dem Datenmodell** — Daten zu alt und falsches LOR-System
- **Status:** ❌ Nicht verwendet

### 5. IHK Gewerbedaten Berlin
- **Quelle:** IHK Berlin Open Data
- **URL:** https://www.ihk.de/berlin/service-und-beratung/digitalisierung/open-data-5691102
- **Datei:** `lor_IHKBerlin_Gewerbedaten.csv`
- **Inhalt:** Aktive Gewerbebetriebe mit planungsraum_id, NACE-Code, business_age
- **Filter:** NACE 56* = Gastronomie (~Restaurants, Cafés, Imbisse)
- **Hinweis:** Datensatz enthält nur aktive Betriebe, keine Abmeldungen → `gastro_abmeldungen` nicht berechenbar. Proxy: `gastro_neu` = business_age ≤ 2 Jahre.
- **Status:** ✅ Fertig, Daten vorhanden

### 6. Medianeinkommen (Senatsverwaltung, 31.12.2023)
- **Datei:** `lor_Medianeinkommen_31-12-2023.xlsx` (liegt eine Ebene über Data_Pipeline/)
- **Inhalt:** Medianeinkommen in EUR pro Planungsraum
- **Hinweis:** Platzhalter-Werte `•` werden als NULL behandelt
- **Status:** ✅ Fertig, Daten vorhanden

### 7. Monitoring Soziale Stadtentwicklung (MSS 2023)
- **Datei:** `lor_monitoring_soziale-stadtentwicklung_2023.xlsx`
- **Inhalt:** Sozialstatus-Index (1–4) und Veränderungsdynamik pro PLR
- **Verwendung:** Score 5 (Sozio), Gentrification-Flag
- **Status:** ✅ Fertig, Daten vorhanden

### 8. Infrastruktur via Google Places Aggregate API
- **Quelle:** Google Places Aggregate API (areainsights.googleapis.com)
- **Methode:** Pro Planungsraum das exakte PLR-Polygon (volles Polygon, EPSG:25833 → WGS84)
- **Calls:** 542 Planungsräume × 7 Typen = 3.794 API-Calls (~$19, ~2 Stunden Laufzeit)
- **Notebook:** `nb_02_infrastruktur_aggregate-api.ipynb`
- **Output:** `lor_infrastruktur.csv` (542 Zeilen)
- **Status:** ✅ Fertig, Daten vorhanden (alle 542 PLR verarbeitet)

| Kategorie | includedTypes | Output-Spalte | Insight |
|---|---|---|---|
| ÖPNV | transit_station | transit_count | Fußgängerfrequenz |
| Bildung | university | university_count | Studenten-Zielgruppe |
| Bildung | school | school_count | Schüler-Zielgruppe |
| Nachtleben | bar, night_club | nightlife_count | Spätabend-Demand |
| Arbeit | corporate_office + government_office | office_count | Mittagsgeschäft |
| Wettbewerb | fast_food_restaurant | fastfood_count | Sättigungsgrad |

---

## Datei-Inventar

### Notebooks (Data_Pipeline/)

| Notebook | Beschreibung | Status |
|---|---|---|
| `nb_01_kebab-stores_google-places-api.ipynb` | Döner-Datensatz via Google Places Text Search API | ✅ fertig, dokumentiert |
| `nb_02_infrastruktur_aggregate-api.ipynb` | Infrastruktur via Google Places Aggregate API | ✅ fertig, dokumentiert, Daten vorhanden |
| `nb_03_merge-masterdata.ipynb` | Master-Merge aller Datenquellen → berlin_masterdata.csv + .db | ✅ fertig, ausgeführt |
| `nb_04_analyse.ipynb` | M3 NLP + M4 Regression + M5 Moran's I + M6 k-Means | ✅ fertig, ausgeführt |

### Konfiguration

| Datei | Beschreibung |
|---|---|
| `_file_name_config.txt` | Alle Eingabe-/Ausgabedateinamen für nb_03 |

### Datendateien (Data_Pipeline/)

| Datei | Inhalt | Status |
|---|---|---|
| `lor_planungsraeume_2021.geojson` | 542 PLR-Polygone (EPSG:25833) | ✅ |
| `lor_bevoelkerungs-daten_2024.csv` | Einwohner 2024 pro PLR | ✅ |
| `lor_monitoring_soziale-stadtentwicklung_2023.xlsx` | MSS 2023 (Sozialstatus + Dynamik) | ✅ |
| `lor_Medianeinkommen_31-12-2023.xlsx` | Medianeinkommen 2023 (liegt im Root-Ordner des Worktrees) | ✅ |
| `dataset_berlin_doener_clean.csv` | 1.346 Dönerläden (bereinigt) | ✅ |
| `dataset_berlin_doener.json` | 1.346 Dönerläden (vollständig, inkl. Reviews) | ✅ |
| `lor_IHKBerlin_Gewerbedaten.csv` | IHK Gewerbedaten (aktive Betriebe) | ✅ |
| `lor_infrastruktur.csv` | Infrastruktur-Counts alle 542 PLR | ✅ |
| `berlin_masterdata.csv` | Master-Datensatz (Output nb_03) | ✅ |
| `berlin_masterdata.db` | SQLite-Datenbank (Output nb_03 + nb_04) | ✅ |

### Nicht verwendete Dateien (zur Dokumentation)

| Datei | Grund für Nicht-Verwendung |
|---|---|
| `EWRMIGRA202012E_Matrix.csv` | Altes LOR-System (447 PLR, Stand 2020) — nicht mappbar |
| `Einwohnerregisterstatistik Berlin.xlsx` | Falsche Granularität (Ortsteil/PLZ-Ebene) |
| `plz.geojson`, `LOR_Data/*.shp` | Nicht benötigt — PLR-GeoJSON ist Basis |

---

## Datenmodell (Zieltabelle `planungsraeume` in berlin_masterdata.db)

Scores werden **nicht** in der Datenbank gespeichert. Sie werden live im Dashboard berechnet.

```
-- Geografie
plr_id                   TEXT PRIMARY KEY   -- 8-stelliger LOR-Schlüssel
plr_name                 TEXT               -- z.B. "Oranienplatz"
flaeche_km2              REAL
centroid_lat             REAL
centroid_lng             REAL

-- Bevölkerung (Stand 31.12.2024)
einwohner_gesamt         INTEGER
einwohner_18_35          INTEGER            -- Kernzielgruppe
einwohner_dichte         REAL               -- pro km²

-- Einkommen (Stand 31.12.2023)
medianeinkommen_eur      REAL

-- Sozialindex MSS 2023
mss_status_index         REAL               -- 1=hoch, 4=sehr niedrig
mss_dynamik_index        REAL               -- Veränderungsdynamik

-- Dönerläden (aggregiert via Point-in-Polygon)
doener_count              INTEGER
doener_avg_rating         REAL
doener_total_reviews      INTEGER
doener_best_rating        REAL
doener_pct_delivery       REAL
doener_avg_hours_per_week REAL
doener_pct_late_night     REAL
doener_pct_open_sunday    REAL
doener_avg_price_level    REAL

-- Infrastruktur (Google Places Aggregate API)
transit_count            INTEGER
university_count         INTEGER
school_count             INTEGER
nightlife_count          INTEGER
office_count             INTEGER
fastfood_count           INTEGER

-- Gewerbedaten IHK (NACE 56*)
gastro_gesamt            INTEGER
gastro_neu               INTEGER            -- business_age ≤ 2 Jahre

-- Abgeleitete Kennzahlen (berechnet in nb_03)
einwohner_pro_doener     REAL
wettbewerb_index         REAL               -- (doener+fastfood)/einwohner*1000
gastro_fluktuation       REAL               -- gastro_neu/gastro_gesamt
gentrification_flag      INTEGER            -- 1 wenn mss_status≤2 AND dynamik=positiv

-- Analyse-Ergebnisse (geschrieben durch nb_04)
lisa_cluster             TEXT               -- HH / LL / HL / LH / NS
kiez_typ                 TEXT               -- k-Means Cluster-Label
```

---

## Score-Kompositionen (live im Dashboard berechnet)

**Score 1 — Nachfrage** (Ø von 6 Min-Max-normierten Variablen)
`einwohner_dichte` + `anteil_18_35` + `transit_count` + `nightlife_count` + `office_count` + `doener_avg_hours_per_week`

**Score 2 — Marktlücke**
`einwohner_pro_doener` (pos) + `gastro_dichte` (invers)

**Score 3 — Wettbewerb** (invertiert — niedriger Wettbewerb ist gut)
`wettbewerb_index` (invers) + `fastfood_count` (invers)

**Score 4 — Infrastruktur**
`transit_count` + `university_count` + `school_count` + `office_count`

**Score 5 — Sozio** (zwei Modi, im Dashboard wählbar)
- Modus Kaufkraft: `medianeinkommen_eur` (pos) + `mss_status_index` (invers)
- Modus Kiez im Aufbruch: `gentrification_flag` (binär × 100)

**Gesamtscore** = gewichtete Summe, Standardgewichtung: Nachfrage 30% · Marktlücke 30% · Wettbewerb 20% · Infrastruktur 10% · Sozio 10%

---

## Methodik

### M3 — NLP Sentiment-Analyse (nb_04)
- Scope: Top 10% und Bottom 10% nach Rating (~134 + 134 Läden)
- Methodik: VADER (regelbasiert), nur deutsche Reviews
- Output: Radar-Chart Top vs. Bottom (4 Themes: Preis, Qualität, Service, Hygiene)
- Datei: `nlp_radar_top_vs_bottom.png`

### M4 — Logistische Regression (nb_04)
- Zielvariable: `erfolg_flag` (rating ≥ 4.3 AND userRatingCount ≥ 200)
- Features: alle PLR-Kennzahlen, Z-Score standardisiert, L2-Regularisierung
- Output: Koeffizientenplot `regression_koeffizienten.png`

### M5 — Räumliche Autokorrelation Moran's I (nb_04)
- Global + Local Moran's I auf `doener_avg_rating`
- LISA-Cluster: HH (Hot Spot), LL (Cold Spot), HL/LH (Ausreißer), NS (nicht signifikant)
- Nachbarschaft: Queen Contiguity, reine Python-Implementierung (kein libpysal)
- Ergebnis `lisa_cluster` wird in DB geschrieben

### M6 — k-Means PLR-Typisierung (nb_04)
- Features: alle 5 Score-Dimensionen + gastro_fluktuation
- Elbow-Methode zur k-Bestimmung
- Ergebnis `kiez_typ` wird in DB geschrieben

---

## Dashboard

**Technologie:** Streamlit (Python)
**Datei:** `Cedrics_WIP/dashboard.py`
**Starten:** `C:\Users\cedric\anaconda3\Scripts\streamlit.exe run dashboard.py` (aus `Cedrics_WIP/`)
**Datenbasis:** `Data_Pipeline/berlin_masterdata.db` (SQLite)
**Voraussetzung:** nb_01 → nb_02 → nb_03 → nb_04 müssen vollständig ausgeführt sein

### Seitenstruktur

| Seite | Beschreibung |
|---|---|
| 🌍 Berlin Übersicht | Scatter-Karte aller 1.346 Dönerläden, eingefärbt nach Bewertung |
| 🚀 Standort-Pitch | 10-Minuten-Präsentation: Marktkontext, Scoring-Konfiguration, Top-N Empfehlungen, Karte, Dashboard-Demo-Leitfaden, Fazit |
| 🎯 Scoring Lab | Interaktive Gewichtungs-Slider, live Choropleth-Karte, Top-Ranking |
| 📊 Marktanalyse | 4 Tabs: Marktlücken / Qualitätslücken / Wettbewerb / Räumliche Cluster (LISA) |
| 🏅 Erfolgs-Profil | NLP-Ergebnisse + Regressions-Koeffizienten |
| 🔍 PLR-Vergleich | Radar-Chart und Kennzahlen-Tabelle für bis zu 4 PLR nebeneinander |
| 📚 Konzepte & Daten | Erklärungsblatt: PLR-Grundlagen, alle 5 Scores, M3–M6, Datenquellen, Limitierungen |
| 📖 Methodik | Technische Details und Hinweise zur Datenqualität |

---

## Umsetzungsreihenfolge

### Sprint 1: Datenbasis ✅ ABGESCHLOSSEN
- [x] LOR GeoJSON, Bevölkerungsdaten, IHK-Daten, Einkommensdaten, MSS-Daten beschafft
- [x] Dönerläden via Google Places API gesammelt (1.346 Läden)
- [x] Infrastruktur via Aggregate API (volles PLR-Polygon, alle 542 PLR)
- [x] Alle drei Daten-Notebooks dokumentiert und bereinigt

### Sprint 2: Datenbank ✅ ABGESCHLOSSEN
- [x] `nb_03_merge-masterdata.ipynb` ausgeführt → `berlin_masterdata.csv` + `berlin_masterdata.db`
- [x] Validierung: Join-Vollständigkeit geprüft (541/542 PLR mit Bevölkerungsdaten)
- [x] Bekannte Probleme dokumentiert (Migrationsdaten, IHK-Fluktuation-Proxy)

### Sprint 3: Analysen ✅ ABGESCHLOSSEN
- [x] `nb_04_analyse.ipynb` ausgeführt
  - M3: NLP Sentiment → `nlp_radar_top_vs_bottom.png`
  - M4: Logistische Regression → `regression_koeffizienten.png`
  - M5: Moran's I + LISA → `lisa_cluster` in DB
  - M6: k-Means → `kiez_typ` in DB

### Sprint 4: Dashboard ✅ ABGESCHLOSSEN
- [x] `dashboard.py` erstellt und vollständig implementiert
- [x] Alle 8 Seiten implementiert (Berlin Übersicht, Pitch, Scoring Lab, Marktanalyse, Erfolgs-Profil, PLR-Vergleich, Konzepte & Daten, Methodik)
- [x] Score-Berechnung live (kein Hardcoding in DB)
- [x] Alle Plotly-Deprecation-Warnungen behoben (Plotly 6 API)

### Sprint 5: Präsentation ✅ ABGESCHLOSSEN
- [x] Standort-Pitch als Dashboard-Seite implementiert
- [x] 10-Minuten-Präsentationsstruktur mit Folie-Nummern und Zeitangaben
- [x] Berlin-weite Kennzahlen, Methodik-Folie, Top-N Empfehlungen, Dashboard-Demo-Leitfaden, Fazit

---

## Offene Fragen / Bekannte Limitierungen

- Migrationshintergrund-Daten: Nur Stand 2020, altes LOR-System (447 PLR) → `anteil_migration` entfällt
- IHK enthält keine Abmeldungen → `gastro_fluktuation` nur als Proxy (business_age ≤ 2 Jahre)
- `fastfood_restaurant`-Tag in Google Places unvollständig (Döner-Läden teils als `turkish_restaurant` gelistet)
- Reviews: Ø nur ~5 Reviews pro Laden → NLP-Ergebnisse als Tendenz verstehen
- 1 PLR fehlt in Bevölkerungsdaten (541/542) → NULL
- Mietpreise auf PLR-Ebene nicht öffentlich verfügbar — wichtiger Faktor für echte Standortentscheidungen fehlt
