# =============================================================================
# Berlin Döner Standortanalyse — Streamlit Dashboard
# Run from Cedrics_WIP/ folder:  streamlit run dashboard.py
# =============================================================================

import math
import json
import os
import sqlite3

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page config (must be the very first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    layout="wide",
    page_title="Berlin Döner Standortanalyse",
    page_icon=None,
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500&display=swap');

    /* ── Global ── */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    .stApp {
        background-color: #F7F8FA !important;
    }

    /* ── Main content ── */
    .main .block-container {
        padding: 2rem 2.5rem 3rem !important;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        width: 210px !important;
        min-width: 210px !important;
        background: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    section[data-testid="stSidebar"] * {
        font-size: 0.85rem !important;
        font-family: 'Inter', sans-serif !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        color: #111827 !important;
        letter-spacing: -0.01em !important;
    }

    /* ── Headings ── */
    h1 { font-size: 1.5rem !important; font-weight: 500 !important;
         color: #111827 !important; letter-spacing: -0.025em !important; }
    h2 { font-size: 1.125rem !important; font-weight: 500 !important;
         color: #111827 !important; letter-spacing: -0.015em !important; }
    h3 { font-size: 0.95rem !important; font-weight: 500 !important;
         color: #374151 !important; line-height: 1.4 !important; }

    /* ── Metric components ── */
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] p,
    div[data-testid="stMetricLabel"] label,
    div[data-testid="stMetricLabel"] span {
        font-size: 0.72rem !important;
        font-weight: 500 !important;
        color: #6B7280 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        line-height: 1.4 !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 500 !important;
        color: #111827 !important;
        line-height: 1.2 !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: #4A6FA5 !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        padding: 0.45rem 1rem !important;
        transition: all 0.15s ease !important;
        box-shadow: none !important;
    }
    .stButton > button:hover {
        background: #3D5F8F !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(74, 111, 165, 0.2) !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab"] {
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        color: #6B7280 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #111827 !important;
    }

    /* ── HR dividers ── */
    hr {
        border: none !important;
        border-top: 1px solid #E2E8F0 !important;
        margin: 20px 0 !important;
    }

    /* ── Expanders ── */
    .streamlit-expanderHeader {
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        color: #374151 !important;
    }

    /* ── Captions ── */
    .stCaption, [data-testid="stCaptionContainer"] {
        font-size: 0.72rem !important;
        color: #9CA3AF !important;
    }

    /* ── Dataframes ── */
    [data-testid="stDataFrame"] {
        border-radius: 8px !important;
        border: 1px solid #E2E8F0 !important;
        overflow: hidden !important;
    }

    /* ── Info / Warning / Error boxes ── */
    [data-testid="stAlert"] {
        border-radius: 8px !important;
        font-size: 0.85rem !important;
    }

    /* ── Sliders ── */
    [data-testid="stSlider"] label {
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: #374151 !important;
    }

    /* ── Select / Radio ── */
    [data-testid="stRadio"] label,
    [data-testid="stSelectbox"] label {
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: #374151 !important;
    }

    /* ── Sidebar toggle button ── */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"] {
        background: white !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
        top: 1rem !important;
    }
    [data-testid="collapsedControl"] svg,
    [data-testid="stSidebarCollapsedControl"] svg {
        color: #374151 !important;
    }

    /* ── Main content top padding (leaves room for header bar) ── */
    .main .block-container {
        padding-top: 1rem !important;
    }

    /* ── Page header bar ── */
    .page-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 0 16px;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 24px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Paths  (dashboard.py lives in Cedrics_WIP/, Data_Pipeline/ is a sibling)
# ---------------------------------------------------------------------------
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(BASE_DIR, "Data_Pipeline")
DB_PATH     = os.path.join(DATA_DIR, "berlin_masterdata.db")
GEOJSON_PATH = os.path.join(DATA_DIR, "lor_planungsraeume_2021.geojson")
DOENER_CSV  = os.path.join(DATA_DIR, "dataset_berlin_doener_clean.csv")
NLP_IMG     = os.path.join(DATA_DIR, "nlp_radar_top_vs_bottom.png")
REG_IMG     = os.path.join(DATA_DIR, "regression_koeffizienten.png")

# ---------------------------------------------------------------------------
# Colour constants
# ---------------------------------------------------------------------------
COLOR_SUCCESS = "#34A853"
COLOR_DANGER  = "#E05252"
COLOR_NEUTRAL = "#4A6FA5"
COLOR_ACCENT  = "#4A6FA5"
MAP_SCALE_MAIN   = "Blues"
MAP_SCALE_RATING = "RdYlGn"
MAP_SCALE_INFRA  = "Blues"

# =============================================================================
# UTM Zone 33N  →  WGS 84  (exact function as specified)
# =============================================================================
def utm33n_to_wgs84(easting, northing):
    a = 6378137.0; f = 1 / 298.257223563; e2 = 2 * f - f ** 2
    k0 = 0.9996; E0 = 500000.0
    lambda0 = math.radians(15.0)
    E = easting - E0; N = northing; M = N / k0
    e_prime2 = e2 / (1 - e2)
    mu = M / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    phi1 = (
        mu
        + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu)
        + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
        + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
        + (1097 * e1 ** 4 / 512) * math.sin(8 * mu)
    )
    N1 = a / math.sqrt(1 - e2 * math.sin(phi1) ** 2)
    T1 = math.tan(phi1) ** 2
    C1 = e_prime2 * math.cos(phi1) ** 2
    R1 = a * (1 - e2) / (1 - e2 * math.sin(phi1) ** 2) ** 1.5
    D = E / (N1 * k0)
    lat = phi1 - (N1 * math.tan(phi1) / R1) * (
        D ** 2 / 2
        - (5 + 3 * T1 + 10 * C1 - 4 * C1 ** 2 - 9 * e_prime2) * D ** 4 / 24
        + (61 + 90 * T1 + 298 * C1 + 45 * T1 ** 2 - 252 * e_prime2 - 3 * C1 ** 2)
        * D ** 6 / 720
    )
    lng = lambda0 + (
        D
        - (1 + 2 * T1 + C1) * D ** 3 / 6
        + (5 - 2 * C1 + 28 * T1 - 3 * C1 ** 2 + 8 * e_prime2 + 24 * T1 ** 2)
        * D ** 5 / 120
    ) / math.cos(phi1)
    return math.degrees(lat), math.degrees(lng)

def safe_df(df):
    """Convert object columns with mixed types to string for Arrow compatibility."""
    df = df.copy()
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].astype(str).replace('nan', '')
    return df




# =============================================================================
# Data loading helpers
# =============================================================================

@st.cache_data
def load_data() -> pd.DataFrame:
    """Load main planungsraeume table from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM planungsraeume", conn)
    conn.close()

    # Ensure numeric types for columns that might come back as object
    numeric_cols = [
        "flaeche_km2", "centroid_lat", "centroid_lng",
        "einwohner_gesamt", "einwohner_18_35", "einwohner_dichte",
        "medianeinkommen_eur", "mss_status_index",
        "doener_count", "doener_avg_rating", "doener_total_reviews",
        "doener_best_rating", "doener_pct_delivery",
        "doener_avg_hours_per_week", "doener_pct_late_night",
        "doener_pct_open_sunday", "doener_avg_price_level",
        "transit_count", "university_count", "school_count",
        "nightlife_count", "office_count", "fastfood_count",
        "gastro_gesamt", "gastro_neu",
        "einwohner_pro_doener", "wettbewerb_index",
        "gastro_fluktuation", "gentrification_flag",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Derived columns
    df["gastro_dichte"] = df["gastro_gesamt"] / df["flaeche_km2"].replace(0, np.nan)
    df["anteil_18_35"]  = df["einwohner_18_35"] / df["einwohner_gesamt"].replace(0, np.nan)

    # Graceful defaults for optional columns
    for col in ["kiez_typ", "lisa_cluster"]:
        if col not in df.columns:
            df[col] = "Unbekannt"
        else:
            df[col] = df[col].fillna("Unbekannt")

    return df


@st.cache_data
def load_geojson() -> dict:
    """Load GeoJSON and reproject EPSG:25833 → WGS84 in-memory."""
    with open(GEOJSON_PATH, encoding="utf-8") as f:
        gj = json.load(f)

    for feat in gj["features"]:
        geom = feat["geometry"]
        # All features are MultiPolygon with one outer part — flatten to Polygon
        new_coords = []
        for ring in geom["coordinates"][0]:
            new_ring = []
            for c in ring:
                lat, lng = utm33n_to_wgs84(c[0], c[1])
                new_ring.append([lng, lat])  # GeoJSON is [lng, lat]
            new_coords.append(new_ring)
        feat["geometry"] = {"type": "Polygon", "coordinates": new_coords}
        feat["id"] = feat["properties"]["PLR_ID"]  # plotly needs top-level id

    return gj


@st.cache_data
def load_shops() -> pd.DataFrame:
    """Load individual Döner shops from CSV for the scatter map."""
    if not os.path.exists(DOENER_CSV):
        return pd.DataFrame()
    df = pd.read_csv(DOENER_CSV, encoding="utf-8")
    for col in ["rating", "userRatingCount", "latitude", "longitude",
                "priceRange_start_units", "priceRange_end_units"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Readable price string
    def fmt_price(row):
        s = row.get("priceRange_start_units")
        e = row.get("priceRange_end_units")
        if pd.notna(s) and pd.notna(e):
            return f"{int(s)}–{int(e)} €"
        if pd.notna(s):
            return f"ab {int(s)} €"
        return "k.A."
    df["preis"] = df.apply(fmt_price, axis=1)
    # Boolean flags as readable strings
    for flag, label in [("delivery","Lieferung"), ("dineIn","Vor Ort"), ("takeout","Mitnehmen")]:
        if flag in df.columns:
            df[flag] = df[flag].map({True: "Ja", False: "Nein", 1: "Ja", 0: "Nein"}).fillna("–")
    df = df.dropna(subset=["latitude", "longitude"])
    return df


# =============================================================================
# Score computation (exact formula as specified)
# =============================================================================

def compute_scores(
    df: pd.DataFrame,
    w_nachfrage: float,
    w_marktluecke: float,
    w_wettbewerb: float,
    w_infrastruktur: float,
    w_sozio: float,
    sozio_mode: str,
) -> pd.DataFrame:
    """Compute 5 sub-scores and a weighted standort_score for every PLR."""
    d = df.copy()

    def norm(s: pd.Series) -> pd.Series:
        mn, mx = s.min(), s.max()
        if mx == mn:
            return pd.Series(0.5, index=s.index)
        return (s - mn) / (mx - mn)

    # Ensure derived columns exist
    if "gastro_dichte" not in d.columns:
        d["gastro_dichte"] = d["gastro_gesamt"] / d["flaeche_km2"].replace(0, np.nan)
    if "anteil_18_35" not in d.columns:
        d["anteil_18_35"] = d["einwohner_18_35"] / d["einwohner_gesamt"].replace(0, np.nan)

    def fn(col: str) -> pd.Series:
        if col in d.columns:
            return d[col].fillna(d[col].median())
        return pd.Series(0, index=d.index)

    # Score 1 — Nachfrage (demand)
    s1 = (
        norm(fn("einwohner_dichte"))
        + norm(fn("anteil_18_35"))
        + norm(fn("transit_count"))
        + norm(fn("nightlife_count"))
        + norm(fn("office_count"))
        + norm(fn("doener_avg_hours_per_week"))
    ) / 6 * 100

    # Score 2 — Marktlücke (market gap)
    # Includes inverted avg rating: areas where existing Döner shops have high ratings
    # face stronger quality competition → less attractive gap
    s2 = (
        norm(fn("einwohner_pro_doener"))
        + (1 - norm(fn("gastro_dichte")))
        + (1 - norm(fn("doener_avg_rating")))   # high existing quality = tougher market
    ) / 3 * 100

    # Score 3 — Wettbewerb (competition – inversion = low competition is good)
    s3 = (1 - (norm(fn("wettbewerb_index")) + norm(fn("fastfood_count"))) / 2) * 100

    # Score 4 — Infrastruktur
    s4 = (
        norm(fn("transit_count"))
        + norm(fn("university_count"))
        + norm(fn("school_count"))
        + norm(fn("office_count"))
    ) / 4 * 100

    # Score 5 — Sozio (two modes)
    if sozio_mode == "Kaufkraft":
        s5 = (norm(fn("medianeinkommen_eur")) + (1 - norm(fn("mss_status_index")))) / 2 * 100
    else:  # Kiez im Aufbruch
        gf = (
            d["gentrification_flag"].fillna(0)
            if "gentrification_flag" in d.columns
            else pd.Series(0, index=d.index)
        )
        s5 = gf * 100

    total_w = w_nachfrage + w_marktluecke + w_wettbewerb + w_infrastruktur + w_sozio
    if total_w == 0:
        total_w = 1

    d["s_nachfrage"]     = s1.round(1)
    d["s_marktluecke"]   = s2.round(1)
    d["s_wettbewerb"]    = s3.round(1)
    d["s_infrastruktur"] = s4.round(1)
    d["s_sozio"]         = s5.round(1)
    d["standort_score"]  = (
        (
            w_nachfrage * s1
            + w_marktluecke * s2
            + w_wettbewerb * s3
            + w_infrastruktur * s4
            + w_sozio * s5
        ) / total_w
    ).round(1)

    return d


# =============================================================================
# Small helpers
# =============================================================================

def safe_fmt(val, fmt="{:.1f}", fallback="–"):
    """Format a potentially NaN value safely."""
    try:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return fallback
        return fmt.format(val)
    except Exception:
        return fallback


def choropleth(
    df: pd.DataFrame,
    geojson: dict,
    color_col: str,
    title: str = "",
    color_scale: str = MAP_SCALE_MAIN,
    height: int = 520,
    hover_data: dict | None = None,
) -> go.Figure:
    """Convenience wrapper for Plotly choropleth_map."""
    hover_data = hover_data or {}
    fig = px.choropleth_map(
        df,
        geojson=geojson,
        locations="plr_id",
        color=color_col,
        color_continuous_scale=color_scale,
        map_style="carto-positron",
        center={"lat": 52.52, "lon": 13.405},
        zoom=9,
        hover_name="plr_name",
        hover_data=hover_data,
        title=title,
        height=height,
    )
    fig.update_layout(
        margin={"r": 0, "t": 30 if title else 0, "l": 0, "b": 0},
        font={"family": "Inter, sans-serif", "size": 12, "color": "#374151"},
        paper_bgcolor="white",
        coloraxis_colorbar={
            "title": {"text": color_col, "font": {"size": 12}},
            "tickfont": {"size": 11},
            "thickness": 12,
        },
    )
    return fig


# =============================================================================
# Session-state initialisation (weights reset support)
# =============================================================================

_WEIGHT_DEFAULTS = {
    "w_nachfrage": 30,
    "w_marktluecke": 30,
    "w_wettbewerb": 20,
    "w_infrastruktur": 10,
    "w_sozio": 10,
}

def _init_session_state():
    for key, val in _WEIGHT_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_session_state()


# =============================================================================
# Sidebar navigation
# =============================================================================

st.sidebar.markdown(
    "<div style='padding:16px 0 8px; font-size:0.9rem; font-weight:500; color:#111827;"
    " letter-spacing:-0.01em;'>Döner Standortanalyse</div>"
    "<div style='font-size:0.72rem; color:#9CA3AF; padding-bottom:12px;'>Berlin · 542 Planungsräume</div>",
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "",
    [
        "Berlin Übersicht",
        "Standort-Pitch",
        "Scoring Lab",
        "Marktanalyse",
        "Erfolgs-Profil",
        "PLR-Vergleich",
        "Konzepte und Daten",
    ],
    label_visibility="collapsed",
)

st.sidebar.markdown(
    "<div style='padding-top:16px; font-size:0.7rem; color:#9CA3AF;'>Datenstand 2023 / 2024</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Guard: check DB exists before loading anything
# ---------------------------------------------------------------------------
if not os.path.exists(DB_PATH):
    st.error(
        f"Datenbank nicht gefunden: `{DB_PATH}`  \n"
        "Bitte zuerst die Data-Pipeline-Notebooks ausführen "
        "(nb_01 → nb_02 → nb_03).",
    )
    st.stop()

# ---------------------------------------------------------------------------
# Load data (cached)
# ---------------------------------------------------------------------------
df_raw   = load_data()
geojson  = load_geojson() if os.path.exists(GEOJSON_PATH) else None

if geojson is None:
    st.warning(
        f"GeoJSON nicht gefunden: `{GEOJSON_PATH}` — Karten werden deaktiviert.",
    )

# ---------------------------------------------------------------------------
# Global page header (rendered on every page)
# ---------------------------------------------------------------------------
_PAGE_LABELS = {
    "Berlin Übersicht":  "Marktüberblick",
    "Standort-Pitch":    "Standort-Empfehlung",
    "Scoring Lab":       "Scoring Lab",
    "Marktanalyse":      "Marktanalyse",
    "Erfolgs-Profil":    "Erfolgsprofil",
    "PLR-Vergleich":     "PLR-Vergleich",
    "Konzepte und Daten":"Dokumentation",
}
_page_label = _PAGE_LABELS.get(page, page)
st.markdown(
    f"""
    <div class="page-header" style="font-family:Inter,sans-serif;">
        <div>
            <div style="font-size:0.68rem; color:#9CA3AF; text-transform:uppercase;
                        letter-spacing:0.08em; margin-bottom:3px;">
                Döner Standortanalyse Berlin
            </div>
            <div style="font-size:1.3rem; font-weight:500; color:#111827;
                        letter-spacing:-0.025em; line-height:1.2;">
                {_page_label}
            </div>
        </div>
        <div style="font-size:0.72rem; color:#C0C8D4; text-align:right; line-height:1.6;">
            542 Planungsräume<br>Datenstand 2023 / 2024
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
#  PAGE 0 — Berlin Übersicht (Karte aller Döner-Läden)
# =============================================================================
if page == "Berlin Übersicht":
    st.markdown(
        "<span style='color:#6B7280; font-size:0.875rem;'>1.346 Dönerläden, farbkodiert nach Kundenbewertung.</span>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    df_shops = load_shops()

    if df_shops.empty:
        st.warning(
            f"Shops-Datei nicht gefunden: `{DOENER_CSV}`  \n"
            "Bitte nb_01 ausfuehren, um die Daten zu generieren.",
        )
    else:
        # ── KPI row ───────────────────────────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Läden gesamt",          f"{len(df_shops):,}".replace(",", "."))
        k2.metric("Ø Bewertung",           f"{df_shops['rating'].mean():.2f} / 5")
        k3.metric("Reviews gesamt",        f"{int(df_shops['userRatingCount'].sum()):,}".replace(",", "."))
        k4.metric("PLR ohne Laden",        f"{int((df_raw['doener_count'].fillna(0) == 0).sum())}")

        st.markdown("---")

        # ── Scatter map ───────────────────────────────────────────────────────
        hover_cols = {}
        for c, lbl in [
            ("shortFormattedAddress", "Adresse"),
            ("preis", "Preis"),
            ("userRatingCount", "Reviews"),
        ]:
            if c in df_shops.columns:
                hover_cols[c] = True
        # Hide lat/lon from hover
        hover_cols["latitude"]  = False
        hover_cols["longitude"] = False

        fig_shops = px.scatter_map(
            df_shops,
            lat="latitude",
            lon="longitude",
            color="rating",
            color_continuous_scale=MAP_SCALE_RATING,
            range_color=[3.0, 5.0],
            size_max=10,
            hover_name="displayName_text" if "displayName_text" in df_shops.columns else None,
            hover_data=hover_cols,
            labels={
                "rating":               "Bewertung",
                "userRatingCount":      "Reviews",
                "shortFormattedAddress":"Adresse",
                "preis":                "Preis",
            },
            map_style="carto-positron",
            center={"lat": 52.52, "lon": 13.405},
            zoom=10,
            height=660,
        )
        fig_shops.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            font={"family": "Inter, sans-serif", "size": 12, "color": "#374151"},
            paper_bgcolor="white",
            coloraxis_colorbar={
                "title": {"text": "Bewertung", "font": {"size": 12}},
                "tickvals": [3.0, 3.5, 4.0, 4.5, 5.0],
                "ticktext": ["3.0", "3.5", "4.0", "4.5", "5.0"],
                "tickfont": {"size": 11},
                "len": 0.6,
                "thickness": 12,
            },
        )
        st.plotly_chart(fig_shops, width="stretch")


# =============================================================================
#  PAGE 0b — Standort-Pitch (10-Minuten-Präsentation)
# =============================================================================
if page == "Standort-Pitch":
    st.markdown(
        "<span style='color:#6B7280; font-size:0.875rem;'>Gewichtung konfigurieren und Standortempfehlungen mit Marktkontext generieren.</span>",
        unsafe_allow_html=True,
    )

    # ── Präsentations-Struktur ─────────────────────────────────────────────────
    with st.expander("Präsentationsstruktur (10 Minuten)", expanded=False):
        st.markdown("""
| # | Abschnitt | Inhalt | Zeit |
|---|---|---|---|
| 1 | Titelfolie | Thema, Datum, Gewichtung | 0:30 |
| 2 | Berliner Döner-Markt | Kennzahlen gesamt, Marktgröße | 1:00 |
| 3 | Datenbasis & Methodik | 6 Quellen, 4 Analysen, Scoring-Modell | 1:30 |
| 4 | Scoring-Konfiguration | Gewählte Gewichtung und Strategie | 1:00 |
| 5–7 | Top-Empfehlungen | Top-3 Standorte mit Profil und Begründung | 3:00 |
| 8 | Karte | Räumlicher Kontext, LISA-Cluster | 1:00 |
| 9 | Live-Dashboard | Demo-Leitfaden für das interaktive Dashboard | 1:00 |
| 10 | Fazit | Kernbotschaft, Limitierungen, nächste Schritte | 1:00 |
        """)

    st.markdown("---")

    # ── Konfiguration ──────────────────────────────────────────────────────────
    with st.expander("Konfiguration", expanded=not st.session_state.get("pitch_ready", False)):
        ca, cb, cc = st.columns(3)
        with ca:
            p_nach = st.slider("Nachfrage",    0, 100, step=5, key="p_w_nach",  value=st.session_state.get("w_nachfrage", 30))
            p_mark = st.slider("Marktlücke",   0, 100, step=5, key="p_w_mark",  value=st.session_state.get("w_marktluecke", 30))
        with cb:
            p_wett = st.slider("Wettbewerb",   0, 100, step=5, key="p_w_wett",  value=st.session_state.get("w_wettbewerb", 20))
            p_infr = st.slider("Infrastruktur",0, 100, step=5, key="p_w_infr",  value=st.session_state.get("w_infrastruktur", 10))
        with cc:
            p_sozi = st.slider("Sozio",         0, 100, step=5, key="p_w_sozi", value=st.session_state.get("w_sozio", 10))
            p_mode = st.selectbox("Sozio-Modus", ["Kaufkraft", "Kiez im Aufbruch"], key="p_sozio_mode")
            p_top_n = st.selectbox("Top-N anzeigen", [3, 5, 10], key="p_top_n")

        if st.button("Analyse starten", type="primary", use_container_width=True):
            st.session_state["pitch_ready"]   = True
            st.session_state["pitch_weights"] = dict(
                w_nachfrage=p_nach, w_marktluecke=p_mark,
                w_wettbewerb=p_wett, w_infrastruktur=p_infr,
                w_sozio=p_sozi, sozio_mode=p_mode,
            )
            st.session_state["pitch_top_n"] = p_top_n
            st.rerun()

    # ── Pitch-Inhalt ──────────────────────────────────────────────────────────
    if st.session_state.get("pitch_ready"):
        pw   = st.session_state["pitch_weights"]
        topn = st.session_state.get("pitch_top_n", 3)

        df_scored = compute_scores(df_raw, **pw)
        top_df    = df_scored.nlargest(topn, "standort_score").reset_index(drop=True)

        ts = pd.Timestamp.now().strftime("%d.%m.%Y")
        w_str = (
            f"Nachfrage {pw['w_nachfrage']}% · Marktlücke {pw['w_marktluecke']}% · "
            f"Wettbewerb {pw['w_wettbewerb']}% · Infrastruktur {pw['w_infrastruktur']}% · "
            f"Sozio {pw['w_sozio']}%"
        )

        def slide_divider(num, title, timing):
            return f"""
            <div style="display:flex; align-items:center; gap:12px; margin:32px 0 16px; font-family:Inter,sans-serif;">
                <div style="background:#4A6FA5; color:white; border-radius:50%; width:26px; height:26px;
                            display:flex; align-items:center; justify-content:center;
                            font-size:0.72rem; font-weight:500; flex-shrink:0; letter-spacing:0;">{num}</div>
                <div style="flex:1; border-top:1px solid #E2E8F0;"></div>
                <div style="color:#374151; font-size:0.875rem; font-weight:500;">{title}</div>
                <div style="flex:1; border-top:1px solid #E2E8F0;"></div>
                <div style="background:#F3F4F6; color:#9CA3AF; border-radius:4px; padding:2px 8px;
                            font-size:0.72rem; flex-shrink:0;">{timing}</div>
            </div>"""

        # ── FOLIE 1: TITEL ────────────────────────────────────────────────────
        st.markdown(slide_divider(1, "Titelfolie", "0:30"), unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="background:#111827; border-radius:12px; padding:40px 48px; color:white;
                        text-align:center; font-family:Inter,sans-serif;">
                <div style="font-size:0.72rem; color:rgba(255,255,255,0.4); margin-bottom:14px;
                            letter-spacing:0.1em; text-transform:uppercase;">
                    Business Intelligence · Standortanalyse Berlin
                </div>
                <div style="font-size:2rem; font-weight:500; margin-bottom:10px; line-height:1.2;
                            letter-spacing:-0.03em;">
                    Dönerstandortanalyse Berlin
                </div>
                <div style="font-size:0.9rem; color:rgba(255,255,255,0.5); margin-bottom:24px;">
                    Datengetriebene Standortempfehlungen
                </div>
                <div style="display:inline-block; background:rgba(255,255,255,0.07);
                            border:1px solid rgba(255,255,255,0.1); border-radius:6px;
                            padding:6px 18px; font-size:0.78rem; color:rgba(255,255,255,0.45);">
                    {ts} &nbsp;·&nbsp; {w_str} &nbsp;·&nbsp; {pw['sozio_mode']}
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

        # ── FOLIE 2: BERLINER DÖNER-MARKT ────────────────────────────────────
        st.markdown(slide_divider(2, "Berliner Döner-Markt in Zahlen", "1:00"), unsafe_allow_html=True)

        total_doener    = int(df_raw["doener_count"].sum())
        total_plr       = len(df_raw)
        plr_ohne_doener = int((df_raw["doener_count"].fillna(0) == 0).sum())
        avg_rating      = df_raw["doener_avg_rating"].mean()
        berlin_avg_epd  = df_raw.loc[df_raw["doener_count"] > 0, "einwohner_pro_doener"].median()

        mk1, mk2, mk3, mk4, mk5 = st.columns(5)
        mk1.metric("Dönerläden gesamt",   f"{total_doener:,}".replace(",", "."))
        mk2.metric("Planungsräume",        f"{total_plr}")
        mk3.metric("PLR ohne Laden",       f"{plr_ohne_doener}")
        mk4.metric("Ø Bewertung",          safe_fmt(avg_rating, "{:.2f}"))
        mk5.metric("Median EW / Laden",    safe_fmt(berlin_avg_epd, "{:.0f}"))

        st.markdown(
            """
            <div style="background:#F7F8FA; border:1px solid #E2E8F0; padding:12px 16px;
                        border-radius:8px; margin-top:12px; font-size:0.85rem; color:#374151;
                        font-family:Inter,sans-serif; line-height:1.6;">
                Berlin verzeichnet über 1.300 Dönerläden auf 542 Planungsräume.
                In <strong style="color:#111827;">{plr_ohne}</strong> dieser Planungsräume
                gibt es keinen einzigen Betrieb — trotz teils signifikanter Bevölkerungsdichte.
            </div>""".format(plr_ohne=plr_ohne_doener),
            unsafe_allow_html=True,
        )

        # ── FOLIE 3: DATENBASIS & METHODIK ───────────────────────────────────
        st.markdown(slide_divider(3, "Datenbasis & Methodik", "1:30"), unsafe_allow_html=True)

        dm1, dm2 = st.columns(2)
        with dm1:
            st.markdown("**Datenquellen**")
            st.markdown("""
- Google Places API — 1.346 Dönerläden mit Bewertung, Öffnungszeiten, Reviews
- Google Places Aggregate API — Infrastruktur pro PLR-Polygon
- Amt für Statistik Berlin — Einwohner nach Alter (2024)
- Senatsverwaltung — Medianeinkommen (2023)
- Monitoring Soziale Stadtentwicklung (2023)
- IHK Berlin — Aktive Gastronomiebetriebe
            """)
        with dm2:
            st.markdown("**Analysen**")
            st.markdown("""
- **NLP:** Sentiment-Analyse von Google-Reviews (Top vs. Bottom 10 %)
- **Regression:** Logistische Regression — Erfolgsfaktoren auf PLR-Ebene
- **Moran's I:** Räumliche Autokorrelation — Clustering von Standortqualität
- **k-Means:** Typisierung der 542 Planungsräume in Kiezprofile
            """)

        # ── FOLIE 4: SCORING-KONFIGURATION ───────────────────────────────────
        st.markdown(slide_divider(4, "Scoring-Konfiguration dieser Analyse", "1:00"), unsafe_allow_html=True)

        score_labels_list = [
            ("Nachfrage",    pw['w_nachfrage'],    "Einwohnerdichte, Altersstruktur, ÖPNV, Nachtleben, Büros"),
            ("Marktlücke",   pw['w_marktluecke'],  "Einwohner/Laden-Ratio, geringe Gastro-Dichte"),
            ("Wettbewerb",   pw['w_wettbewerb'],   "Wettbewerbs-Index invertiert, wenig Fastfood"),
            ("Infrastruktur",pw['w_infrastruktur'],"ÖPNV, Universitäten, Schulen, Büros"),
            ("Sozio",        pw['w_sozio'],         pw['sozio_mode']),
        ]
        fig_weights = go.Figure(go.Bar(
            x=[w for _, w, _ in score_labels_list],
            y=[n for n, _, _ in score_labels_list],
            orientation="h",
            marker_color="#4A6FA5",
            marker_line_width=0,
            text=[f"{w} %" for _, w, _ in score_labels_list],
            textposition="outside",
            textfont={"size": 12, "color": "#374151"},
            hovertext=[f"{n}: {d}" for n, _, d in score_labels_list],
            hoverinfo="text",
        ))
        fig_weights.update_layout(
            height=200, margin={"l":0,"r":60,"t":10,"b":0},
            xaxis={"range":[0,115], "showgrid":False, "visible":False},
            yaxis={"autorange":"reversed"},
            plot_bgcolor="white",
            paper_bgcolor="white",
            showlegend=False,
            font={"family": "Inter, sans-serif", "size": 12, "color": "#374151"},
        )
        st.plotly_chart(fig_weights, width="stretch")

        st.caption(f"Sozio-Modus: {pw['sozio_mode']}  ·  Gewichtung normiert auf 100 %")

        # ── FOLIE 5–7: TOP-N EMPFEHLUNGEN ────────────────────────────────────
        st.markdown(
            slide_divider(
                "5–7" if topn == 3 else f"5–{4+topn}",
                f"Top-{topn} Standort-Empfehlungen",
                "3:00"
            ),
            unsafe_allow_html=True,
        )

        MEDALS  = ["01","02","03","04","05","06","07","08","09","10"]
        BORDERS = ["#E53935","#E53935","#E53935","#E53935","#E53935",
                   "#E53935","#E53935","#E53935","#E53935","#E53935"]

        score_col_map = {
            "s_nachfrage":    "Nachfrage",
            "s_marktluecke":  "Marktlücke",
            "s_wettbewerb":   "Wettbewerb",
            "s_infrastruktur":"Infrastruktur",
            "s_sozio":        "Sozio",
        }

        for row_start in range(0, topn, 3):
            row_items = list(top_df.itertuples())[row_start:row_start+3]
            cols = st.columns(len(row_items))

            for col, row in zip(cols, row_items):
                idx    = row.Index
                label  = MEDALS[idx] if idx < len(MEDALS) else str(idx+1)
                bcolor = BORDERS[idx % len(BORDERS)]

                subs = {lbl: getattr(row, sc, 0) for sc, lbl in score_col_map.items()}
                reasons = sorted(subs.items(), key=lambda x: x[1], reverse=True)[:3]
                reasons_html = "".join(
                    f'<li style="margin-bottom:3px;">{lbl} — <b>{val:.0f} Pkt.</b></li>'
                    for lbl, val in reasons
                )

                doener_cnt  = int(getattr(row, "doener_count",  0) or 0)
                transit_cnt = int(getattr(row, "transit_count", 0) or 0)
                einw        = safe_fmt(getattr(row, "einwohner_gesamt", None), "{:,.0f}").replace(",", ".")
                avg_rat     = safe_fmt(getattr(row, "doener_avg_rating", None), "{:.2f}")
                epd         = safe_fmt(getattr(row, "einwohner_pro_doener", None), "{:.0f}")

                card = f"""
                <div style="border:1px solid #E2E8F0; border-radius:10px; padding:20px;
                            background:white; box-shadow:0 1px 3px rgba(0,0,0,0.06),0 1px 2px rgba(0,0,0,0.04);
                            font-family:Inter,sans-serif;">
                    <div style="font-size:0.7rem; font-weight:500; color:#4A6FA5; text-transform:uppercase;
                                letter-spacing:0.06em; margin-bottom:4px;">{label}</div>
                    <div style="font-size:1rem; font-weight:500; color:#111827; margin-bottom:14px;
                                line-height:1.3;">{row.plr_name}</div>
                    <div style="margin-bottom:14px;">
                        <span style="font-size:2.2rem; font-weight:500; color:#111827; letter-spacing:-0.03em;">{row.standort_score:.1f}</span>
                        <span style="color:#9CA3AF; font-size:0.8rem; margin-left:4px;">/ 100</span>
                    </div>
                    <div style="border-top:1px solid #E2E8F0; padding-top:10px; margin-bottom:10px;">
                    <table style="width:100%; font-size:0.78rem; border-collapse:collapse;">
                        {"".join(
                            f'<tr><td style="padding:3px 0; color:#6B7280;">{lbl}</td>'
                            f'<td style="text-align:right; font-weight:500; color:#111827;">'
                            f'{getattr(row, sc, 0):.0f}</td></tr>'
                            for sc, lbl in score_col_map.items()
                        )}
                    </table>
                    </div>
                    <div style="border-top:1px solid #E2E8F0; padding-top:10px; margin-bottom:10px;">
                    <div style="font-size:0.72rem; font-weight:500; color:#9CA3AF; margin-bottom:6px;
                                text-transform:uppercase; letter-spacing:0.05em;">Stärkste Dimensionen</div>
                    <ul style="font-size:0.78rem; padding-left:14px; margin:0; color:#374151; line-height:1.8;">
                        {reasons_html}
                    </ul>
                    </div>
                    <div style="border-top:1px solid #E2E8F0; padding-top:10px;">
                    <table style="width:100%; font-size:0.78rem; color:#6B7280; border-collapse:collapse;">
                        <tr><td style="padding:2px 0;">Einwohner</td><td style="text-align:right; color:#374151; font-weight:500;">{einw}</td></tr>
                        <tr><td style="padding:2px 0;">EW / Laden</td><td style="text-align:right; color:#374151; font-weight:500;">{epd}</td></tr>
                        <tr><td style="padding:2px 0;">Dönerläden</td><td style="text-align:right; color:#374151; font-weight:500;">{doener_cnt}</td></tr>
                        <tr><td style="padding:2px 0;">ÖPNV-Haltestellen</td><td style="text-align:right; color:#374151; font-weight:500;">{transit_cnt}</td></tr>
                        <tr><td style="padding:2px 0;">Ø Bewertung</td><td style="text-align:right; color:#374151; font-weight:500;">{avg_rat}</td></tr>
                    </table>
                    </div>
                </div>
                """
                with col:
                    st.markdown(card, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        # ── FOLIE 8: KARTE ────────────────────────────────────────────────────
        map_slide_num = 5 + topn
        st.markdown(
            slide_divider(map_slide_num, "Räumlicher Kontext — Karte", "1:00"),
            unsafe_allow_html=True,
        )

        if geojson and all(c in df_scored.columns for c in ["centroid_lat", "centroid_lng"]):
            fig_pitch = choropleth(
                df_scored, geojson, color_col="standort_score",
                title="", color_scale=MAP_SCALE_MAIN, height=480,
                hover_data={"standort_score": True},
            )
            for idx_r, prow in enumerate(top_df.itertuples()):
                clat = getattr(prow, "centroid_lat", None)
                clon = getattr(prow, "centroid_lng", None)
                if pd.isna(clat) or pd.isna(clon):
                    continue
                fig_pitch.add_trace(go.Scattermap(
                    lat=[clat], lon=[clon],
                    mode="markers+text",
                    marker={"size": max(22 - idx_r * 2, 14), "color": BORDERS[idx_r % len(BORDERS)], "opacity": 0.95},
                    text=[MEDALS[idx_r] if idx_r < len(MEDALS) else str(idx_r+1)],
                    textfont={"size": 12, "color": "white"},
                    textposition="middle center",
                    hovertext=[f"{MEDALS[idx_r] if idx_r < len(MEDALS) else idx_r+1} {prow.plr_name} — Score: {prow.standort_score:.1f}"],
                    hoverinfo="text",
                    name=f"{MEDALS[idx_r] if idx_r < len(MEDALS) else idx_r+1} {prow.plr_name}",
                    showlegend=True,
                ))
            fig_pitch.update_layout(legend={
                "yanchor":"top","y":0.99,"xanchor":"left","x":0.01,
                "bgcolor":"rgba(255,255,255,0.9)","bordercolor":"#E2E8F0","borderwidth":1,
                "font":{"size":11, "family":"Inter, sans-serif"},
            })
            st.plotly_chart(fig_pitch, width="stretch")
        else:
            st.info("Karte nicht verfügbar (GeoJSON oder Zentroid-Koordinaten fehlen).")

        # ── FOLIE 9: LIVE-DASHBOARD ───────────────────────────────────────────
        demo_slide_num = map_slide_num + 1
        st.markdown(
            slide_divider(demo_slide_num, "Live-Demo: Interaktives Dashboard", "1:00"),
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div style="background:#F7F8FA; border:1px solid #E2E8F0; border-radius:8px;
                        padding:20px 24px; font-family:Inter,sans-serif;">
                <div style="font-size:0.82rem; font-weight:500; color:#111827; margin-bottom:12px;">
                    Demo-Leitfaden (ca. 1 Minute)
                </div>
                <ol style="margin:0; padding-left:18px; color:#374151; line-height:2; font-size:0.82rem;">
                    <li>
                        <span style="font-weight:500;">Scoring Lab</span> — Gewichtungsregler live anpassen und
                        zeigen, wie sich Karte und Ranking sofort aktualisieren.
                    </li>
                    <li>
                        <span style="font-weight:500;">Sozio-Strategie</span> — zwischen Kaufkraft und
                        Kiez im Aufbruch wechseln und die Verschiebung in der Karte zeigen.
                    </li>
                    <li>
                        <span style="font-weight:500;">Marktanalyse</span> — LISA-Cluster erklären,
                        Hot- und Cold-Spots im Stadtgebiet lokalisieren.
                    </li>
                    <li>
                        <span style="font-weight:500;">PLR-Vergleich</span> — zwei Top-Standorte
                        nebeneinanderstellen und den Radar-Chart zeigen.
                    </li>
                </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── FOLIE 10: FAZIT ───────────────────────────────────────────────────
        fazit_slide_num = demo_slide_num + 1
        st.markdown(
            slide_divider(fazit_slide_num, "Fazit & nächste Schritte", "1:00"),
            unsafe_allow_html=True,
        )

        top1 = top_df.iloc[0]
        top1_score = top1["standort_score"]
        top1_name  = top1["plr_name"]

        fc1, fc2 = st.columns(2)
        with fc1:
            st.markdown("**Kernbotschaft**")
            st.markdown(
                f"<div style='font-size:0.875rem; color:#374151; line-height:1.7; font-family:Inter,sans-serif;'>"
                f"Der Standort-Score identifiziert <strong style='color:#111827;'>{top1_name}</strong> als "
                f"Top-Empfehlung mit {top1_score:.1f}&thinsp;/&thinsp;100 Punkten. "
                f"Hohe Einwohnerdichte, gute ÖPNV-Anbindung und geringe Wettbewerbsdichte "
                f"kennzeichnen attraktive Standorte konsistent."
                f"</div>",
                unsafe_allow_html=True,
            )
        with fc2:
            st.markdown("**Einschränkungen & nächste Schritte**")
            st.markdown(
                "<div style='font-size:0.875rem; color:#374151; line-height:1.7; font-family:Inter,sans-serif;'>"
                "<ul style='padding-left:16px; margin:0;'>"
                "<li>Mietpreise auf PLR-Ebene nicht verfügbar</li>"
                "<li>Saisonale Effekte nicht erfasst</li>"
                "<li>NLP-Basis gering (Ø ca. 5 Reviews/Laden)</li>"
                "<li style='font-weight:500; color:#111827;'>Nächste Schritte: Vor-Ort-Begehung Top-3 PLR, "
                "Gewerberaumrecherche</li>"
                "</ul>"
                "</div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        if st.button("Neue Analyse"):
            st.session_state["pitch_ready"] = False
            st.rerun()

# =============================================================================
#  PAGE 1 — Scoring Lab
# =============================================================================
if page == "Scoring Lab":
    # ── Config section ────────────────────────────────────────────────────────
    cfg1, cfg2, cfg3, cfg4, cfg5, cfg_ctrl = st.columns([1, 1, 1, 1, 1, 1.2])
    with cfg1:
        w_nachfrage     = st.slider("Nachfrage",      0, 100, value=st.session_state.get("w_nachfrage",     _WEIGHT_DEFAULTS["w_nachfrage"]),     step=5, key="w_nachfrage")
    with cfg2:
        w_marktluecke   = st.slider("Marktlücke",     0, 100, value=st.session_state.get("w_marktluecke",  _WEIGHT_DEFAULTS["w_marktluecke"]),    step=5, key="w_marktluecke")
    with cfg3:
        w_wettbewerb    = st.slider("Wettbewerb",     0, 100, value=st.session_state.get("w_wettbewerb",   _WEIGHT_DEFAULTS["w_wettbewerb"]),     step=5, key="w_wettbewerb")
    with cfg4:
        w_infrastruktur = st.slider("Infrastruktur",  0, 100, value=st.session_state.get("w_infrastruktur",_WEIGHT_DEFAULTS["w_infrastruktur"]),  step=5, key="w_infrastruktur")
    with cfg5:
        w_sozio         = st.slider("Sozio",          0, 100, value=st.session_state.get("w_sozio",        _WEIGHT_DEFAULTS["w_sozio"]),          step=5, key="w_sozio")
    with cfg_ctrl:
        sozio_mode = st.radio(
            "Sozio-Strategie",
            ["Kaufkraft", "Kiez im Aufbruch"],
            help="Kaufkraft: Medianeinkommen + MSS-Status  |  Kiez im Aufbruch: MSS-Dynamik-Flag",
        )
        kiez_types = sorted(df_raw["kiez_typ"].dropna().unique().tolist())
        selected_kiez = st.multiselect("Kiez-Typ", kiez_types, default=[], help="Leer = alle")

    total_w = w_nachfrage + w_marktluecke + w_wettbewerb + w_infrastruktur + w_sozio
    sigma_color = COLOR_SUCCESS if total_w == 100 else "#D97706"

    ctrl_row_l, ctrl_row_r = st.columns([6, 1])
    with ctrl_row_l:
        st.markdown(
            f"<div style='font-size:0.78rem; color:{sigma_color}; padding:2px 0;'>"
            f"Summe: {total_w} %"
            f"{'  ·  Für beste Vergleichbarkeit sollte die Summe 100 % ergeben.' if total_w != 100 else ''}"
            f"  ·  Erläuterungen unter <em>Konzepte und Daten → Die 5 Scores</em>.</div>",
            unsafe_allow_html=True,
        )
    def _do_reset_weights():
        st.session_state.update(_WEIGHT_DEFAULTS)

    with ctrl_row_r:
        st.button("Zurücksetzen", help="Standardgewichtung", on_click=_do_reset_weights)

    st.markdown("---")

    # ── Compute scores ────────────────────────────────────────────────────────
    df_filtered = df_raw.copy()
    if selected_kiez:
        df_filtered = df_filtered[df_filtered["kiez_typ"].isin(selected_kiez)]

    df_scored = compute_scores(
        df_filtered,
        w_nachfrage, w_marktluecke, w_wettbewerb,
        w_infrastruktur, w_sozio, sozio_mode,
    )

    top15 = (
        df_scored.nlargest(15, "standort_score")[
            ["plr_name", "bezirk", "standort_score", "doener_count"]
        ]
        .reset_index(drop=True)
    )

    # Session-state for map highlight (table renders first → updates state → map uses it)
    if "scoring_highlight" not in st.session_state:
        st.session_state["scoring_highlight"] = None

    col_map, col_rank = st.columns([3, 2])

    # ── RIGHT: Top 15 table (render first to capture click events) ────────────
    with col_rank:
        st.subheader("Top 15")

        def _score_color(val):
            color = COLOR_SUCCESS if val > 50 else COLOR_DANGER
            return f"color: {color}; font-weight: 500"

        top15_display = top15.rename(columns={
            "plr_name": "PLR", "bezirk": "Bezirk",
            "standort_score": "Score", "doener_count": "Läden",
        })
        tbl_event = st.dataframe(
            top15_display.style.map(_score_color, subset=["Score"]),
            width="stretch",
            height=580,
            on_select="rerun",
            selection_mode="single-row",
            key="scoring_table",
        )
        if tbl_event.selection.rows:
            sel_name = top15.iloc[tbl_event.selection.rows[0]]["plr_name"]
            st.session_state["scoring_highlight"] = sel_name

    # ── LEFT: Choropleth map ──────────────────────────────────────────────────
    with col_map:
        if geojson is None:
            st.info("GeoJSON nicht verfügbar.")
        else:
            fig_map = px.choropleth_map(
                df_scored,
                geojson=geojson,
                locations="plr_id",
                color="standort_score",
                color_continuous_scale=MAP_SCALE_MAIN,
                map_style="carto-positron",
                center={"lat": 52.52, "lon": 13.405},
                zoom=9,
                hover_name="plr_name",
                hover_data={"bezirk": True, "standort_score": True, "doener_count": True},
                height=600,
            )
            fig_map.update_layout(
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                coloraxis_colorbar={"title": {"text": "Score", "font": {"size": 12}}, "thickness": 12, "tickfont": {"size": 11}},
                font={"family": "Inter, sans-serif", "size": 12, "color": "#374151"},
                paper_bgcolor="white",
            )
            # Highlight selected PLR
            hl = st.session_state.get("scoring_highlight")
            if hl:
                hlr = df_scored[df_scored["plr_name"] == hl]
                if not hlr.empty and pd.notna(hlr.iloc[0].get("centroid_lat")):
                    fig_map.add_trace(go.Scattermap(
                        lat=[hlr.iloc[0]["centroid_lat"]],
                        lon=[hlr.iloc[0]["centroid_lng"]],
                        mode="markers+text",
                        marker={"size": 18, "color": "#4A6FA5", "opacity": 0.9},
                        text=[hl],
                        textfont={"size": 10, "color": "white"},
                        textposition="middle center",
                        hovertext=[f"{hl} — Score: {hlr.iloc[0]['standort_score']:.1f}"],
                        hoverinfo="text",
                        showlegend=False,
                    ))
            st.plotly_chart(fig_map, width="stretch")


# =============================================================================
#  PAGE 2 — Marktanalyse (4 Tabs)
# =============================================================================
elif page == "Marktanalyse":
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["Marktlücken", "Wettbewerb", "Infrastruktur"])

    # ── Tab 1: Marktlücken ──────────────────────────────────────────────────
    with tab1:
        avg_epd   = df_raw["einwohner_pro_doener"].median()
        max_epd   = df_raw["einwohner_pro_doener"].max()
        n_ohne    = int((df_raw["doener_count"] == 0).sum())

        m1, m2, m3 = st.columns(3)
        m1.metric("Median EW / Laden", f"{avg_epd:,.0f}")
        m2.metric("Maximum EW / Laden", f"{max_epd:,.0f}" if pd.notna(max_epd) else "–")
        m3.metric("PLR ohne Laden", n_ohne)

        st.markdown("---")
        if geojson:
            fig_ml = choropleth(
                df_raw.copy(), geojson, "einwohner_pro_doener",
                color_scale=MAP_SCALE_MAIN,
                hover_data={"bezirk": True, "einwohner_pro_doener": True, "doener_count": True},
                height=480,
            )
            fig_ml.update_layout(coloraxis_colorbar={"title": {"text": "EW/Döner", "font": {"size": 12}}, "thickness": 12})
            st.plotly_chart(fig_ml, width='stretch')

        st.markdown("**Top 15 Planungsräume nach Marktlückenpotenzial** (mind. 3.000 Einwohner)")
        top_gaps = (
            df_raw[df_raw["einwohner_gesamt"] >= 3000]
            .nlargest(15, "einwohner_pro_doener")[
                ["plr_name", "bezirk", "einwohner_gesamt", "doener_count", "einwohner_pro_doener"]
            ]
            .reset_index(drop=True)
        )
        top_gaps.columns = ["PLR", "Bezirk", "Einwohner", "Döner", "EW / Döner"]
        st.dataframe(safe_df(top_gaps), width='stretch', height=560)

    # ── Tab 2: Wettbewerb ───────────────────────────────────────────────────
    with tab2:
        bezirk_agg = (
            df_raw.groupby("bezirk")
            .agg(doener=("doener_count", "sum"), fastfood=("fastfood_count", "sum"))
            .reset_index()
            .sort_values("doener", ascending=False)
        )
        # Rename for display
        bezirk_melt = bezirk_agg.melt(
            id_vars="bezirk", value_vars=["doener", "fastfood"],
            var_name="Kategorie", value_name="Anzahl",
        )
        bezirk_melt["Kategorie"] = bezirk_melt["Kategorie"].map(
            {"doener": "Döner", "fastfood": "Fastfood"}
        )
        fig_bar = px.bar(
            bezirk_melt,
            x="bezirk", y="Anzahl", color="Kategorie",
            barmode="group",
            labels={"bezirk": "Bezirk", "Anzahl": "Anzahl Standorte"},
            color_discrete_map={"Döner": COLOR_NEUTRAL, "Fastfood": COLOR_DANGER},
            height=420,
        )
        fig_bar.update_layout(
            font={"family": "Inter, sans-serif", "size": 12, "color": "#374151"},
            paper_bgcolor="white", plot_bgcolor="white", xaxis_tickangle=-30,
            legend_title="",
        )
        st.plotly_chart(fig_bar, width='stretch')

    # ── Tab 3: Infrastruktur ────────────────────────────────────────────────
    with tab3:
        infra_options = {
            "ÖPNV": "transit_count",
            "Universitäten": "university_count",
            "Nachtleben": "nightlife_count",
            "Büros": "office_count",
        }
        infra_sel_label = st.selectbox("Metrik", list(infra_options.keys()))
        infra_col = infra_options[infra_sel_label]

        if geojson:
            fig_infra = choropleth(
                df_raw, geojson, infra_col,
                color_scale=MAP_SCALE_INFRA,
                hover_data={"bezirk": True, infra_col: True, "doener_count": True},
                height=480,
            )
            st.plotly_chart(fig_infra, width='stretch')

        st.markdown(
            "<div style='background:#F7F8FA; border:1px solid #E2E8F0; padding:12px 16px; "
            "border-radius:8px; font-size:0.82rem; color:#374151; font-family:Inter,sans-serif; line-height:1.7;'>"
            "<strong style='color:#111827;'>Warum ist der ÖPNV-Wert in manchen PLR so hoch?</strong><br>"
            "Die Google Places Aggregate API zählt alle Orte vom Typ <code>transit_station</code> innerhalb "
            "des PLR-Polygons — dazu gehören S-Bahn, U-Bahn, Tram, Busstationen und Fähren. "
            "Planungsräume mit Bahnhöfen oder Knotenpunkten (z.B. Wannsee: S-Bahn-Endhaltestelle + Fähre + Busknoten) "
            "erreichen dadurch Werte von 60–80+. Die Metrik misst <em>Frequenz</em>, nicht reine Linienzahl. "
            "Für die Scoring-Formel wird der Wert min-max-normiert — hohe Absolutwerte fallen daher "
            "nicht überproportional ins Gewicht. Details unter <em>Konzepte und Daten</em>."
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.markdown("**Pearson-Korrelation: Infrastruktur vs. Ø Bewertung**")
        infra_cols  = ["transit_count", "university_count", "school_count",
                       "nightlife_count", "office_count", "fastfood_count"]
        target_col  = "doener_avg_rating"
        df_corr_src = df_raw[df_raw["doener_count"] > 0].dropna(subset=[target_col])
        corr_rows = []
        for c in infra_cols:
            if c in df_corr_src.columns:
                r = df_corr_src[[c, target_col]].dropna()
                if len(r) > 5:
                    corr_rows.append({"Metrik": c, "Pearson r": round(r[c].corr(r[target_col]), 3)})
        if corr_rows:
            st.dataframe(safe_df(pd.DataFrame(corr_rows).sort_values("Pearson r", ascending=False)), width='stretch')
        else:
            st.caption("Nicht genug Daten.")


# =============================================================================
#  PAGE 3 — Erfolgs-Profil
# =============================================================================
elif page == "Erfolgs-Profil":
    st.markdown("---")

    img_col1, img_col2 = st.columns(2)

    with img_col1:
        st.markdown("**NLP-Analyse: Sentiment Top vs. Bottom 10 %**")
        st.caption("Vergleich der Google-Review-Sentiments in Planungsräumen mit Top- und Bottom-Rating-Läden (VADER).")
        try:
            st.image(NLP_IMG, width='stretch')
        except Exception:
            st.caption("Grafik nicht verfügbar — nb_04 ausführen.")

    with img_col2:
        st.markdown("**Regressionskoeffizienten**")
        st.caption("Logistische Regression: Welche Standortmerkmale erhöhen die Wahrscheinlichkeit eines erfolgreichen Ladens?")
        try:
            st.image(REG_IMG, width='stretch')
        except Exception:
            st.caption("Grafik nicht verfügbar — nb_04 ausführen.")


# =============================================================================
#  PAGE 4 — PLR-Vergleich
# =============================================================================
elif page == "PLR-Vergleich":
    st.markdown(
        "<span style='color:#6B7280; font-size:0.875rem;'>Direkter Vergleich von bis zu 4 Planungsräumen.</span>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # Compute default scores for comparison (equal weights)
    df_comp = compute_scores(df_raw, 30, 30, 20, 10, 10, "Kaufkraft")

    plr_options = sorted(df_comp["plr_name"].tolist())
    selected_plrs = st.multiselect(
        "Planungsräume (max. 4)",
        options=plr_options,
        default=[],
        max_selections=4,
    )

    if len(selected_plrs) < 2:
        st.caption("Mindestens 2 Planungsräume auswählen.")
    else:
        df_sel = df_comp[df_comp["plr_name"].isin(selected_plrs)].copy()

        # ── Radar chart ────────────────────────────────────────────────────
        score_dims   = ["s_nachfrage", "s_marktluecke", "s_wettbewerb", "s_infrastruktur", "s_sozio"]
        score_labels = ["Nachfrage", "Marktlücke", "Wettbewerb", "Infrastruktur", "Sozio"]
        palette = [
            ("#4A6FA5", "rgba(74,111,165,0.10)"),
            ("#34A853", "rgba(52,168,83,0.10)"),
            ("#D97706", "rgba(217,119,6,0.10)"),
            ("#6B7280", "rgba(107,114,128,0.10)"),
        ]

        fig_comp = go.Figure()
        for i, (_, row) in enumerate(df_sel.iterrows()):
            vals = [row.get(d, 0) for d in score_dims]
            lc, fc = palette[i % len(palette)]
            fig_comp.add_trace(
                go.Scatterpolar(
                    r=vals + [vals[0]],
                    theta=score_labels + [score_labels[0]],
                    fill="toself",
                    name=row["plr_name"],
                    line_color=lc,
                    line_width=1.5,
                    fillcolor=fc,
                )
            )
        fig_comp.update_layout(
            polar=dict(radialaxis=dict(
                visible=True, range=[0, 100],
                tickfont={"size": 9, "color": "#9CA3AF"},
                gridcolor="#E2E8F0",
            )),
            height=480,
            font={"family": "Inter, sans-serif", "size": 12, "color": "#374151"},
            paper_bgcolor="white",
            legend=dict(orientation="h", y=-0.15, font={"size": 12}),
        )
        st.plotly_chart(fig_comp, width='stretch')

        st.markdown("---")

        # ── Comparison table ────────────────────────────────────────────────
        compare_cols = [
            "plr_name", "bezirk",
            "standort_score", "s_nachfrage", "s_marktluecke", "s_wettbewerb",
            "s_infrastruktur", "s_sozio",
            "einwohner_gesamt", "doener_count", "doener_avg_rating",
            "transit_count", "medianeinkommen_eur", "mss_status_index",
            "nightlife_count", "kiez_typ",
        ]
        available_cols = [c for c in compare_cols if c in df_sel.columns]
        df_display = df_sel[available_cols].set_index("plr_name").T
        st.dataframe(safe_df(df_display), width='stretch')

        csv_data = df_sel[available_cols].to_csv(index=False, sep=";", decimal=",")
        st.download_button(
            label="CSV exportieren",
            data=csv_data,
            file_name="plr_vergleich.csv",
            mime="text/csv",
        )


# =============================================================================
#  PAGE 4b — Konzepte & Daten
# =============================================================================
if page == "Konzepte und Daten":
    st.markdown("---")

    # ── 1. Planungsräume ─────────────────────────────────────────────────────
    with st.expander("Was sind Planungsräume?", expanded=True):
        st.markdown("""
**Planungsraum (PLR)** ist die kleinste statistische Einheit der Berliner Stadtplanung.
Berlin ist in **542 Planungsräume** unterteilt (12 Bezirke). Ø ca. 7.000 Einwohner, ca. 3 km² pro PLR.

Wir analysieren auf PLR-Ebene, weil Bevölkerungs-, Einkommens- und Sozialdaten auf dieser Granularität vorliegen
und Planungsräume homogenere Quartiere abbilden als Postleitzahlen oder Bezirke.
Die Google Places Aggregate API kann exakt auf PLR-Polygonen abgefragt werden.

Jeder Dönerladen wird per Point-in-Polygon einem PLR zugeordnet;
alle Läden eines PLR werden zu Durchschnittswerten aggregiert.
        """)

    # ── 2. Die 5 Scores ──────────────────────────────────────────────────────
    with st.expander("Die 5 Scores — Berechnung und Bedeutung", expanded=True):
        st.markdown("""
Alle Scores liegen auf **0–100**. Jede Variable wird min-max-normiert
(0 = schlechtester Wert in Berlin, 100 = bester Wert). Der Gesamtscore ist die gewichtete Summe.

---

**Score 1 — Nachfrage** *(Wie viele potenzielle Kunden gibt es hier?)*

| Variable | Richtung | Erklärung |
|---|---|---|
| Einwohnerdichte | + | Mehr Einwohner/km² = mehr Laufkundschaft |
| Anteil 18–35-Jährige | + | Kernzielgruppe |
| ÖPNV-Haltestellen | + | Frequenz → Impulskäufe |
| Nachtleben (Bars, Clubs) | + | Spätabend-Nachfrage |
| Büros | + | Mittagsgeschäft |
| Ø Öffnungsstunden/Woche bestehender Läden | + | Proxy für bewährte lokale Nachfrage |

---

**Score 2 — Marktlücke** *(Wie unterversorgt ist das Gebiet?)*

| Variable | Richtung | Erklärung |
|---|---|---|
| Einwohner pro Dönerladen | + | Viele Einwohner, wenig Läden = Lücke |
| Gastronomiebetriebe/km² | − | Wenig Gastro insgesamt = Lücke |
| Ø Bewertung bestehender Läden | − | Hohe Bestandsqualität = stärkerer Wettbewerb |

---

**Score 3 — Wettbewerb** *(Niedriger Wettbewerb = hoher Score)*

| Variable | Richtung | Erklärung |
|---|---|---|
| Wettbewerbs-Index | − | (Döner + Fastfood) / Einwohner × 1.000 |
| Fastfood-Betriebe | − | Direkter Sättigungsgrad |

---

**Score 4 — Infrastruktur** *(Lagequalität strukturell)*

| Variable | Richtung | Erklärung |
|---|---|---|
| ÖPNV-Haltestellen | + | Zugänglichkeit — zählt alle transit_station-Typen (S, U, Tram, Bus, Fähre) |
| Universitäten | + | Studierende als Zielgruppe |
| Schulen | + | Mittagszielgruppe |
| Büros | + | Mittagsgeschäft |

*Hinweis ÖPNV:* Die Google Places Aggregate API zählt alle `transit_station`-Orte im Polygon —
darunter fallen S-Bahn, U-Bahn, Tram, Bus und Fähren kumuliert. PLR mit Bahnhöfen oder
Verkehrsknoten (z.B. Wannsee) erreichen Werte von 60–80+. Da der Wert normiert wird,
hat das keinen überproportionalen Einfluss auf den Score.

---

**Score 5 — Sozio** *(zwei wählbare Strategien)*

*Kaufkraft:* Medianeinkommen (+) · MSS-Status-Index (−, invertiert)

*Kiez im Aufbruch:* Gentrification-Flag — MSS-Status niedrig (benachteiligte Lage) UND positive MSS-Dynamik (Aufwertungstrend)

---

**Gesamtscore**

`Standort-Score = (w₁·S₁ + w₂·S₂ + w₃·S₃ + w₄·S₄ + w₅·S₅) / Σwᵢ`

Standardgewichtung: Nachfrage 30 % · Marktlücke 30 % · Wettbewerb 20 % · Infrastruktur 10 % · Sozio 10 %
        """)

    # ── 3. Score-Formeln (formal) ────────────────────────────────────────────
    with st.expander("Score-Formeln (formal)", expanded=False):
        st.markdown("**Normierung:**")
        st.latex(r"\text{norm}(x) = \frac{x - x_{\min}}{x_{\max} - x_{\min}}")

        st.markdown("**S1 — Nachfrage:**")
        st.latex(r"S_1 = \frac{\text{norm}(\rho_E)+\text{norm}(A_{18-35})+\text{norm}(T)+\text{norm}(N)+\text{norm}(O)+\text{norm}(H)}{6}\times100")
        st.caption("ρ_E Einwohnerdichte, A Anteil 18–35, T ÖPNV, N Nachtleben, O Büros, H Öffnungszeit")

        st.markdown("**S2 — Marktlücke:**")
        st.latex(r"S_2 = \frac{\text{norm}(EW/D)+(1-\text{norm}(G_d))+(1-\text{norm}(R))}{3}\times100")
        st.caption("EW/D Einwohner/Döner, G_d Gastrodichte, R Ø Bewertung bestehender Läden")

        st.markdown("**S3 — Wettbewerb:**")
        st.latex(r"S_3 = \left(1-\frac{\text{norm}(W)+\text{norm}(F)}{2}\right)\times100")
        st.caption("W Wettbewerbs-Index, F Fastfood-Count")

        st.markdown("**S4 — Infrastruktur:**")
        st.latex(r"S_4 = \frac{\text{norm}(T)+\text{norm}(U)+\text{norm}(S)+\text{norm}(O)}{4}\times100")
        st.caption("T ÖPNV, U Uni, S Schule, O Büros")

        st.markdown("**S5 — Sozio (Kaufkraft):**")
        st.latex(r"S_5 = \frac{\text{norm}(I)+(1-\text{norm}(MSS))}{2}\times100")
        st.caption("I Medianeinkommen, MSS Sozialstruktur-Index")

        st.markdown("**Gesamt:**")
        st.latex(r"\text{Score}=\frac{w_1 S_1+w_2 S_2+w_3 S_3+w_4 S_4+w_5 S_5}{\sum w_i}")

    # ── 4. Analysemethoden ───────────────────────────────────────────────────
    with st.expander("Analysemethoden (M1–M5)", expanded=False):
        st.markdown("""
**M1 — Datenintegration** *(nb_03_merge-masterdata.ipynb)*

Zusammenführung aller 7 Rohdatenquellen auf PLR-Ebene. Räumliche Zuordnung der
Dönerläden per Point-in-Polygon. Aggregation je PLR (Ø Rating, Summen, Anteile).
Ergebnis: SQLite-Datenbank `berlin_masterdata.db` mit 542 Zeilen × 34 Spalten.

---

**M2 — Explorative Analyse & Feature Engineering** *(nb_04_analyse.ipynb)*

Ausreißer-Behandlung, Verteilungsanalysen, Ableitung abgeleiteter Variablen
(Einwohner/Döner, Wettbewerbs-Index, Gastro-Fluktuation, Gentrification-Flag).

---

**M3 — Logistische Regression (Erfolgsfaktoren)**

Zielvariable: `erfolg_flag` = 1, wenn Ø Rating ≥ 4,3 UND Bewertungsanzahl ≥ 200.
Features: alle PLR-Kennzahlen, Z-Score-standardisiert.
Methode: Logistische Regression mit L2-Regularisierung, 80/20 Train-Test-Split.
Ergebnis: Koeffizientenplot (sichtbar auf der Erfolgsprofil-Seite).

---

**M4 — NLP Sentiment-Analyse**

Google Places liefert bis zu 5 Reviews pro Laden. Sentiment-Berechnung mit **VADER**
(regelbasiert, kein Training erforderlich).
Vergleich: Top-10 % vs. Bottom-10 % nach Rating.
Ergebnis: Radar-Chart (sichtbar auf der Erfolgsprofil-Seite).
*Limitierung:* Ø ca. 5 Reviews/Laden — Ergebnisse sind als Tendenz zu interpretieren.

---

**M5 — PLR-Typisierung (k-Means Clustering)**

k-Means gruppiert die 542 PLR in Kiez-Typen anhand aller 5 Score-Dimensionen
plus Gastro-Fluktuation und MSS-Dynamik.
Optimale Clusteranzahl per Elbow-Methode.
Typische Cluster: Studentenviertel, Bürokiez, Wohnquartier, Nachtleben-Kiez, Randgebiet.
Jeder PLR bekommt einen `kiez_typ`-Label als Filter im PLR-Vergleich.
        """)

    # ── 5. Datenquellen ──────────────────────────────────────────────────────
    with st.expander("Datenquellen", expanded=False):
        data_sources = pd.DataFrame([
            ["Google Places Text Search API", "1.346 Dönerläden mit Koordinaten, Rating, Öffnungszeiten, Reviews", "2024"],
            ["Google Places Aggregate API", "Infrastruktur-Counts pro PLR-Polygon (ÖPNV, Uni, Schule, Nachtleben, Büro, Fastfood)", "2024"],
            ["ODIS Berlin — LOR Geodaten", "542 PLR-Polygone (EPSG:25833)", "2021"],
            ["Amt für Statistik Berlin", "Einwohner nach Alter pro PLR", "2024"],
            ["Senatsverwaltung — Medianeinkommen", "Medianeinkommen je PLR", "2023"],
            ["Monitoring Soziale Stadtentwicklung (MSS)", "Sozialstatus- und Dynamik-Index pro PLR", "2023"],
            ["IHK Berlin Open Data", "Aktive Gewerbebetriebe mit NACE-Code pro PLR", "2024"],
        ], columns=["Quelle", "Inhalt", "Stand"])
        st.dataframe(safe_df(data_sources), width='stretch')

    # ── 6. Limitierungen ─────────────────────────────────────────────────────
    with st.expander("Bekannte Limitierungen", expanded=False):
        st.markdown("""
- **Mietpreise fehlen:** Nicht öffentlich auf PLR-Ebene verfügbar — ein zentraler Standortfaktor fehlt im Score.
- **Fastfood-Tag unvollständig:** Dönerläden sind teils als `turkish_restaurant`, teils als `fast_food_restaurant` getaggt. `fastfood_count` kann Dönerläden selbst mitzählen.
- **Reviews dünn:** Ø ~5 Reviews/Laden. NLP-Ergebnisse sind als Tendenz zu verstehen.
- **ÖPNV-Zählung kumulativ:** Zählt alle `transit_station`-Typen (S, U, Tram, Bus, Fähre). Knoten-PLR haben hohe Absolutwerte (normiert, daher kein überproportionaler Score-Einfluss).
- **Statischer Schnappschuss:** Datenstand 2023/2024. Saisonale Effekte und Marktveränderungen nicht erfasst.
- **Migrationsdaten fehlen:** Aktuellste PLR-Migrationsdaten aus 2020 nutzen das alte LOR-System (447 PLR, nicht mappbar).
- **Koordinatenprojektion:** UTM 33N (EPSG:25833) → WGS84 als reine Python-Implementierung; minimale Rundungsfehler möglich.
        """)

    st.markdown("---")
    st.caption("Python · Streamlit · Pandas · Plotly · SQLite  ·  BI-Projekt · FU Berlin · 2024/2025")


