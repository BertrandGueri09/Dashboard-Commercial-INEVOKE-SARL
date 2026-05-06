
"""
INEVOKE SARL — Dashboard Commercial Automatique
Dashboard Streamlit connecté à KoboToolbox.

Objectifs :
- 0 donnée initiale
- Mise à jour automatique depuis Kobo
- KPIs, graphiques, carte Côte d’Ivoire
- Couleurs et logo INEVOKE
"""

import os
import base64
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None


# ============================================================
# CONFIGURATION STREAMLIT
# ============================================================

st.set_page_config(
    page_title="INEVOKE — Dashboard Commercial",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

BLUE = "#2196F3"
ORANGE = "#F9A825"
NAVY = "#0D47A1"
LIGHT = "#E3F2FD"
GREEN = "#2E7D32"
RED = "#C62828"
DARK = "#1A1A2E"
GRAY = "#F5F7FA"

PALETTE = [BLUE, ORANGE, "#26C6DA", "#66BB6A", "#AB47BC", "#EF5350", "#26A69A"]

KOBO_FORM_LINK = "https://ee.kobotoolbox.org/x/EIygoDnx"

# IMPORTANT :
# Mets ces valeurs dans .streamlit/secrets.toml en production.
KOBO_API_URL = st.secrets.get("KOBO_API_URL", "https://kf.kobotoolbox.org")
KOBO_ASSET_UID = st.secrets.get("KOBO_ASSET_UID", "")
KOBO_API_TOKEN = st.secrets.get("KOBO_API_TOKEN", "")


# ============================================================
# STYLE
# ============================================================

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Barlow', sans-serif;
}}

.main-header {{
    background: linear-gradient(135deg, {NAVY} 0%, {BLUE} 100%);
    padding: 22px 28px;
    border-radius: 16px;
    margin-bottom: 1.4rem;
    display: flex;
    align-items: center;
    gap: 20px;
    box-shadow: 0 6px 24px rgba(33,150,243,.25);
}}

.main-header h1 {{
    color: white;
    font-size: 28px;
    font-weight: 700;
    margin: 0;
}}

.main-header p {{
    color: rgba(255,255,255,.85);
    font-size: 14px;
    margin: 4px 0 0;
}}

.kpi-card {{
    background: white;
    border-radius: 14px;
    padding: 18px 18px;
    border-top: 5px solid {BLUE};
    box-shadow: 0 2px 14px rgba(0,0,0,.08);
    text-align: center;
    min-height: 112px;
}}

.kpi-card.orange {{ border-top-color: {ORANGE}; }}
.kpi-card.green {{ border-top-color: {GREEN}; }}
.kpi-card.red {{ border-top-color: {RED}; }}
.kpi-card.navy {{ border-top-color: {NAVY}; }}

.kpi-label {{
    font-size: 11px;
    color: #666;
    text-transform: uppercase;
    letter-spacing: .08em;
    font-weight: 600;
}}

.kpi-value {{
    font-size: 28px;
    color: {NAVY};
    font-weight: 800;
    margin-top: 8px;
}}

.section-title {{
    font-size: 17px;
    font-weight: 800;
    color: {NAVY};
    border-left: 5px solid {ORANGE};
    padding-left: 12px;
    margin: 1rem 0 .8rem;
}}

.alert-box {{
    background: {LIGHT};
    border-left: 5px solid {BLUE};
    border-radius: 10px;
    padding: 14px 18px;
    color: {NAVY};
    font-size: 14px;
    margin-bottom: 1rem;
}}

.empty-box {{
    background: white;
    border: 2px dashed {BLUE};
    border-radius: 14px;
    padding: 28px;
    color: {NAVY};
    text-align: center;
    margin-top: 1rem;
}}

section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {NAVY} 0%, #1565C0 100%);
}}

section[data-testid="stSidebar"] * {{
    color: white !important;
}}

.stDownloadButton > button {{
    background: {ORANGE};
    color: {DARK};
    border: none;
    border-radius: 8px;
    font-weight: 700;
}}

.stButton > button {{
    background: {BLUE};
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 700;
}}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# OUTILS
# ============================================================

def image_to_base64(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def empty_dataframe() -> pd.DataFrame:
    cols = [
        "date_collecte", "nom_client", "secteur", "offre", "ville", "montant",
        "statut", "source", "probabilite", "date_entree", "date_signature",
        "responsable", "prochaine_action", "date_prochaine_action", "observations",
        "latitude", "longitude"
    ]
    return pd.DataFrame(columns=cols)


def normalize_kobo_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise les noms de colonnes Kobo/XLSForm vers les noms utilisés dans le dashboard."""
    if df is None or len(df) == 0:
        return empty_dataframe()

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    mapping = {
        "Date de collecte": "date_collecte",
        "date_collecte": "date_collecte",
        "Nom du client": "nom_client",
        "nom_client": "nom_client",
        "Secteur": "secteur",
        "secteur": "secteur",
        "Offre proposée": "offre",
        "offre": "offre",
        "Ville": "ville",
        "ville": "ville",
        "Montant de l’offre (FCFA)": "montant",
        "Montant de l'offre (FCFA)": "montant",
        "montant": "montant",
        "Statut": "statut",
        "statut": "statut",
        "Source du client": "source",
        "source": "source",
        "Probabilité de signature (%)": "probabilite",
        "probabilite": "probabilite",
        "Date d’entrée dans le pipeline": "date_entree",
        "Date d'entree dans le pipeline": "date_entree",
        "date_entree": "date_entree",
        "Date de signature": "date_signature",
        "date_signature": "date_signature",
        "Responsable commercial": "responsable",
        "responsable": "responsable",
        "Prochaine action": "prochaine_action",
        "prochaine_action": "prochaine_action",
        "Date prochaine action": "date_prochaine_action",
        "date_prochaine_action": "date_prochaine_action",
        "Observations": "observations",
        "observations": "observations",
        "_submission_time": "date_soumission",
        "_geolocation": "geolocation",
    }

    df = df.rename(columns={c: mapping.get(c, c) for c in df.columns})

    for col in empty_dataframe().columns:
        if col not in df.columns:
            df[col] = np.nan

    # Gestion géolocalisation Kobo : _geolocation = [lat, lon]
    if "geolocation" in df.columns:
        def get_lat(x):
            if isinstance(x, list) and len(x) >= 2:
                return x[0]
            return np.nan

        def get_lon(x):
            if isinstance(x, list) and len(x) >= 2:
                return x[1]
            return np.nan

        df["latitude"] = df["geolocation"].apply(get_lat)
        df["longitude"] = df["geolocation"].apply(get_lon)

    # Dates
    for col in ["date_collecte", "date_entree", "date_signature", "date_prochaine_action"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Montants et probabilité
    df["montant"] = pd.to_numeric(df["montant"], errors="coerce").fillna(0)

    df["probabilite"] = (
        df["probabilite"]
        .astype(str)
        .str.replace("%", "", regex=False)
        .str.strip()
    )
    df["probabilite"] = pd.to_numeric(df["probabilite"], errors="coerce").fillna(0)

    # Textes
    for col in ["nom_client", "secteur", "offre", "ville", "statut", "source", "responsable", "prochaine_action", "observations"]:
        df[col] = df[col].fillna("").astype(str)

    df["annee"] = df["date_collecte"].dt.year
    df["mois"] = df["date_collecte"].dt.month
    df["mois_label"] = df["date_collecte"].dt.strftime("%Y-%m")
    df["semaine"] = df["date_collecte"].dt.isocalendar().week.astype("Int64")
    df["valeur_ponderee"] = df["montant"] * df["probabilite"] / 100

    return df


@st.cache_data(ttl=60, show_spinner=False)
def fetch_kobo_data(api_url: str, asset_uid: str, token: str) -> pd.DataFrame:
    """Récupère automatiquement les soumissions Kobo via API."""
    if not asset_uid or not token:
        return empty_dataframe()

    url = f"{api_url.rstrip('/')}/api/v2/assets/{asset_uid}/data.json"
    headers = {"Authorization": f"Token {token}"}

    rows = []
    next_url = url

    try:
        while next_url:
            response = requests.get(next_url, headers=headers, timeout=30)
            response.raise_for_status()
            payload = response.json()

            results = payload.get("results", [])
            rows.extend(results)

            next_url = payload.get("next")
            if next_url and next_url.startswith("/"):
                next_url = api_url.rstrip("/") + next_url

        return normalize_kobo_columns(pd.DataFrame(rows))

    except Exception as e:
        st.error(f"Erreur de connexion à Kobo : {e}")
        return empty_dataframe()


def format_fcfa(value):
    try:
        value = float(value)
    except Exception:
        value = 0

    if abs(value) >= 1_000_000:
        return f"{value/1_000_000:,.1f} M"
    return f"{value:,.0f}"


def kpi_card(label, value, color_class="blue"):
    st.markdown(
        f"""
        <div class="kpi-card {color_class}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def safe_value_counts(df, col):
    if len(df) == 0 or col not in df.columns:
        return pd.DataFrame({col: [], "count": []})
    out = df[col].replace("", "Non renseigné").value_counts().reset_index()
    out.columns = [col, "count"]
    return out


# ============================================================
# AUTO REFRESH
# ============================================================

with st.sidebar:
    st.markdown("### 🔄 Actualisation automatique")
    refresh_seconds = st.selectbox(
        "Fréquence",
        [30, 60, 120, 300],
        index=1,
        format_func=lambda x: f"Toutes les {x} secondes"
    )

if st_autorefresh is not None:
    st_autorefresh(interval=refresh_seconds * 1000, key="kobo_auto_refresh")


# ============================================================
# HEADER
# ============================================================

logo_b64 = image_to_base64("assets/logo_inevoke.jpeg")
logo_html = (
    f'<img src="data:image/jpeg;base64,{logo_b64}" style="height:70px;background:white;border-radius:10px;padding:6px;">'
    if logo_b64 else "☀️"
)

st.markdown(
    f"""
<div class="main-header">
    <div>{logo_html}</div>
    <div>
        <h1>Dashboard Commercial — INEVOKE SARL</h1>
        <p>Suivi automatique des soumissions Kobo · Pipeline · Commerciaux · Carte Côte d’Ivoire</p>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# CHARGEMENT DES DONNÉES
# ============================================================

with st.sidebar:
    st.markdown("---")
    st.markdown("### 🔗 Formulaire Kobo")
    st.markdown(f"[Ouvrir le formulaire Kobo]({KOBO_FORM_LINK})")
    st.caption("Le dashboard lit les soumissions via l’API Kobo.")

    if st.button("Forcer l’actualisation maintenant"):
        st.cache_data.clear()
        st.rerun()

df_all = fetch_kobo_data(KOBO_API_URL, KOBO_ASSET_UID, KOBO_API_TOKEN)


# ============================================================
# FILTRES
# ============================================================

with st.sidebar:
    st.markdown("---")
    st.markdown("### 🔍 Filtres")

    df = df_all.copy()

    if len(df_all) > 0 and df_all["date_collecte"].notna().any():
        date_min = df_all["date_collecte"].min().date()
        date_max = df_all["date_collecte"].max().date()
        date_range = st.date_input(
            "Période",
            value=(date_min, date_max),
            min_value=date_min,
            max_value=date_max,
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            df = df[
                (df["date_collecte"].dt.date >= start_date) &
                (df["date_collecte"].dt.date <= end_date)
            ]
    else:
        st.caption("Aucune date disponible pour filtrer.")

    commerciaux = ["Tous"] + sorted([x for x in df_all["responsable"].dropna().unique().tolist() if x])
    commercial = st.selectbox("Commercial", commerciaux)
    if commercial != "Tous":
        df = df[df["responsable"] == commercial]

    statuts = ["Tous"] + sorted([x for x in df_all["statut"].dropna().unique().tolist() if x])
    statut = st.selectbox("Statut", statuts)
    if statut != "Tous":
        df = df[df["statut"] == statut]

    offres = ["Toutes"] + sorted([x for x in df_all["offre"].dropna().unique().tolist() if x])
    offre = st.selectbox("Offre", offres)
    if offre != "Toutes":
        df = df[df["offre"] == offre]


# ============================================================
# KPIS
# ============================================================

if len(df) == 0:
    total_leads = nb_signes = nb_perdus = 0
    ca_signe = pipeline = valeur_ponderee = montant_moyen = taux_conversion = 0
    nego_count = prospects_count = 0
else:
    status_lower = df["statut"].str.lower()
    signes = df[status_lower.isin(["signé", "signe"])]
    perdus = df[status_lower == "perdu"]
    nego = df[status_lower.str.contains("négo|nego", regex=True, na=False)]
    prospects = df[status_lower == "prospect"]

    total_leads = len(df)
    nb_signes = len(signes)
    nb_perdus = len(perdus)
    ca_signe = signes["montant"].sum()
    pipeline = df[status_lower.isin(["prospect", "négociation", "negociation", "en attente"])]["montant"].sum()
    valeur_ponderee = df["valeur_ponderee"].sum()
    taux_conversion = nb_signes / max(total_leads, 1) * 100
    montant_moyen = signes["montant"].mean() if nb_signes else 0
    nego_count = len(nego)
    prospects_count = len(prospects)

st.markdown(
    f"""
<div class="alert-box">
    <b>Mode automatique Kobo :</b> les données se mettent à jour toutes les {refresh_seconds} secondes.
    <br><b>Dernière actualisation :</b> {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
    <br><b>Nombre de soumissions reçues :</b> {len(df_all)}
</div>
""",
    unsafe_allow_html=True,
)

if not KOBO_ASSET_UID or not KOBO_API_TOKEN:
    st.warning(
        "Connexion Kobo non configurée. Ajoute KOBO_ASSET_UID et KOBO_API_TOKEN "
        "dans le fichier .streamlit/secrets.toml pour activer la mise à jour automatique."
    )

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1: kpi_card("Leads total", total_leads, "blue")
with c2: kpi_card("Signés", nb_signes, "green")
with c3: kpi_card("Perdus", nb_perdus, "red")
with c4: kpi_card("Taux conversion", f"{taux_conversion:.1f}%", "orange")
with c5: kpi_card("CA signé", f"{format_fcfa(ca_signe)} FCFA", "navy")
with c6: kpi_card("Pipeline", f"{format_fcfa(pipeline)} FCFA", "blue")

st.markdown("<br>", unsafe_allow_html=True)

c7, c8, c9, c10 = st.columns(4)
with c7: kpi_card("Valeur pondérée", f"{format_fcfa(valeur_ponderee)} FCFA", "orange")
with c8: kpi_card("Montant moyen signé", f"{format_fcfa(montant_moyen)} FCFA", "navy")
with c9: kpi_card("En négociation", nego_count, "blue")
with c10: kpi_card("Prospects", prospects_count, "green")


# ============================================================
# SI AUCUNE DONNÉE
# ============================================================

if len(df) == 0:
    st.markdown(
        """
<div class="empty-box">
    <h3>Aucune donnée commerciale pour le moment</h3>
    <p>Le dashboard est initialisé à zéro. Dès qu’un formulaire Kobo est soumis et que l’API est configurée,
    les indicateurs se mettront à jour automatiquement.</p>
</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# TABS
# ============================================================

tabs = st.tabs([
    "Vue d’ensemble",
    "Pipeline & conversion",
    "Commerciaux",
    "Carte Côte d’Ivoire",
    "Données",
])

with tabs[0]:
    st.markdown("<div class='section-title'>Vue d’ensemble commerciale</div>", unsafe_allow_html=True)

    col1, col2 = st.columns([1.4, 1])

    with col1:
        if len(df) > 0:
            evo = df.dropna(subset=["date_collecte"]).groupby("mois_label").agg(
                leads=("nom_client", "count"),
                ca_signe=("montant", lambda x: x[df.loc[x.index, "statut"].str.lower().isin(["signé", "signe"])].sum()),
            ).reset_index()

            fig = go.Figure()
            fig.add_trace(go.Bar(x=evo["mois_label"], y=evo["leads"], name="Leads", marker_color=BLUE))
            fig.add_trace(go.Scatter(
                x=evo["mois_label"],
                y=evo["ca_signe"]/1_000_000,
                name="CA signé (M FCFA)",
                mode="lines+markers",
                line=dict(color=ORANGE, width=3),
                yaxis="y2"
            ))
            fig.update_layout(
                height=360,
                plot_bgcolor="grey",
                paper_bgcolor="black",
                legend=dict(orientation="h"),
                yaxis=dict(title="Nombre de leads"),
                yaxis2=dict(title="M FCFA", overlaying="y", side="right", showgrid=False),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune évolution à afficher pour le moment.")

    with col2:
        if len(df) > 0:
            stat = safe_value_counts(df, "statut")
            fig = px.pie(stat, values="count", names="statut", hole=.45, color_discrete_sequence=PALETTE)
            fig.update_layout(height=360, paper_bgcolor="black")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune répartition par statut pour le moment.")

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("<div class='section-title'>Montant par offre</div>", unsafe_allow_html=True)
        if len(df) > 0:
            offre_df = df.groupby("offre").agg(montant=("montant", "sum"), leads=("nom_client", "count")).reset_index().sort_values("montant")
            fig = px.bar(offre_df, x="montant", y="offre", orientation="h", text=offre_df["montant"].apply(lambda x: f"{x/1e6:.1f}M"), color_discrete_sequence=[BLUE])
            fig.update_traces(textposition="outside")
            fig.update_layout(height=330, plot_bgcolor="grey", paper_bgcolor="black")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune offre à afficher.")

    with col4:
        st.markdown("<div class='section-title'>Leads par source</div>", unsafe_allow_html=True)
        if len(df) > 0:
            src = safe_value_counts(df, "source")
            fig = px.bar(src, x="count", y="source", orientation="h", color_discrete_sequence=[ORANGE])
            fig.update_layout(height=330, plot_bgcolor="grey", paper_bgcolor="black")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune source à afficher.")


with tabs[1]:
    st.markdown("<div class='section-title'>Pipeline & conversion</div>", unsafe_allow_html=True)

    funnel = pd.DataFrame({
        "Étape": ["Leads total", "Prospects", "Négociation", "Signés"],
        "Valeur": [total_leads, prospects_count, nego_count, nb_signes],
    })

    fig = go.Figure(go.Funnel(
        y=funnel["Étape"],
        x=funnel["Valeur"],
        textinfo="value+percent initial",
        marker=dict(color=[BLUE, "#26C6DA", ORANGE, GREEN]),
    ))
    fig.update_layout(height=360, paper_bgcolor="black")
    st.plotly_chart(fig, use_container_width=True)

    if len(df) > 0:
        active = df[df["statut"].str.lower().isin(["prospect", "négociation", "negociation", "en attente"])]
        if len(active) > 0:
            fig = px.scatter(
                active,
                x="probabilite",
                y="montant",
                color="offre",
                size="montant",
                hover_name="nom_client",
                hover_data=["ville", "responsable", "statut"],
                color_discrete_sequence=PALETTE,
            )
            fig.update_layout(height=380, plot_bgcolor="grey", paper_bgcolor="black")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucun élément actif dans le pipeline.")


with tabs[2]:
    st.markdown("<div class='section-title'>Performance par commercial</div>", unsafe_allow_html=True)

    if len(df) > 0:
        perf = df.groupby("responsable").agg(
            leads=("nom_client", "count"),
            signes=("statut", lambda x: x.str.lower().isin(["signé", "signe"]).sum()),
            perdus=("statut", lambda x: (x.str.lower() == "perdu").sum()),
            ca=("montant", lambda x: x[df.loc[x.index, "statut"].str.lower().isin(["signé", "signe"])].sum()),
            pipeline=("montant", lambda x: x[df.loc[x.index, "statut"].str.lower().isin(["prospect", "négociation", "negociation", "en attente"])].sum()),
        ).reset_index()

        perf["taux_conversion"] = perf["signes"] / perf["leads"].clip(lower=1) * 100
        perf["ca_M"] = perf["ca"] / 1_000_000
        perf["pipeline_M"] = perf["pipeline"] / 1_000_000
        perf = perf.sort_values("ca", ascending=False)

        st.dataframe(perf, use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(perf, x="responsable", y="ca_M", color_discrete_sequence=[BLUE], text=perf["ca_M"].apply(lambda x: f"{x:.1f}M"))
            fig.update_traces(textposition="outside")
            fig.update_layout(title="CA signé par commercial", height=360, plot_bgcolor="grey", paper_bgcolor="black")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(perf, x="responsable", y="taux_conversion", color_discrete_sequence=[ORANGE], text=perf["taux_conversion"].apply(lambda x: f"{x:.1f}%"))
            fig.add_hline(y=30, line_dash="dash", line_color=RED, annotation_text="Objectif 30%")
            fig.update_traces(textposition="outside")
            fig.update_layout(title="Taux conversion par commercial", height=360, plot_bgcolor="grey", paper_bgcolor="black")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune performance commerciale à afficher pour le moment.")


with tabs[3]:
    st.markdown("<div class='section-title'>Carte commerciale — Côte d’Ivoire</div>", unsafe_allow_html=True)

    coords = pd.DataFrame([
        {"ville": "Abidjan", "lat": 5.3599517, "lon": -4.0082563},
        {"ville": "Bouaké", "lat": 7.6906, "lon": -5.0391},
        {"ville": "Yamoussoukro", "lat": 6.8276, "lon": -5.2893},
        {"ville": "San-Pédro", "lat": 4.7485, "lon": -6.6363},
        {"ville": "Daloa", "lat": 6.8774, "lon": -6.4502},
        {"ville": "Korhogo", "lat": 9.4578, "lon": -5.6296},
        {"ville": "Divo", "lat": 5.8390, "lon": -5.3570},
        {"ville": "Gagnoa", "lat": 6.1319, "lon": -5.9506},
        {"ville": "Man", "lat": 7.4125, "lon": -7.5538},
        {"ville": "Abengourou", "lat": 6.7297, "lon": -3.4964},
        {"ville": "Bondoukou", "lat": 8.0402, "lon": -2.8000},
        {"ville": "Odienné", "lat": 9.5104, "lon": -7.5692},
        {"ville": "Séguéla", "lat": 7.9611, "lon": -6.6731},
    ])

    if len(df) > 0:
        map_df = df.groupby("ville").agg(
            leads=("nom_client", "count"),
            montant=("montant", "sum"),
            signes=("statut", lambda x: x.str.lower().isin(["signé", "signe"]).sum()),
        ).reset_index()

        map_df["ville_clean"] = map_df["ville"].str.strip().str.lower()
        coords["ville_clean"] = coords["ville"].str.strip().str.lower()

        map_df = map_df.merge(coords[["ville_clean", "lat", "lon"]], on="ville_clean", how="left")
        map_df = map_df.dropna(subset=["lat", "lon"])

        if len(map_df) > 0:
            fig = px.scatter_mapbox(
                map_df,
                lat="lat",
                lon="lon",
                size="leads",
                color="montant",
                hover_name="ville",
                hover_data={"leads": True, "signes": True, "montant": ":,.0f"},
                zoom=5.7,
                height=620,
                color_continuous_scale=[[0, LIGHT], [.5, ORANGE], [1, BLUE]],
                size_max=46,
            )

            fig.update_layout(
                mapbox_style="open-street-map",
                mapbox_center={"lat": 7.54, "lon": -5.55},
                margin=dict(l=0, r=0, t=0, b=0),
                paper_bgcolor="black",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune ville reconnue pour la carte.")
    else:
        st.info("La carte sera affichée dès qu’il y aura des données.")


with tabs[4]:
    st.markdown("<div class='section-title'>Données commerciales</div>", unsafe_allow_html=True)

    st.dataframe(df, use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 Télécharger les données filtrées en CSV",
        data=csv,
        file_name="donnees_commerciales_inevoke.csv",
        mime="text/csv",
    )


st.markdown("---")
st.caption("INEVOKE SARL — Dashboard commercial automatique ")
