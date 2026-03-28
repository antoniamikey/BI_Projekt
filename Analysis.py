import pandas as pd
import geopandas as gpd


PLR_SHAPEFILE = "LOR_Data/LOR_2023-01-01_PLR_EPSG_25833_nur_ID.shp"
PLZ_GEOJSON = "plz.geojson"
INCOME_XLSX = "Medianeinkommen_Karte_31-12-2023.xlsx"
POPULATION_XLSX = "Einwohnerregisterstatistik Berlin.xlsx"


def load_plr_with_income() -> gpd.GeoDataFrame:
    """Lädt PLR-Geometrien und hängt das Medianeinkommen an."""
    plr = gpd.read_file(PLR_SHAPEFILE)
    plr["PLR_ID"] = plr["PLR_ID"].astype(str)

    income = pd.read_excel(
        INCOME_XLSX,
        sheet_name="Medianeinkommen PLR",
        skiprows=6,
        dtype={"RAUMID": str},
    )[
        [
            "RAUMID",
            "Planungsraumname",
            "Medianeinkommen in EUR",
            "SvB in Vollzeit",
            "Platzierung des Medians (Quintil)",
            "SvB im unteren Entgeltbreich",
            "SvB in Vollzeit im unteren Entgeltbereich in %",
        ]
    ].rename(
        columns={
            "RAUMID": "PLR_ID",
            "Planungsraumname": "plr_name",
            "Medianeinkommen in EUR": "medianeinkommen_eur",
            "SvB in Vollzeit": "svb_vollzeit",
            "Platzierung des Medians (Quintil)": "median_quintil",
            "SvB im unteren Entgeltbreich": "svb_unteres_entgelt",
            "SvB in Vollzeit im unteren Entgeltbereich in %": "svb_unteres_entgelt_pct",
        }
    )

    return plr.merge(income, on="PLR_ID", how="left")


def load_population_by_plz() -> pd.DataFrame:
    """
    Liest T14 ein und aggregiert auf eindeutige PLZ.

    Das Tabellenblatt T14 enthält Kombinationen aus PLZ und Bezirk.
    Da die GeoJSON-Datei nur eine Geometrie pro PLZ enthält, werden
    Mehrfachzeilen derselben PLZ hier auf PLZ-Ebene aufsummiert.
    """
    age_columns = [
        "einwohner_gesamt",
        "alter_unter_6",
        "alter_6_bis_15",
        "alter_15_bis_18",
        "alter_18_bis_27",
        "alter_27_bis_45",
        "alter_45_bis_55",
        "alter_55_bis_65",
        "alter_65_plus",
        "weiblich",
    ]

    population = pd.read_excel(
        POPULATION_XLSX,
        sheet_name="T14",
        skiprows=5,
        header=None,
        names=["plz", "bezirk", *age_columns],
    ).dropna(subset=["plz", "bezirk"])

    population["plz"] = (
        population["plz"]
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(5)
    )
    population["bezirk"] = population["bezirk"].astype(str).str.strip()

    for column in age_columns:
        population[column] = pd.to_numeric(population[column], errors="coerce")

    population_by_plz = (
        population.groupby("plz", as_index=False)[age_columns]
        .sum(min_count=1)
        .sort_values("plz")
    )

    population_by_plz["anzahl_bezirke_in_t14"] = (
        population.groupby("plz")["bezirk"].nunique().reindex(population_by_plz["plz"]).values
    )

    return population_by_plz


def load_plz_with_population() -> gpd.GeoDataFrame:
    """Lädt PLZ-Geometrien und hängt die aggregierten Altersdaten an."""
    plz = gpd.read_file(PLZ_GEOJSON)
    plz["plz"] = plz["plz"].astype(str).str.strip()

    population_by_plz = load_population_by_plz()
    return plz.merge(population_by_plz, on="plz", how="left")


def attach_shop_context(shops: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    Hängt für Punkte mit lon/lat sowohl PLZ-Altersdaten als auch PLR-Einkommen an.

    Erwartete Spalten in shops:
    - lon
    - lat
    Optional:
    - name
    """
    required_columns = {"lon", "lat"}
    missing = required_columns.difference(shops.columns)
    if missing:
        raise ValueError(f"Fehlende Spalten für Shop-Koordinaten: {sorted(missing)}")

    shops_gdf = gpd.GeoDataFrame(
        shops.copy(),
        geometry=gpd.points_from_xy(shops["lon"], shops["lat"]),
        crs="EPSG:4326",
    )

    plr = load_plr_with_income()
    plz = load_plz_with_population()

    shops_projected = shops_gdf.to_crs(plr.crs)
    plz_projected = plz.to_crs(plr.crs)

    shops_with_plz = gpd.sjoin(
        shops_projected,
        plz_projected,
        how="left",
        predicate="within",
    ).drop(columns=["index_right"])

    shops_with_plr = gpd.sjoin(
        shops_with_plz,
        plr,
        how="left",
        predicate="within",
        lsuffix="_plz",
        rsuffix="_plr",
    ).drop(columns=["index_right"])

    return shops_with_plr


if __name__ == "__main__":
    plr_with_income = load_plr_with_income()
    plz_with_population = load_plz_with_population()

    print("PLR mit Einkommen")
    print(plr_with_income[["PLR_ID", "plr_name", "medianeinkommen_eur"]].head())
    print()

    print("PLZ mit Altersdaten")
    print(
        plz_with_population[
            ["plz", "einwohner_gesamt", "alter_unter_6", "alter_65_plus", "anzahl_bezirke_in_t14"]
        ].head()
    )
