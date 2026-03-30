"""
Berlin Döner BI — Daten einlesen & verknüpfen
===============================================
Liest alle Quellen ein und erzeugt zwei GeoDataFrames (Wie DataFrames nur mit der Ergänzung von Geodaten):

  gdf_plr   — LOR-Planungsräume + Medianeinkommen
  gdf_plz   — PLZ-Polygone + Altersstruktur (aggregiert über Bezirke)

Outputs:
  lor_mit_einkommen.gpkg   — LOR + Medianeinkommen (GeoPackage)
  plz_mit_alter.gpkg       — PLZ + Altersstruktur  (GeoPackage)
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path

# ── Pfade ────────────────────────────────────────────────────────────
PLR_SHP       = "LOR_Data/LOR_2023-01-01_PLR_EPSG_25833_nur_ID.shp" #PLR steht hier für Planungsraum
PLZ_GEOJSON   = "plz.geojson"
EINKOMMEN_XLS = "Medianeinkommen_Karte_31-12-2023.xlsx"
ALTER_XLS     = "Einwohnerregisterstatistik Berlin.xlsx"

OUT_LOR       = "lor_mit_einkommen.gpkg"
OUT_PLZ       = "plz_mit_alter.gpkg"

TARGET_CRS    = "EPSG:25833" # definiert das Koordinatenreferenzsystem in welches die Geodaten transformiert werden sollen 
# ─────────────────────────────────────────────────────────────────────


# ════════════════════════════════════════════════════════════════════
# BLOCK 1 — LOR-Shapefile einlesen
# ════════════════════════════════════════════════════════════════════
print("=========================")
print("BLOCK 1 — LOR-Shapefile")
print("=========================")

lor = gpd.read_file(PLR_SHP) # Laden der Planugnsraum-Shapefile-Datei
lor["PLR_ID"] = lor["PLR_ID"].astype(str).str.strip() # Bereinigung der ID Spalte 

print(f"  Spalten:  {list(lor.columns)}") # welche Spalten gibt es?
print(f"  CRS:      {lor.crs}") # welches Koordinatenreferenzsystem wird genutzt
print(f"  Zeilen:   {len(lor)}") # das sollte übereinstimmen mit der Anzahl der Zeilen in der Tabelle mit dem Medianeinkommen!
print(lor.head(3))


# ════════════════════════════════════════════════════════════════════
# BLOCK 2 — Medianeinkommen einlesen & mit LOR mergen
# ════════════════════════════════════════════════════════════════════
print("=========================")
print("BLOCK 2 — Medianeinkommen")
print("=========================")


# Einlesen der Excel mit dem Medianeinkommen pro PLR
df_eink = pd.read_excel(
    EINKOMMEN_XLS,
    sheet_name="Medianeinkommen PLR",
    skiprows=6,
    dtype={"RAUMID": str} # Raum ID wird direkt als String eingelesen, damit führende Nullen nicht verloren gehen
)

# Nur relevante Spalten behalten (PLR)
df_eink = df_eink[["RAUMID", "Planungsraumname", "Medianeinkommen in EUR"]].copy()
df_eink = df_eink.rename(columns={
    "RAUMID":                "raumid",
    "Planungsraumname":      "plr_name",
    "Medianeinkommen in EUR": "medianeinkommen_eur"
})

#### Hier Testsweise auch das gleiche mit den Bezirken machen  -> da ist aber noch irgendein Fehler drin aufgrund der gleichen Variablennamen 

# # Einlesen der Excel mit dem Medianeinkommen pro Bezirk
# df_eink = pd.read_excel(
#     EINKOMMEN_XLS,
#     sheet_name="Medianeinkommen Bezirke",
#     skiprows=6,
# )

# # Nur relevante Spalten behalten (Bezirk)
# df_eink = df_eink[["Bezirksnummer", "Bezirk", "Medianeinkommen in EUR"]].copy()
# df_eink = df_eink.rename(columns={
#     "Bezirksnummer":          "bezirksnr",
#     "Bezirk":                 "bezirkname",
#     "Medianeinkommen in EUR": "medianeinkommen_eur_bezirk"
# })

# Leerzeilen und Nicht-numerische Werte entfernen
df_eink = df_eink.dropna(subset=["raumid", "medianeinkommen_eur"]) # Alle Zeilen entfernene, in denen Entweder die RaumID oder das Medianeinkommen fehlt 
df_eink["medianeinkommen_eur"] = pd.to_numeric(
    df_eink["medianeinkommen_eur"], errors="coerce" # Einträge werden in Zahlen umgewandelt und falsche Formate zu NaN
)
df_eink = df_eink.dropna(subset=["medianeinkommen_eur"]) # Entfernt alle Zeilen, in denen der Median keine Nummer ist
df_eink["raumid"] = df_eink["raumid"].str.strip() # Leerzeichen zu Beginn und Ende des Strings entfernen

print(f"  Zeilen nach Bereinigung: {len(df_eink)}")
print(df_eink.head(3))

# # Merge: LOR-Geometrien + Medianeinkommen
# gdf_plr = lor.merge(
#     df_eink,
#     left_on="PLR_ID",
#     right_on="raumid",
#     how="left"
# )

# n_missing = gdf_plr["medianeinkommen_eur"].isna().sum()
# print(f"\n  LOR gesamt:              {len(gdf_plr)}")
# print(f"  Ohne Einkommensdaten:    {n_missing}")
# print(gdf_plr[["PLR_ID", "plr_name", "medianeinkommen_eur"]].head(5))

# # Export
# gdf_plr.to_file(OUT_LOR, driver="GPKG")
# print(f"\n  Gespeichert: {OUT_LOR}")


# # ════════════════════════════════════════════════════════════════════
# # BLOCK 3 — PLZ-GeoJSON einlesen
# # ════════════════════════════════════════════════════════════════════
# print("\n" + "=" * 60)
# print("BLOCK 3 — PLZ GeoJSON")
# print("=" * 60)

# gdf_plz_geo = gpd.read_file(PLZ_GEOJSON)

# # PLZ-Spaltenname normieren
# plz_col = [c for c in gdf_plz_geo.columns if c.lower() == "plz"][0]
# gdf_plz_geo = gdf_plz_geo.rename(columns={plz_col: "plz"})
# gdf_plz_geo["plz"] = gdf_plz_geo["plz"].astype(str).str.strip()
# gdf_plz_geo = gdf_plz_geo.to_crs(TARGET_CRS)

# print(f"  Spalten:  {list(gdf_plz_geo.columns)}")
# print(f"  CRS:      {gdf_plz_geo.crs}")
# print(f"  Zeilen:   {len(gdf_plz_geo)}")
# print(gdf_plz_geo.head(3))


# # ════════════════════════════════════════════════════════════════════
# # BLOCK 4 — Altersstruktur aus T14 einlesen
# # ════════════════════════════════════════════════════════════════════
# print("\n" + "=" * 60)
# print("BLOCK 4 — Altersstruktur T14")
# print("=" * 60)

# # Tabellenstruktur laut Screenshot:
# #   Zeile 1-4: Titel + Leerzeilen
# #   Zeile 5:   Spaltenheader (Postleitzahl, Bezirk, Insgesamt, ...)
# #   Zeile 6+:  Daten
# df_alter_raw = pd.read_excel(
#     ALTER_XLS,
#     sheet_name="T14",
#     skiprows=4,          # Zeilen 1-4 überspringen → Zeile 5 wird Header
#     dtype={"Postleitzahl": str}
# )

# print(f"  Rohe Spalten: {list(df_alter_raw.columns)}")
# print(df_alter_raw.head(5))

# # ── Spalten umbenennen ──────────────────────────────────────────────
# # Passe die Spaltennamen an, falls deine Excel leicht anders beschriftet ist.
# # Die Reihenfolge aus dem Screenshot: PLZ, Bezirk, Insgesamt,
# # unter 6, 6-15, 15-18, 18-27, 27-45, 45-55, 55-65, 65+, darunter weiblich

# rename_map = {}
# cols = list(df_alter_raw.columns)

# # Automatisch die ersten 12 inhaltlichen Spalten mappen
# expected = [
#     "plz", "bezirk", "einwohner_gesamt",
#     "alter_u6", "alter_6_15", "alter_15_18",
#     "alter_18_27", "alter_27_45", "alter_45_55",
#     "alter_55_65", "alter_65plus", "davon_weiblich"
# ]
# for i, new_name in enumerate(expected):
#     if i < len(cols):
#         rename_map[cols[i]] = new_name

# df_alter = df_alter_raw.rename(columns=rename_map)

# # Nur die bekannten Spalten behalten
# df_alter = df_alter[[c for c in expected if c in df_alter.columns]].copy()

# # PLZ bereinigen: Nur 5-stellige Zahlen behalten, Leerzeilen raus
# df_alter = df_alter.dropna(subset=["plz"])
# df_alter["plz"] = df_alter["plz"].astype(str).str.strip().str.zfill(5)
# df_alter = df_alter[df_alter["plz"].str.match(r"^\d{5}$")]

# # Numerische Spalten konvertieren (Bindestriche = fehlende Werte)
# num_cols = [c for c in expected if c not in ("plz", "bezirk")]
# for col in num_cols:
#     if col in df_alter.columns:
#         df_alter[col] = pd.to_numeric(df_alter[col], errors="coerce")

# print(f"\n  Zeilen nach Bereinigung: {len(df_alter)}")
# print(f"  Eindeutige PLZ:          {df_alter['plz'].nunique()}")
# print(f"  PLZ×Bezirk-Kombinationen (Sonderfall): "
#       f"{(df_alter.groupby('plz')['bezirk'].nunique() > 1).sum()} PLZ in mehreren Bezirken")
# print(df_alter.head(6))

# # ── Aggregation: PLZ×Bezirk → PLZ (Summe über Bezirke) ────────────
# # Da manche PLZ in mehreren Bezirken vorkommen, aggregieren wir auf PLZ-Ebene.
# # Das ist die sauberste Methode für den Spatial Join mit den Dönerladen-Punkten,
# # weil der Punkt selbst dann per Spatial Join dem richtigen Bezirk zugeordnet wird.
# df_alter_agg = (
#     df_alter
#     .groupby("plz")[num_cols]
#     .sum(min_count=1)           # NaN bleibt NaN wenn ALLE Werte fehlen
#     .reset_index()
# )

# # Nützliche Kombispalten berechnen
# if all(c in df_alter_agg.columns for c in ["alter_18_27", "alter_27_45"]):
#     df_alter_agg["alter_18_45"] = (
#         df_alter_agg["alter_18_27"].fillna(0) +
#         df_alter_agg["alter_27_45"].fillna(0)
#     )

# if "einwohner_gesamt" in df_alter_agg.columns:
#     df_alter_agg["anteil_18_45_pct"] = (
#         df_alter_agg.get("alter_18_45", 0) /
#         df_alter_agg["einwohner_gesamt"].replace(0, float("nan"))
#         * 100
#     ).round(1)

# print(f"\n  Aggregiert auf PLZ-Ebene: {len(df_alter_agg)} Zeilen")
# print(df_alter_agg.head(5))


# # ════════════════════════════════════════════════════════════════════
# # BLOCK 5 — PLZ-Geo + Altersstruktur mergen
# # ════════════════════════════════════════════════════════════════════
# print("\n" + "=" * 60)
# print("BLOCK 5 — PLZ-Geo + Altersstruktur mergen")
# print("=" * 60)

# gdf_plz = gdf_plz_geo.merge(
#     df_alter_agg,
#     on="plz",
#     how="left"
# )

# n_missing_alter = gdf_plz["einwohner_gesamt"].isna().sum()
# print(f"  PLZ gesamt:              {len(gdf_plz)}")
# print(f"  Ohne Altersdaten:        {n_missing_alter}")

# # PLZ, die in Geo aber nicht in T14 auftauchen — nützlich zu wissen
# plz_nur_geo = set(gdf_plz_geo["plz"]) - set(df_alter_agg["plz"])
# plz_nur_t14 = set(df_alter_agg["plz"]) - set(gdf_plz_geo["plz"])
# if plz_nur_geo:
#     print(f"  PLZ nur in GeoJSON (kein T14-Eintrag): {sorted(plz_nur_geo)}")
# if plz_nur_t14:
#     print(f"  PLZ nur in T14 (keine Geometrie):      {sorted(plz_nur_t14)}")

# print(gdf_plz[["plz", "einwohner_gesamt", "alter_18_45",
#                "anteil_18_45_pct"]].head(8))

# # Export
# gdf_plz.to_file(OUT_PLZ, driver="GPKG")
# print(f"\n  Gespeichert: {OUT_PLZ}")


# # ════════════════════════════════════════════════════════════════════
# # ABSCHLUSS
# # ════════════════════════════════════════════════════════════════════
# print("\n" + "=" * 60)
# print("FERTIG — beide GeoPackages bereit für Spatial Join")
# print("=" * 60)
# print(f"""
#   {OUT_LOR}
#     {len(gdf_plr)} LOR-Planungsräume mit Medianeinkommen
#     Schlüssel: PLR_ID

#   {OUT_PLZ}
#     {len(gdf_plz)} PLZ-Gebiete mit Altersstruktur
#     Schlüssel: plz

#   Nächster Schritt: Dönerladen-Punkte per Spatial Join
#   mit beiden Layern verknüpfen (Analysis.py).
# """)