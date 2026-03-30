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
    page_icon="🥙",
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
COLOR_SUCCESS = "#2ecc71"
COLOR_DANGER  = "#e74c3c"
COLOR_NEUTRAL = "#3498db"

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
            df[flag] = df[flag].map({True: "✅", False: "❌", 1: "✅", 0: "❌"}).fillna("–")
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
    s2 = (norm(fn("einwohner_pro_doener")) + (1 - norm(fn("gastro_dichte")))) / 2 * 100

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
    if sozio_mode == "Kaufkraft 💰":
        s5 = (norm(fn("medianeinkommen_eur")) + (1 - norm(fn("mss_status_index")))) / 2 * 100
    else:  # Kiez im Aufbruch 🌱
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
    color_scale: str = "RdYlGn",
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
        font_family="sans-serif",
        coloraxis_colorbar={"title": {"text": color_col}},
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

st.sidebar.image(
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/1px-transparent.png",
    width=1,
)  # invisible spacer – keeps layout stable on load
st.sidebar.title("🥙 Döner Standortanalyse")
st.sidebar.markdown("**Berlin · 542 Planungsräume**")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "🌍 Berlin Übersicht",
        "🚀 Standort-Pitch",
        "🎯 Scoring Lab",
        "📊 Marktanalyse",
        "🏅 Erfolgs-Profil",
        "🔍 PLR-Vergleich",
        "📚 Konzepte & Daten",
        "📖 Methodik",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption("Datenstand: 2023/2024  ·  542 PLR")

# ---------------------------------------------------------------------------
# Guard: check DB exists before loading anything
# ---------------------------------------------------------------------------
if not os.path.exists(DB_PATH):
    st.error(
        f"⚠️  Datenbank nicht gefunden: `{DB_PATH}`  \n"
        "Bitte zuerst die Data-Pipeline-Notebooks ausführen "
        "(nb_01 → nb_02 → nb_03).",
        icon="🚨",
    )
    st.stop()

# ---------------------------------------------------------------------------
# Load data (cached)
# ---------------------------------------------------------------------------
df_raw   = load_data()
geojson  = load_geojson() if os.path.exists(GEOJSON_PATH) else None

if geojson is None:
    st.warning(
        f"⚠️  GeoJSON nicht gefunden: `{GEOJSON_PATH}` — Karten werden deaktiviert.",
        icon="⚠️",
    )


# =============================================================================
#  PAGE 0 — Berlin Übersicht (Karte aller Döner-Läden)
# =============================================================================
if page == "🌍 Berlin Übersicht":
    st.title("🌍 Berlin — Alle Döner-Läden")
    st.markdown(
        "Jeder Punkt ist ein einzelner Laden. **Farbe = Bewertung** (🔴 schlecht → 🟡 okay → 🟢 top). "
        "Hovere über einen Punkt für Details."
    )
    st.markdown("---")

    df_shops = load_shops()

    if df_shops.empty:
        st.warning(
            f"Shops-Datei nicht gefunden: `{DOENER_CSV}`  \n"
            "Bitte nb_01 ausfuehren, um die Daten zu generieren.",
            icon="⚠️",
        )
    else:
        # ── KPI row ───────────────────────────────────────────────────────────
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("🥙 Döner-Läden gesamt",  f"{len(df_shops):,}".replace(",", "."))
        k2.metric("⭐ Ø Bewertung",          f"{df_shops['rating'].mean():.2f}")
        k3.metric("💬 Reviews gesamt",       f"{int(df_shops['userRatingCount'].sum()):,}".replace(",", "."))
        k4.metric("🌟 Höchstes Rating",      f"{df_shops['rating'].max():.1f}")
        k5.metric("🚫 PLR ohne Laden",       f"{int((df_raw['doener_count'].fillna(0) == 0).sum())}")

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
            color_continuous_scale=[
                [0.0, "#e74c3c"],
                [0.25, "#e67e22"],
                [0.5,  "#f1c40f"],
                [0.75, "#2ecc71"],
                [1.0,  "#27ae60"],
            ],
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
            coloraxis_colorbar={
                "title": {"text": "Bewertung"},
                "tickvals": [3.0, 3.5, 4.0, 4.5, 5.0],
                "ticktext": ["3.0 🔴", "3.5", "4.0 🟡", "4.5", "5.0 🟢"],
                "len": 0.6,
            },
        )
        st.plotly_chart(fig_shops, width="stretch")


# =============================================================================
#  PAGE 0b — Standort-Pitch (10-Minuten-Präsentation)
# =============================================================================
if page == "🚀 Standort-Pitch":
    st.title("Standort-Pitch")
    st.markdown(
        "Konfiguriere deine Präferenzen und erhalte eine fertige **10-Minuten-Präsentation** "
        "mit Top-Standort-Empfehlungen, Marktkontext und Dashboard-Demo-Leitfaden."
    )

    # ── Präsentations-Struktur ─────────────────────────────────────────────────
    with st.expander("Präsentations-Ablauf (10 Minuten)", expanded=False):
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
    with st.expander("Einstellungen konfigurieren", expanded=not st.session_state.get("pitch_ready", False)):
        ca, cb, cc = st.columns(3)
        with ca:
            p_nach = st.slider("Nachfrage",    0, 100, step=5, key="p_w_nach",  value=st.session_state.get("w_nachfrage", 30))
            p_mark = st.slider("Marktlücke",   0, 100, step=5, key="p_w_mark",  value=st.session_state.get("w_marktluecke", 30))
        with cb:
            p_wett = st.slider("Wettbewerb",   0, 100, step=5, key="p_w_wett",  value=st.session_state.get("w_wettbewerb", 20))
            p_infr = st.slider("Infrastruktur",0, 100, step=5, key="p_w_infr",  value=st.session_state.get("w_infrastruktur", 10))
        with cc:
            p_sozi = st.slider("Sozio",         0, 100, step=5, key="p_w_sozi", value=st.session_state.get("w_sozio", 10))
            p_mode = st.selectbox("Sozio-Modus", ["Kaufkraft 💰", "Kiez im Aufbruch 🌱"], key="p_sozio_mode")
            p_top_n = st.selectbox("Top-N anzeigen", [3, 5, 10], key="p_top_n")

        if st.button("Pitch generieren", type="primary", use_container_width=True):
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
            <div style="display:flex; align-items:center; gap:12px; margin:24px 0 12px;">
                <div style="background:#0f3460; color:white; border-radius:50%; width:32px; height:32px;
                            display:flex; align-items:center; justify-content:center;
                            font-size:0.85em; font-weight:bold; flex-shrink:0;">{num}</div>
                <div style="flex:1; border-top:2px solid #0f3460;"></div>
                <div style="color:#0f3460; font-size:1.05em; font-weight:600;">{title}</div>
                <div style="flex:1; border-top:2px solid #0f3460;"></div>
                <div style="background:#ecf0f1; color:#7f8c8d; border-radius:4px; padding:2px 8px;
                            font-size:0.78em; flex-shrink:0;">{timing}</div>
            </div>"""

        # ── FOLIE 1: TITEL ────────────────────────────────────────────────────
        st.markdown(slide_divider(1, "Titelfolie", "0:30"), unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);
                        border-radius:16px; padding:36px 40px; color:white; text-align:center;">
                <div style="font-size:0.9em; opacity:0.6; margin-bottom:8px; letter-spacing:2px; text-transform:uppercase;">
                    Business Intelligence · Standortanalyse
                </div>
                <div style="font-size:2.4em; font-weight:700; margin-bottom:8px; line-height:1.2;">
                    Döner-Standortanalyse Berlin
                </div>
                <div style="font-size:1.1em; opacity:0.8; margin-bottom:20px;">
                    Datengetriebene Empfehlungen für neue Dönerläden in Berlin
                </div>
                <div style="display:inline-block; background:rgba(255,255,255,0.1); border-radius:8px;
                            padding:8px 20px; font-size:0.85em; opacity:0.75;">
                    {ts} · Gewichtung: {w_str} · Modus: {pw['sozio_mode']}
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
        mk1.metric("Dönerläden gesamt",      f"{total_doener:,}".replace(",", "."))
        mk2.metric("Planungsräume",           f"{total_plr}")
        mk3.metric("PLR ohne Laden",          f"{plr_ohne_doener}")
        mk4.metric("Ø Bewertung",            safe_fmt(avg_rating, "{:.2f}"))
        mk5.metric("Median Einwohner/Laden", safe_fmt(berlin_avg_epd, "{:.0f}"))

        st.markdown(
            """
            <div style="background:#f8f9fa; border-left:4px solid #3498db; padding:12px 16px;
                        border-radius:0 8px 8px 0; margin-top:12px; font-size:0.92em; color:#2c3e50;">
                Berlin ist Deutschlands Döner-Hauptstadt. Mit über 1.300 Läden auf 542 Planungsräume
                verteilt sind jedoch nicht alle Stadtteile gleich gut versorgt.
                In <strong>{plr_ohne}</strong> Planungsräumen gibt es keinen einzigen Dönerladen —
                trotz teilweise signifikanter Einwohnerzahlen. Genau hier liegt die Chance.
            </div>""".format(plr_ohne=plr_ohne_doener),
            unsafe_allow_html=True,
        )

        # ── FOLIE 3: DATENBASIS & METHODIK ───────────────────────────────────
        st.markdown(slide_divider(3, "Datenbasis & Methodik", "1:30"), unsafe_allow_html=True)

        dm1, dm2 = st.columns(2)
        with dm1:
            st.markdown("**Datenquellen (6)**")
            st.markdown("""
- Google Places API — 1.346 Dönerläden mit Rating, Öffnungszeiten, Reviews
- Google Places Aggregate API — Infrastruktur für alle 542 PLR-Polygone
- Bevölkerungsstatistik Berlin 2024 — Einwohner nach Alter
- Medianeinkommen Senatsverwaltung 2023
- Monitoring Soziale Stadtentwicklung 2023
- IHK Berlin Gewerbedaten — aktive Gastronomiebetriebe
            """)
        with dm2:
            st.markdown("**Analysen (4)**")
            st.markdown("""
- **NLP (M3):** Sentiment-Analyse von Google-Reviews — Top vs. Bottom-Läden
- **Regression (M4):** Logistische Regression — welche Faktoren erklären Erfolg?
- **Moran's I (M5):** Räumliche Autokorrelation — wo clustern gute Standorte?
- **k-Means (M6):** Typisierung der 542 PLR in Kiez-Kategorien
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
            marker_color=["#e67e22","#2ecc71","#e74c3c","#3498db","#9b59b6"],
            text=[f"{w}%" for _, w, _ in score_labels_list],
            textposition="outside",
            hovertext=[f"{n}: {d}" for n, _, d in score_labels_list],
            hoverinfo="text",
        ))
        fig_weights.update_layout(
            height=200, margin={"l":0,"r":60,"t":10,"b":0},
            xaxis={"range":[0,105], "showgrid":False, "visible":False},
            yaxis={"autorange":"reversed"},
            plot_bgcolor="white",
            showlegend=False,
        )
        st.plotly_chart(fig_weights, width="stretch")

        st.caption(f"Sozio-Modus: {pw['sozio_mode']} · Gesamtgewichtung normiert auf 100%")

        # ── FOLIE 5–7: TOP-N EMPFEHLUNGEN ────────────────────────────────────
        st.markdown(
            slide_divider(
                "5–7" if topn == 3 else f"5–{4+topn}",
                f"Top-{topn} Standort-Empfehlungen",
                "3:00"
            ),
            unsafe_allow_html=True,
        )

        MEDALS  = ["1.","2.","3.","4.","5.","6.","7.","8.","9.","10."]
        BORDERS = ["#e6a817","#95a5a6","#cd7f32","#3498db","#9b59b6",
                   "#1abc9c","#e74c3c","#2ecc71","#e67e22","#34495e"]

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
                <div style="border:2px solid {bcolor}; border-radius:14px; padding:18px 16px;
                            background:white; box-shadow:0 3px 12px rgba(0,0,0,0.08);
                            font-family:sans-serif;">
                    <div style="font-size:1.3em; font-weight:700; color:{bcolor}; margin-bottom:4px;">
                        {label} {row.plr_name}
                    </div>
                    <div style="margin-bottom:10px;">
                        <span style="font-size:2.2em; font-weight:900; color:{bcolor};">{row.standort_score:.1f}</span>
                        <span style="color:#95a5a6; font-size:0.9em;"> / 100 Punkte</span>
                    </div>
                    <hr style="border:none; border-top:1px solid #ecf0f1; margin:8px 0;">
                    <table style="width:100%; font-size:0.82em; border-collapse:collapse; margin-bottom:6px;">
                        {"".join(
                            f'<tr><td style="padding:2px 0;color:#555;">{lbl}</td>'
                            f'<td style="text-align:right;font-weight:bold;color:#2c3e50;">'
                            f'{getattr(row, sc, 0):.0f}</td></tr>'
                            for sc, lbl in score_col_map.items()
                        )}
                    </table>
                    <hr style="border:none; border-top:1px solid #ecf0f1; margin:8px 0;">
                    <p style="font-size:0.78em; font-weight:700; color:#7f8c8d; margin:4px 0;">
                        Stärkste Dimensionen:
                    </p>
                    <ul style="font-size:0.80em; padding-left:14px; margin:4px 0;
                               color:#2c3e50; list-style:disc;">
                        {reasons_html}
                    </ul>
                    <hr style="border:none; border-top:1px solid #ecf0f1; margin:8px 0;">
                    <table style="width:100%; font-size:0.80em; color:#555;">
                        <tr><td>Einwohner</td><td style="text-align:right;font-weight:bold;">{einw}</td></tr>
                        <tr><td>Einwohner / Laden</td><td style="text-align:right;font-weight:bold;">{epd}</td></tr>
                        <tr><td>Döner im PLR</td><td style="text-align:right;font-weight:bold;">{doener_cnt}</td></tr>
                        <tr><td>Transit-Haltestellen</td><td style="text-align:right;font-weight:bold;">{transit_cnt}</td></tr>
                        <tr><td>Ø Bewertung existierend</td><td style="text-align:right;font-weight:bold;">{avg_rat}</td></tr>
                    </table>
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
                title="", color_scale="RdYlGn", height=480,
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
                "bgcolor":"rgba(255,255,255,0.85)","bordercolor":"#ccc","borderwidth":1,
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
            <div style="background:#f0f7ff; border:1px solid #3498db; border-radius:12px;
                        padding:20px 24px; font-family:sans-serif;">
                <h4 style="margin:0 0 12px; color:#2c3e50;">Demo-Leitfaden (ca. 1 Minute)</h4>
                <ol style="margin:0; padding-left:20px; color:#2c3e50; line-height:1.9;">
                    <li>
                        <b>Scoring Lab</b> — Gewichtungs-Regler live verstellen und zeigen,
                        wie sich Karte und Ranking sofort aktualisieren.
                        Unterschied Nachfrage-fokussiert vs. Marktlücken-fokussiert demonstrieren.
                    </li>
                    <li>
                        <b>Sozio-Modus toggle</b> — Umschalten zwischen Kaufkraft und
                        Kiez im Aufbruch und die Verschiebung in der Karte zeigen.
                    </li>
                    <li>
                        <b>Marktanalyse → Tab Räumliche Cluster</b> — LISA Hot/Cold Spots erklären.
                        Zeigen wo Chancen-Cluster liegen.
                    </li>
                    <li>
                        <b>PLR-Vergleich</b> — zwei der Top-Standorte nebeneinander stellen
                        und Radar-Chart zeigen.
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
                f"""
                Der Standort-Score identifiziert **{top1_name}** als Top-Empfehlung
                mit einem Score von **{top1_score:.1f}/100** unter den gewählten Gewichtungen.
                Nicht jeder Kiez ist gleich gut versorgt — die Daten zeigen klare räumliche
                Muster in Angebot und Nachfrage.
                Die Kombination aus hoher Einwohnerdichte, guter ÖPNV-Anbindung und geringer
                Wettbewerbsdichte kennzeichnet attraktive Standorte konsistent.
                """
            )
        with fc2:
            st.markdown("**Limitierungen & nächste Schritte**")
            st.markdown(
                """
                - Mietpreise pro PLR fehlen (nicht öffentlich auf PLR-Ebene verfügbar)
                - Saisonale Effekte und aktuelle Marktveränderungen nicht erfasst
                - NLP-Basis dünn (Ø ~5 Reviews/Laden)
                - **Nächste Schritte:** Vor-Ort-Analyse der Top-3 PLR,
                  Gewerberaum-Recherche, Gespräch mit Kiez-Netzwerken
                """
            )

        st.markdown("---")
        if st.button("Neue Analyse starten"):
            st.session_state["pitch_ready"] = False
            st.rerun()

# =============================================================================
#  PAGE 1 — Scoring Lab
# =============================================================================
if page == "🎯 Scoring Lab":
    st.title("🎯 Scoring Lab — Standortbewertung")
    st.markdown(
        "Passe die Gewichtungen an und finde die besten Standorte für deinen Döner-Laden."
    )
    st.info(
        "Jeder der 5 Scores liegt auf einer Skala von 0–100. Der **Standort-Score** ist die "
        "gewichtete Summe aller Sub-Scores. Verschiebe die Regler, um deine Prioritäten "
        "widerzuspiegeln — Nachfrage (Bevölkerung, Verkehr) vs. Marktlücke (wenig Konkurrenz) "
        "vs. Infrastruktur (Schulen, Büros, ÖPNV). Ausführliche Erklärungen unter "
        "**Konzepte & Daten**.",
        icon="ℹ️",
    )
    st.markdown("---")

    col_weights, col_map, col_rank = st.columns([1.4, 3, 1.8])

    # ── Left: weights ────────────────────────────────────────────────────────
    with col_weights:
        st.subheader("⚖️ Gewichtung")

        if st.button("↺ Reset", help="Gewichtungen auf Standardwerte zurücksetzen"):
            for key, val in _WEIGHT_DEFAULTS.items():
                st.session_state[key] = val
            st.rerun()

        w_nachfrage    = st.slider("🟠 Nachfrage",     0, 100, step=5, key="w_nachfrage")
        w_marktluecke  = st.slider("🟢 Marktlücke",   0, 100, step=5, key="w_marktluecke")
        w_wettbewerb   = st.slider("🔴 Wettbewerb",   0, 100, step=5, key="w_wettbewerb")
        w_infrastruktur= st.slider("🔵 Infrastruktur",0, 100, step=5, key="w_infrastruktur")
        w_sozio        = st.slider("🟣 Sozio",         0, 100, step=5, key="w_sozio")

        total_w = w_nachfrage + w_marktluecke + w_wettbewerb + w_infrastruktur + w_sozio
        sigma_color = COLOR_SUCCESS if total_w == 100 else "#f39c12"
        st.markdown(
            f"<span style='font-size:1.1em; color:{sigma_color}'>**Σ = {total_w}%**</span>",
            unsafe_allow_html=True,
        )
        if total_w != 100:
            st.caption("💡 Tipp: Σ = 100 % für beste Vergleichbarkeit")

        st.markdown("---")
        sozio_mode = st.radio(
            "Sozio-Modus",
            ["Kaufkraft 💰", "Kiez im Aufbruch 🌱"],
            help="Kaufkraft: Medianeinkommen + MSS-Status  |  Kiez im Aufbruch: Gentrifizierungs-Flag",
        )

        st.markdown("---")
        # Optional kiez_typ filter
        kiez_types = sorted(df_raw["kiez_typ"].dropna().unique().tolist())
        selected_kiez = st.multiselect(
            "Kiez-Typ filtern",
            options=kiez_types,
            default=[],
            help="Leer lassen = alle Typen anzeigen",
        )

    # ── Compute scores ────────────────────────────────────────────────────────
    df_filtered = df_raw.copy()
    if selected_kiez:
        df_filtered = df_filtered[df_filtered["kiez_typ"].isin(selected_kiez)]

    df_scored = compute_scores(
        df_filtered,
        w_nachfrage, w_marktluecke, w_wettbewerb,
        w_infrastruktur, w_sozio, sozio_mode,
    )

    # ── Middle: map ───────────────────────────────────────────────────────────
    with col_map:
        st.subheader("🗺️ Standort-Score Karte")
        if geojson is None:
            st.info("GeoJSON nicht verfügbar — Karte kann nicht angezeigt werden.")
        else:
            fig_map = px.choropleth_map(
                df_scored,
                geojson=geojson,
                locations="plr_id",
                color="standort_score",
                color_continuous_scale="RdYlGn",
                map_style="carto-positron",
                center={"lat": 52.52, "lon": 13.405},
                zoom=9,
                hover_name="plr_name",
                hover_data={
                    "bezirk": True,
                    "standort_score": True,
                    "doener_count": True,
                },
                height=600,
            )
            fig_map.update_layout(
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                coloraxis_colorbar={"title": {"text": "Score"}},
                font_family="sans-serif",
            )
            st.plotly_chart(fig_map, width="stretch")

    # ── Right: ranking + detail ────────────────────────────────────────────────
    with col_rank:
        st.subheader("🏆 Top 15")

        top15 = (
            df_scored.nlargest(15, "standort_score")[
                ["plr_name", "bezirk", "standort_score", "doener_count"]
            ]
            .reset_index(drop=True)
        )

        # Colour-code score column
        def _score_color(val):
            color = COLOR_SUCCESS if val > 50 else COLOR_DANGER
            return f"color: {color}; font-weight: bold"

        st.dataframe(
            top15.rename(
                columns={
                    "plr_name": "PLR",
                    "bezirk": "Bezirk",
                    "standort_score": "Score",
                    "doener_count": "Döner",
                }
            ).style.map(_score_color, subset=["Score"]),
            width='stretch',
            height=360,
        )

        st.markdown("---")
        st.subheader("📍 PLR auswählen")

        plr_names = sorted(df_scored["plr_name"].tolist())
        selected_plr_name = st.selectbox(
            "Planungsraum wählen",
            options=plr_names,
            index=0,
        )

        row = df_scored[df_scored["plr_name"] == selected_plr_name].iloc[0]

        st.markdown(
            f"### {row['plr_name']}\n"
            f"<span style='color:{COLOR_NEUTRAL}'>📍 {row['bezirk']}</span>",
            unsafe_allow_html=True,
        )

        # KPI row 1
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("👥 Einwohner", f"{int(row['einwohner_gesamt']):,}" if pd.notna(row["einwohner_gesamt"]) else "–")
        kpi2.metric("🥙 Döner-Läden", int(row["doener_count"]) if pd.notna(row["doener_count"]) else "–")
        kpi3.metric("⭐ Ø Rating", safe_fmt(row["doener_avg_rating"]) if row["doener_count"] > 0 else "–")

        # KPI row 2
        kpi4, kpi5, kpi6 = st.columns(3)
        kpi4.metric("🚇 ÖPNV", int(row["transit_count"]) if pd.notna(row["transit_count"]) else "–")
        kpi5.metric("💶 Medianeinkommen", f"{int(row['medianeinkommen_eur']):,} €" if pd.notna(row["medianeinkommen_eur"]) else "–")
        kpi6.metric("📊 MSS-Index", safe_fmt(row["mss_status_index"]))

        # Radar chart (5 score dimensions)
        score_dims   = ["s_nachfrage", "s_marktluecke", "s_wettbewerb", "s_infrastruktur", "s_sozio"]
        score_labels = ["Nachfrage", "Marktlücke", "Wettbewerb", "Infrastruktur", "Sozio"]
        score_vals   = [row.get(d, 0) for d in score_dims]

        fig_radar = go.Figure(
            go.Scatterpolar(
                r=score_vals + [score_vals[0]],
                theta=score_labels + [score_labels[0]],
                fill="toself",
                fillcolor="rgba(52,152,219,0.3)",
                line_color=COLOR_NEUTRAL,
                name=row["plr_name"],
            )
        )
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False,
            height=260,
            margin=dict(t=20, b=10, l=20, r=20),
            font_family="sans-serif",
        )
        st.plotly_chart(fig_radar, width='stretch')

        # Badges
        badge_kiez  = row.get("kiez_typ", "–") or "–"
        badge_lisa  = row.get("lisa_cluster", "–") or "–"
        st.markdown(
            f"<span style='background:{COLOR_NEUTRAL};color:white;padding:3px 8px;"
            f"border-radius:4px;font-size:0.85em'>🏘️ {badge_kiez}</span>&nbsp;"
            f"<span style='background:#8e44ad;color:white;padding:3px 8px;"
            f"border-radius:4px;font-size:0.85em'>📐 LISA: {badge_lisa}</span>",
            unsafe_allow_html=True,
        )


# =============================================================================
#  PAGE 2 — Marktanalyse (4 Tabs)
# =============================================================================
elif page == "📊 Marktanalyse":
    st.title("📊 Marktanalyse")
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["🍽️ Marktlücken", "⭐ Qualitätslücken", "🥊 Wettbewerb", "🏗️ Infrastruktur"]
    )

    # ── Tab 1: Marktlücken ──────────────────────────────────────────────────
    with tab1:
        st.subheader("🍽️ Marktlücken — Einwohner pro Döner-Laden")

        avg_epd   = df_raw["einwohner_pro_doener"].median()
        max_epd   = df_raw["einwohner_pro_doener"].max()
        n_ohne    = int((df_raw["doener_count"] == 0).sum())

        m1, m2, m3 = st.columns(3)
        m1.metric("Berlin-Median EW/Döner", f"{avg_epd:,.0f}")
        m2.metric("Maximum EW/Döner", f"{max_epd:,.0f}" if pd.notna(max_epd) else "–")
        m3.metric("PLR ohne Döner-Läden", n_ohne)

        st.markdown("---")
        if geojson:
            df_map1 = df_raw.copy()
            # RdYlGn_r: viele EW pro Döner (grün) = Marktlücke
            fig_ml = choropleth(
                df_map1, geojson, "einwohner_pro_doener",
                color_scale="RdYlGn",
                hover_data={"bezirk": True, "einwohner_pro_doener": True, "doener_count": True},
                height=480,
            )
            fig_ml.update_layout(coloraxis_colorbar={"title": {"text": "EW/Döner"}})
            st.plotly_chart(fig_ml, width='stretch')

        st.markdown("**Top 20 PLR mit dem größten Marktlücken-Potenzial (min. 3.000 Einwohner)**")
        top_gaps = (
            df_raw[df_raw["einwohner_gesamt"] >= 3000]
            .nlargest(20, "einwohner_pro_doener")[
                ["plr_name", "bezirk", "einwohner_gesamt", "doener_count", "einwohner_pro_doener"]
            ]
            .reset_index(drop=True)
        )
        top_gaps.columns = ["PLR", "Bezirk", "Einwohner", "Döner", "EW/Döner"]
        st.dataframe(safe_df(top_gaps), width='stretch')

    # ── Tab 2: Qualitätslücken ──────────────────────────────────────────────
    with tab2:
        st.subheader("⭐ Qualitätslücken — Rating vs. Bewertungsanzahl")

        min_reviews = st.slider(
            "Mindest-Reviews für Darstellung", min_value=1, max_value=200, value=10, step=5
        )

        df_q = df_raw[
            (df_raw["doener_count"] > 0)
            & (df_raw["doener_total_reviews"] >= min_reviews)
        ].copy()

        if df_q.empty:
            st.info("Keine Daten für den gewählten Filter.")
        else:
            med_reviews = df_q["doener_total_reviews"].median()

            fig_scatter = px.scatter(
                df_q,
                x="doener_total_reviews",
                y="doener_avg_rating",
                size="doener_count",
                color="bezirk",
                hover_name="plr_name",
                hover_data={"doener_count": True, "doener_best_rating": True},
                labels={
                    "doener_total_reviews": "Anzahl Reviews (gesamt)",
                    "doener_avg_rating": "Ø Rating",
                    "bezirk": "Bezirk",
                },
                height=520,
            )
            # Quadrant lines
            fig_scatter.add_vline(x=med_reviews, line_dash="dash", line_color="gray", opacity=0.5)
            fig_scatter.add_hline(y=4.0, line_dash="dash", line_color="gray", opacity=0.5)

            # Quadrant annotation – "Goldmine" = viele Reviews, niedriges Rating
            fig_scatter.add_annotation(
                x=df_q["doener_total_reviews"].max() * 0.75,
                y=3.3,
                text="💎 Goldmine<br>(viel Nachfrage, schlechte Qualität)",
                showarrow=False,
                bgcolor="rgba(255,215,0,0.2)",
                bordercolor="gold",
                font=dict(size=11),
            )
            fig_scatter.update_layout(font_family="sans-serif")
            st.plotly_chart(fig_scatter, width='stretch')

    # ── Tab 3: Wettbewerb ───────────────────────────────────────────────────
    with tab3:
        st.subheader("🥊 Wettbewerbs-Analyse")

        # Bar chart per Bezirk
        bezirk_agg = (
            df_raw.groupby("bezirk")
            .agg(doener=("doener_count", "sum"), fastfood=("fastfood_count", "sum"))
            .reset_index()
            .sort_values("doener", ascending=False)
        )

        fig_bar = px.bar(
            bezirk_agg.melt(id_vars="bezirk", value_vars=["doener", "fastfood"],
                            var_name="Kategorie", value_name="Anzahl"),
            x="bezirk",
            y="Anzahl",
            color="Kategorie",
            barmode="group",
            labels={"bezirk": "Bezirk", "Anzahl": "Anzahl Standorte"},
            color_discrete_map={"doener": COLOR_NEUTRAL, "fastfood": COLOR_DANGER},
            height=400,
        )
        fig_bar.update_layout(font_family="sans-serif", xaxis_tickangle=-30)
        st.plotly_chart(fig_bar, width='stretch')

        st.markdown("---")
        col_sc1, col_sc2 = st.columns([2, 1])
        with col_sc1:
            fig_wett = px.scatter(
                df_raw,
                x="fastfood_count",
                y="doener_count",
                color="bezirk",
                hover_name="plr_name",
                labels={"fastfood_count": "Fastfood-Standorte", "doener_count": "Döner-Läden"},
                height=420,
            )
            fig_wett.update_layout(font_family="sans-serif")
            st.plotly_chart(fig_wett, width='stretch')

        with col_sc2:
            n_virgin = int(
                ((df_raw["fastfood_count"] == 0) & (df_raw["doener_count"] == 0)).sum()
            )
            st.metric(
                label="PLR ohne Fastfood & ohne Döner",
                value=n_virgin,
                help="Potenzielle Neumärkte ohne jeglichen direkten Wettbewerb",
            )
            st.markdown(
                f"<br><p style='color:{COLOR_NEUTRAL}'>Diese {n_virgin} Planungsräume haben "
                "weder Döner-Läden noch Fastfood-Konkurrenz — potenzielle Neumärkte.</p>",
                unsafe_allow_html=True,
            )

    # ── Tab 4: Infrastruktur ────────────────────────────────────────────────
    with tab4:
        st.subheader("🏗️ Infrastruktur-Analyse")

        infra_options = {
            "ÖPNV (transit_count)": "transit_count",
            "Universitäten (university_count)": "university_count",
            "Nachtleben (nightlife_count)": "nightlife_count",
            "Büros (office_count)": "office_count",
        }
        infra_sel_label = st.selectbox(
            "Infrastruktur-Metrik für Karte wählen", list(infra_options.keys())
        )
        infra_col = infra_options[infra_sel_label]

        if geojson:
            fig_infra = choropleth(
                df_raw, geojson, infra_col,
                color_scale="Blues",
                hover_data={"bezirk": True, infra_col: True, "doener_count": True},
                height=480,
            )
            st.plotly_chart(fig_infra, width='stretch')

        st.markdown("---")
        st.markdown("**Pearson-Korrelation der Infrastruktur-Metriken mit Ø Rating**")

        infra_cols  = ["transit_count", "university_count", "school_count",
                       "nightlife_count", "office_count", "fastfood_count"]
        target_col  = "doener_avg_rating"
        df_corr_src = df_raw[df_raw["doener_count"] > 0].dropna(subset=[target_col])

        corr_rows = []
        for c in infra_cols:
            if c in df_corr_src.columns:
                r = df_corr_src[[c, target_col]].dropna()
                if len(r) > 5:
                    corr_val = r[c].corr(r[target_col])
                    corr_rows.append({"Metrik": c, "Pearson r": round(corr_val, 3)})

        if corr_rows:
            df_corr = pd.DataFrame(corr_rows).sort_values("Pearson r", ascending=False)
            st.dataframe(safe_df(df_corr), width='stretch')
        else:
            st.info("Nicht genug Daten für Korrelationsberechnung.")


# =============================================================================
#  PAGE 3 — Erfolgs-Profil
# =============================================================================
elif page == "🏅 Erfolgs-Profil":
    st.title("🏅 Erfolgs-Profil — Was macht einen erfolgreichen Döner-Laden aus?")
    st.markdown("---")

    col_ctrl, col_main = st.columns([1, 3])

    with col_ctrl:
        rating_thresh = st.slider(
            "Rating-Schwelle für Erfolg",
            min_value=3.5, max_value=4.8, value=4.3, step=0.1,
            format="%.1f",
        )
        review_thresh = st.slider(
            "Mindest-Reviews für Erfolg",
            min_value=50, max_value=500, value=200, step=25,
        )

    # Compute erfolg_flag dynamically
    df_ef = df_raw.copy()
    df_ef["erfolg_flag"] = (
        (df_ef["doener_avg_rating"] >= rating_thresh)
        & (df_ef["doener_total_reviews"] >= review_thresh)
        & (df_ef["doener_count"] > 0)
    ).astype(int)

    n_erfolg = int(df_ef["erfolg_flag"].sum())
    n_total  = int((df_ef["doener_count"] > 0).sum())
    pct      = (n_erfolg / n_total * 100) if n_total > 0 else 0

    with col_ctrl:
        st.markdown("---")
        st.metric("Erfolgreiche PLR", n_erfolg, help=f"von {n_total} PLR mit Döner-Läden")
        st.metric("Anteil", f"{pct:.1f} %")
        st.caption(
            f"Rating ≥ {rating_thresh:.1f} **und** ≥ {review_thresh} Reviews"
        )

    with col_main:
        # Box plots: erfolg vs. nicht-erfolg for key features
        box_features = {
            "einwohner_dichte": "Einwohnerdichte",
            "transit_count": "ÖPNV-Stationen",
            "medianeinkommen_eur": "Medianeinkommen (€)",
            "nightlife_count": "Nachtleben",
        }

        df_box = df_ef[df_ef["doener_count"] > 0].copy()
        df_box["Gruppe"] = df_box["erfolg_flag"].map({1: "✅ Erfolgreich", 0: "❌ Nicht erfolgreich"})

        fig_box = go.Figure()
        colors = {
            "✅ Erfolgreich": COLOR_SUCCESS,
            "❌ Nicht erfolgreich": COLOR_DANGER,
        }
        for i, (feat_col, feat_label) in enumerate(box_features.items()):
            for gruppe, grp_color in colors.items():
                vals = df_box[df_box["Gruppe"] == gruppe][feat_col].dropna()
                fig_box.add_trace(
                    go.Box(
                        y=vals,
                        name=f"{feat_label} — {gruppe}",
                        boxmean=True,
                        marker_color=grp_color,
                        legendgroup=gruppe,
                        showlegend=(i == 0),
                        x=[feat_label] * len(vals),
                    )
                )
        fig_box.update_layout(
            boxmode="group",
            height=480,
            font_family="sans-serif",
            xaxis_title="Merkmal",
            yaxis_title="Wert",
            legend_title="Gruppe",
        )
        st.plotly_chart(fig_box, width='stretch')

    st.markdown("---")

    # Insight text
    df_succ   = df_ef[df_ef["erfolg_flag"] == 1]
    avg_trans = df_succ["transit_count"].mean() if len(df_succ) > 0 else 0
    avg_inc   = df_succ["medianeinkommen_eur"].mean() if len(df_succ) > 0 else 0

    st.info(
        f"💡  **Insight:** Erfolgreiche Läden stehen in PLR mit Ø **{avg_trans:.0f}** "
        f"ÖPNV-Stationen und einem Median-Einkommen von **{avg_inc:,.0f} €**."
    )

    st.markdown("---")
    img_col1, img_col2 = st.columns(2)

    with img_col1:
        st.markdown("**NLP Radar: Top- vs. Bottom-Läden**")
        try:
            st.image(NLP_IMG, width='stretch')
        except Exception:
            st.caption("_Bild noch nicht verfügbar (nb_04 ausführen)_")

    with img_col2:
        st.markdown("**Regressionskoeffizienten**")
        try:
            st.image(REG_IMG, width='stretch')
        except Exception:
            st.caption("_Bild noch nicht verfügbar (nb_04 ausführen)_")


# =============================================================================
#  PAGE 4 — PLR-Vergleich
# =============================================================================
elif page == "🔍 PLR-Vergleich":
    st.title("🔍 PLR-Vergleich")
    st.markdown("Wähle 2–4 Planungsräume für einen direkten Vergleich.")
    st.markdown("---")

    # Compute default scores for comparison (equal weights)
    df_comp = compute_scores(df_raw, 30, 30, 20, 10, 10, "Kaufkraft 💰")

    plr_options = sorted(df_comp["plr_name"].tolist())
    selected_plrs = st.multiselect(
        "Bis zu 4 PLR auswählen",
        options=plr_options,
        default=[],
        max_selections=4,
    )

    if len(selected_plrs) < 2:
        st.info("ℹ️  Bitte mindestens 2 Planungsräume auswählen, um den Vergleich zu starten.")
    else:
        df_sel = df_comp[df_comp["plr_name"].isin(selected_plrs)].copy()

        # ── Radar chart ────────────────────────────────────────────────────
        score_dims   = ["s_nachfrage", "s_marktluecke", "s_wettbewerb", "s_infrastruktur", "s_sozio"]
        score_labels = ["Nachfrage", "Marktlücke", "Wettbewerb", "Infrastruktur", "Sozio"]
        palette      = [COLOR_NEUTRAL, COLOR_SUCCESS, COLOR_DANGER, "#f39c12"]

        fig_comp = go.Figure()
        for i, (_, row) in enumerate(df_sel.iterrows()):
            vals = [row.get(d, 0) for d in score_dims]
            fig_comp.add_trace(
                go.Scatterpolar(
                    r=vals + [vals[0]],
                    theta=score_labels + [score_labels[0]],
                    fill="toself",
                    name=row["plr_name"],
                    line_color=palette[i % len(palette)],
                    fillcolor=palette[i % len(palette)].replace(")", ",0.15)").replace("rgb", "rgba")
                    if "rgb" in palette[i % len(palette)]
                    else f"rgba(0,0,0,0.07)",
                )
            )
        fig_comp.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            height=480,
            font_family="sans-serif",
            legend=dict(orientation="h", y=-0.15),
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
            "nightlife_count", "kiez_typ", "lisa_cluster",
        ]
        available_cols = [c for c in compare_cols if c in df_sel.columns]
        df_display = df_sel[available_cols].set_index("plr_name").T
        st.dataframe(safe_df(df_display), width='stretch')

        # ── CSV download ─────────────────────────────────────────────────────
        csv_data = df_sel[available_cols].to_csv(index=False, sep=";", decimal=",")
        st.download_button(
            label="⬇️  Vergleich als CSV exportieren",
            data=csv_data,
            file_name="plr_vergleich.csv",
            mime="text/csv",
        )


# =============================================================================
#  PAGE 4b — Konzepte & Daten
# =============================================================================
if page == "📚 Konzepte & Daten":
    st.title("Konzepte & Daten")
    st.markdown(
        "Dieses Blatt erklärt alle Konzepte, Scores und Analysen, die im Dashboard verwendet werden. "
        "Es richtet sich an alle, die verstehen möchten, wie die Ergebnisse zustande kommen."
    )
    st.markdown("---")

    # ── 1. Grundlagen ────────────────────────────────────────────────────────
    with st.expander("Grundlagen: Was sind Planungsräume?", expanded=True):
        st.markdown("""
**Planungsraum (PLR)** ist die kleinste statistische Einheit der Berliner Stadtplanung.
Berlin ist in **542 Planungsräume** unterteilt, die zusammen 12 Bezirke bilden.
Jeder Planungsraum hat im Durchschnitt ca. 7.000 Einwohner und eine Fläche von ca. 3 km².

Wir analysieren auf PLR-Ebene, weil:
- Bevölkerungs-, Einkommens- und Sozialdaten auf dieser Granularität vorliegen
- Planungsräume homogenere Quartiere abbilden als Postleitzahlen oder Bezirke
- Die Google Places Aggregate API exakt auf PLR-Polygonen abgefragt werden kann

Jeder Dönerladen wird über seine GPS-Koordinaten einem Planungsraum zugeordnet (Point-in-Polygon-Verfahren).
Danach werden alle Läden eines PLR zu Durchschnittswerten aggregiert.
        """)

    # ── 2. Die 5 Scores ───────────────────────────────────────────────────────
    with st.expander("Die 5 Scores — Berechnung und Bedeutung", expanded=True):
        st.markdown("""
Alle Scores liegen auf einer Skala von **0 bis 100**. Jede Variable wird zunächst
Min-Max-normiert (0 = schlechtester Wert in Berlin, 100 = bester Wert in Berlin).
Der Gesamtscore ist die gewichtete Summe aller 5 Sub-Scores, wobei die Gewichte
im Scoring Lab frei eingestellt werden können.

---

**Score 1 — Nachfrage** *(Wie viele potenzielle Kunden gibt es hier?)*

| Variable | Richtung | Erklärung |
|---|---|---|
| Einwohnerdichte | + | Mehr Einwohner pro km² = mehr Laufkundschaft |
| Anteil 18–35-Jährige | + | Kernzielgruppe für Döner |
| ÖPNV-Haltestellen | + | Frequentierte Orte ziehen Hunger-Impulskäufe an |
| Nachtleben (Bars, Clubs) | + | Spätabend-Nachfrage nach Döner |
| Büros (corporate + government) | + | Mittagsgeschäft |
| Ø Öffnungsstunden pro Woche | + | Bewährte Stunden = hohe lokale Nachfrage |

---

**Score 2 — Marktlücke** *(Wie unterversorgt ist das Gebiet?)*

| Variable | Richtung | Erklärung |
|---|---|---|
| Einwohner pro Dönerladen | + | Viele Einwohner, wenig Läden = Lücke |
| Gastronomiebetriebe pro km² | − | Wenig Gastro insgesamt = Lücke |

---

**Score 3 — Wettbewerb** *(Niedriger Wettbewerb ist gut)*

| Variable | Richtung | Erklärung |
|---|---|---|
| Wettbewerbs-Index | − | (Döner + Fastfood) / Einwohner × 1.000 |
| Fastfood-Betriebe | − | Direkter Sättigungsgrad |

Score 3 wird invertiert: Ein PLR mit wenig Wettbewerb bekommt eine hohe Punktzahl.

---

**Score 4 — Infrastruktur** *(Lagequalität strukturell)*

| Variable | Richtung | Erklärung |
|---|---|---|
| ÖPNV-Haltestellen | + | Zugänglichkeit |
| Universitäten | + | Studierende als Zielgruppe |
| Schulen | + | Schüler als Mittagszielgruppe |
| Büros | + | Mittagsgeschäft |

---

**Score 5 — Sozio** *(zwei wählbare Modi)*

Der Sozio-Score kann im Scoring Lab zwischen zwei Strategien umgeschaltet werden:

*Modus A — Kaufkraft:*
Geeignet für ein Konzept, das auf kaufkräftigere Kundschaft setzt.
- Medianeinkommen (positiv)
- MSS-Sozialstatus-Index (invers — niedrig = benachteiligt)

*Modus B — Kiez im Aufbruch:*
Geeignet für Lagen, die sich noch entwickeln — günstige Mieten, steigende Nachfrage.
- Gentrification-Flag: MSS-Status niedrig (benachteiligte Lage) UND MSS-Dynamik positiv (Aufwertungstrend)

---

**Gesamtscore — Standort-Score**

`Standort-Score = (w1 × Score1 + w2 × Score2 + w3 × Score3 + w4 × Score4 + w5 × Score5) / Σw`

Die Gewichte w1–w5 sind frei wählbar (0–100 in 5er-Schritten). Standardgewichtung:
Nachfrage 30% · Marktlücke 30% · Wettbewerb 20% · Infrastruktur 10% · Sozio 10%.
        """)

    # ── 3. Analysen M3–M6 ────────────────────────────────────────────────────
    with st.expander("Die vier Analysen (M3–M6)", expanded=False):
        st.markdown("""
Die Analysen laufen in `nb_04_analyse.ipynb` und schreiben ihre Ergebnisse zurück in die Datenbank.

---

**M3 — NLP Sentiment-Analyse**

Google Places liefert zu jedem Laden bis zu 5 Kunden-Reviews.
Wir filtern auf deutsche Reviews und berechnen mit **VADER** (regelbasiertes Sentiment-Tool,
kein Training erforderlich) einen Sentiment-Score pro Review.

Vergleich: Top 10% der Läden (nach Rating) vs. Bottom 10%.
Ergebnis: Radar-Chart mit den Sentiment-Kategorien Preis, Qualität, Service, Hygiene —
sichtbar in der Erfolgs-Profil-Seite des Dashboards.

*Limitierung:* Ø ~5 Reviews pro Laden, geringe Textmenge. Ergebnisse als Tendenz verstehen,
nicht als statistisch belastbare Aussage.

---

**M4 — Logistische Regression (Erfolgs-Analyse)**

Zielvariable: `erfolg_flag` = 1, wenn Rating ≥ 4.3 UND Anzahl Bewertungen ≥ 200.
Das sind die Top-Läden, die sowohl gut bewertet als auch viel frequentiert werden.

Vorgehen:
- Features: alle PLR-Kennzahlen (Einwohner, Infrastruktur, Sozio, Wettbewerb)
- Standardisierung (Z-Score) aller Features
- Logistische Regression mit L2-Regularisierung (verhindert Overfitting)
- 80/20 Train-Test-Split

Ergebnis: Koeffizientenplot — welche Standortfaktoren erhöhen die Wahrscheinlichkeit
eines erfolgreichen Ladens?

---

**M5 — Räumliche Autokorrelation (Moran's I)**

Frage: Sind gute Standorte räumlich geclustert, oder verteilen sie sich zufällig?

Global Moran's I misst, ob ähnliche Werte benachbart liegen (I > 0 = positiv autokorrelliert).
Local Moran's I (LISA) weist jedem PLR einen Cluster-Typ zu:

| Typ | Bedeutung |
|---|---|
| HH (Hot Spot) | Hoher Wert, umgeben von hohen Nachbarn — starkes Cluster |
| LL (Cold Spot) | Niedriger Wert, niedrige Nachbarn — schwaches Cluster |
| HL (Ausreißer) | Hoher Wert, aber niedrige Nachbarn |
| LH (Ausreißer) | Niedriger Wert, aber hohe Nachbarn |

Nachbarschaft: Queen Contiguity (PLR teilt Kante oder Ecke mit Nachbar-PLR).
Berechnet als reine Python-Implementierung ohne libpysal.

---

**M6 — PLR-Typisierung (k-Means Clustering)**

k-Means gruppiert die 542 PLR in Kiez-Typen anhand aller 5 Score-Dimensionen
plus Gastro-Fluktuation und MSS-Dynamik.

Elbow-Methode bestimmt die optimale Clusteranzahl. Typische Cluster:
Studentenviertel, Bürokiez, Wohnquartier, Nachtleben-Kiez, Randgebiet.

Jeder PLR bekommt einen Cluster-Label (`kiez_typ`), der im Dashboard als Filter
in der Marktanalyse und im PLR-Vergleich nutzbar ist.
        """)

    # ── 4. Datenquellen ───────────────────────────────────────────────────────
    with st.expander("Datenquellen und bekannte Grenzen", expanded=False):
        st.markdown("""
**Verwendete Datenquellen**

| Quelle | Datei | Inhalt | Stand |
|---|---|---|---|
| Google Places Text Search API | `dataset_berlin_doener_clean.csv` | 1.346 Dönerläden mit Koordinaten, Rating, Öffnungszeiten, Reviews | 2024 |
| Google Places Aggregate API | `lor_infrastruktur.csv` | Infrastruktur-Counts pro PLR-Polygon (ÖPNV, Uni, Schule, Nachtleben, Büro, Fastfood) | 2024 |
| ODIS Berlin (LOR Geodaten) | `lor_planungsraeume_2021.geojson` | 542 PLR-Polygone (EPSG:25833) | seit 2021 |
| Amt für Statistik Berlin | `lor_bevoelkerungs-daten_2024.csv` | Einwohner nach Alter pro PLR | 31.12.2024 |
| Senatsverwaltung Berlin | `lor_Medianeinkommen_31-12-2023.xlsx` | Medianeinkommen pro PLR | 31.12.2023 |
| Monitoring Soziale Stadtentwicklung (MSS) | `lor_monitoring_soziale-stadtentwicklung_2023.xlsx` | Sozialstatus- und Dynamik-Index pro PLR | 2023 |
| IHK Berlin Open Data | `lor_IHKBerlin_Gewerbedaten.csv` | Aktive Gewerbebetriebe mit NACE-Code pro PLR | 2024 |

---

**Bekannte Grenzen und Einschränkungen**

- **Migrationsdaten fehlen:** Die einzigen verfügbaren PLR-Migrationsdaten stammen aus 2020
  und nutzen das alte LOR-System (447 PLR, nicht mappbar auf 542 PLR) — entfällt daher aus dem Modell.

- **IHK enthält keine Schließungen:** Die Fluktuation wird als Proxy berechnet
  (Gastro-Betriebe ≤ 2 Jahre alt). Tatsächliche Schließungsraten sind nicht verfügbar.

- **Fastfood-Tag unvollständig:** Döner-Läden sind in Google Places teils als
  `turkish_restaurant`, teils als `fast_food_restaurant` getaggt. Der `fastfood_count`
  aus der Aggregate API kann Döner-Läden selbst mitzählen — bekannte Unschärfe.

- **Reviews dünn:** Ø ~5 Reviews pro Laden. NLP-Ergebnisse sind als Tendenz zu verstehen.

- **Kein Mietpreis:** Mietpreise pro PLR sind nicht öffentlich auf PLR-Ebene verfügbar —
  ein wichtiger Faktor für tatsächliche Standortentscheidungen fehlt.

- **Statischer Schnappschuss:** Alle Daten spiegeln den Stand 2023/2024 wider.
  Saisonale Effekte und aktuelle Marktveränderungen sind nicht erfasst.
        """)

    st.markdown("---")
    st.caption(
        "Alle Berechnungen in Python (Streamlit, Pandas, Plotly). "
        "Datenbank: SQLite (`berlin_masterdata.db`). "
        "Koordinaten-Projektion: UTM Zone 33N (EPSG:25833) → WGS84, reine Python-Implementierung."
    )


# =============================================================================
#  PAGE 5 — Methodik
# =============================================================================
elif page == "📖 Methodik":
    st.title("📖 Methodik & Dokumentation")
    st.markdown("---")

    # ── Datenquellen ──────────────────────────────────────────────────────────
    st.subheader("📦 Datenquellen")
    data_sources = pd.DataFrame(
        [
            ["Google Places API", "Döner-Laden-Standorte + Bewertungen", "PLR (542)", "2024"],
            ["Google Places API", "Infrastruktur (ÖPNV, Uni, Schule, …)", "PLR (542)", "2024"],
            ["Amt f. Statistik Berlin-Brandenburg", "Einwohnerzahlen nach Alter", "PLR (542)", "2024"],
            ["Senatsverwaltung — MSS", "Sozialstruktur-Index (MSS)", "PLR (542)", "2023"],
            ["IHK Berlin", "Gewerbedaten (Gastro-Neugründungen)", "PLR (542)", "2023"],
            ["Senatsverwaltung — Stadtentwicklung", "LOR-Planungsraumgrenzen (GeoJSON)", "PLR (542)", "2021"],
            ["Senatsverwaltung — Finanzen", "Medianeinkommen je PLR", "PLR (542)", "2023"],
        ],
        columns=["Quelle", "Inhalt", "Granularität", "Stand"],
    )
    st.dataframe(safe_df(data_sources), width='stretch')

    st.markdown("---")

    # ── Score-Formel ───────────────────────────────────────────────────────────
    st.subheader("🧮 Score-Formeln")

    st.markdown("**Normierungs-Funktion** (min-max, 0–1):")
    st.latex(r"\text{norm}(x) = \frac{x - x_{\min}}{x_{\max} - x_{\min}}")

    st.markdown("**Score 1 — Nachfrage:**")
    st.latex(
        r"S_{\text{Nachfrage}} = \frac{"
        r"\text{norm}(\rho_E) + \text{norm}(A_{18-35}) + \text{norm}(T) + "
        r"\text{norm}(N) + \text{norm}(O) + \text{norm}(H)"
        r"}{6} \times 100"
    )
    st.caption(r"ρ_E = Einwohnerdichte, A = Anteil 18–35, T = ÖPNV, N = Nachtleben, O = Büros, H = Öffnungszeit Döner")

    st.markdown("**Score 2 — Marktlücke:**")
    st.latex(
        r"S_{\text{Marktlücke}} = \frac{"
        r"\text{norm}(EW/D) + (1 - \text{norm}(G_d))"
        r"}{2} \times 100"
    )
    st.caption("EW/D = Einwohner pro Döner, G_d = Gastro-Dichte")

    st.markdown("**Score 3 — Wettbewerb** (niedrig = gut):")
    st.latex(
        r"S_{\text{Wettbewerb}} = \left(1 - \frac{"
        r"\text{norm}(W) + \text{norm}(F)"
        r"}{2}\right) \times 100"
    )
    st.caption("W = Wettbewerbs-Index, F = Fastfood-Count")

    st.markdown("**Score 4 — Infrastruktur:**")
    st.latex(
        r"S_{\text{Infra}} = \frac{"
        r"\text{norm}(T) + \text{norm}(U) + \text{norm}(S) + \text{norm}(O)"
        r"}{4} \times 100"
    )
    st.caption("T = ÖPNV, U = Uni, S = Schule, O = Büros")

    st.markdown("**Score 5 — Sozio (Kaufkraft-Modus):**")
    st.latex(
        r"S_{\text{Sozio}} = \frac{"
        r"\text{norm}(I) + (1 - \text{norm}(MSS))"
        r"}{2} \times 100"
    )
    st.caption("I = Medianeinkommen, MSS = Sozialstruktur-Status-Index")

    st.markdown("**Gesamt-Score:**")
    st.latex(
        r"\text{Score} = \frac{"
        r"w_1 S_1 + w_2 S_2 + w_3 S_3 + w_4 S_4 + w_5 S_5"
        r"}{\sum w_i}"
    )

    st.markdown("---")

    # ── Methodik ───────────────────────────────────────────────────────────────
    st.subheader("🔬 Methodik")

    st.markdown(
        """
| Schritt | Beschreibung |
|---------|--------------|
| **M3** | Zusammenführung aller Rohdaten auf PLR-Ebene (nb_03_merge-masterdata) |
| **M4** | Explorative Datenanalyse, Ausreißer-Behandlung, Feature Engineering |
| **M5** | Räumliche Autokorrelation (Moran's I / LISA-Cluster) für Döner-Dichte |
| **M6** | Regressionsanalyse & NLP-Auswertung von Review-Texten zur Erfolgsbestimmung |
"""
    )

    st.markdown("---")

    # ── Limitierungen ─────────────────────────────────────────────────────────
    st.subheader("⚠️ Bekannte Limitierungen")

    st.markdown(
        """
- **Fastfood-Tag unvollständig:** Google Places klassifiziert nicht alle Fastfood-Betriebe konsistent.
- **Migrationsdaten 2020:** Die aktuellsten verfügbaren Bevölkerungsdaten stammen teilweise aus 2020.
- **Döner-Definition:** Es wurden Betriebe mit dem Label „Döner" oder „Kebab" erfasst — atypische Betriebe können fehlen.
- **Statische Infrastruktur:** ÖPNV- und Schuldaten können veraltet sein (kein Live-Update).
- **Keine Mietdaten:** Standortkosten (Miete) sind nicht im Score enthalten.
- **Gentrification-Flag:** Binäre Klassifikation basierend auf MSS-Dynamik; keine kontinuierliche Messung.
- **GeoJSON EPSG:25833:** Koordinaten-Konvertierung erfolgt numerisch (ohne PROJ); minimale Rundungsfehler möglich.
"""
    )

    st.markdown("---")
    st.caption(
        "Erstellt im Rahmen des BI-Projekts · Studium · FU Berlin · 2024/2025  "
        "·  Daten: Google Places API, Senatsverwaltung Berlin, IHK Berlin"
    )
