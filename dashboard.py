import re
import requests
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import date

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Idealista A Coruña", layout="wide")


# ── Data ──────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    resp = requests.get(f"{API_URL}/listings", params={"limit": 500}, timeout=10)
    resp.raise_for_status()
    listings = resp.json()["listings"]
    df = pd.DataFrame(listings)
    df["first_seen"] = pd.to_datetime(df["first_seen"])
    df["neighbourhood_label"] = df["neighbourhood"].str.replace("-", " ").str.title()
    df["published_date"] = df.apply(_parse_published, axis=1)
    return df


@st.cache_data(ttl=60)
def load_price_history() -> pd.DataFrame:
    resp = requests.get(f"{API_URL}/price-history", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return pd.DataFrame(columns=["url", "price", "recorded_at", "full_url"])
    return pd.DataFrame(data)


MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

def _parse_published(row) -> date | None:
    s = row.get("published")
    ref = row.get("first_seen")
    if not s or not ref:
        return None
    s = str(s).lower()
    m = re.search(r"(\d+)\s+de\s+(\w+)", s)
    if m:
        day = int(m.group(1))
        month = MONTHS.get(m.group(2))
        if month:
            ref_dt = pd.to_datetime(ref)
            year = ref_dt.year if month <= ref_dt.month else ref_dt.year - 1
            try:
                return date(year, month, day)
            except ValueError:
                pass
    return None


df = load_data()

# ── Sidebar ────────────────────────────────────────────────────────────────────

st.sidebar.title("Filters")

neighbourhoods = sorted(df["neighbourhood_label"].unique())
selected_n = st.sidebar.multiselect("Neighbourhood", neighbourhoods, default=neighbourhoods)

price_min, price_max = int(df["price_num"].min()), int(df["price_num"].max())
price_range = st.sidebar.slider("Price (€)", price_min, price_max, (price_min, price_max), step=5000)

elevator = st.sidebar.checkbox("Elevator only", value=False)
terrace  = st.sidebar.checkbox("Terrace only", value=False)

st.sidebar.divider()
st.sidebar.subheader("Scraper")

if "scraping" not in st.session_state:
    st.session_state.scraping = False

scraper_status = requests.get(f"{API_URL}/scraper/status", timeout=5).json()

if st.session_state.scraping:
    if scraper_status["running"]:
        with st.sidebar.status("Scraper running...", expanded=True) as status:
            log_text = requests.get(f"{API_URL}/scraper/log", timeout=5).text
            st.code(log_text or "Starting...", language=None)
        import time; time.sleep(3); st.rerun()
    else:
        # Just finished
        st.session_state.scraping = False
        st.cache_data.clear()
        last = scraper_status.get("last_run") or {}
        new_n = last.get("new_listings", 0)
        if new_n:
            st.sidebar.success(f"Done! {new_n} new listing(s) found.")
        else:
            st.sidebar.info("Done. No new listings.")
        log_text = requests.get(f"{API_URL}/scraper/log", timeout=5).text
        if log_text.strip():
            with st.sidebar.expander("Run log"):
                st.code(log_text, language=None)
else:
    last = scraper_status.get("last_run")
    if last and last.get("finished_at"):
        new_n = last.get("new_listings", 0)
        st.sidebar.caption(f"Last run: {last['finished_at'][:16]} · {new_n} new listing(s)")
    if st.sidebar.button("Run scraper"):
        r = requests.post(f"{API_URL}/scraper/run", timeout=5)
        if r.status_code == 409:
            st.sidebar.warning("Already running.")
        else:
            st.session_state.scraping = True
            st.rerun()

# ── Filter ────────────────────────────────────────────────────────────────────

fdf = df[df["neighbourhood_label"].isin(selected_n)]
fdf = fdf[fdf["price_num"].between(*price_range)]
if elevator: fdf = fdf[fdf["has_elevator"] == True]
if terrace:  fdf = fdf[fdf["has_terrace"]  == True]

# ── Header ────────────────────────────────────────────────────────────────────

st.title("🏠 Idealista — A Coruña")
st.caption(f"Via API · {len(df)} total listings")

# ── Metrics ───────────────────────────────────────────────────────────────────

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Listings",      len(fdf))
c2.metric("Avg price",     f"{fdf['price_num'].mean():,.0f}€".replace(",", ".") if len(fdf) else "—")
c3.metric("Median price",  f"{fdf['price_num'].median():,.0f}€".replace(",", ".") if len(fdf) else "—")
c4.metric("Avg €/m²",      f"{fdf['ppm_num'].mean():,.0f}€".replace(",", ".") if len(fdf) else "—")
c5.metric("With elevator", f"{int(fdf['has_elevator'].sum())}/{len(fdf)}")

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Price distribution")
    fig = px.histogram(fdf, x="price_num", nbins=20,
                       labels={"price_num": "Price (€)"},
                       color_discrete_sequence=["#4C9BE8"])
    fig.update_layout(margin=dict(t=20, b=20), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Avg price by neighbourhood")
    avg_by_n = (fdf.groupby("neighbourhood_label")["price_num"]
                   .mean().reset_index()
                   .sort_values("price_num", ascending=True))
    fig2 = px.bar(avg_by_n, x="price_num", y="neighbourhood_label",
                  orientation="h",
                  labels={"price_num": "Avg price (€)", "neighbourhood_label": ""},
                  color_discrete_sequence=["#4C9BE8"])
    fig2.update_layout(margin=dict(t=20, b=20))
    st.plotly_chart(fig2, use_container_width=True)

# ── Latest per neighbourhood ───────────────────────────────────────────────────

st.subheader("Latest listings by neighbourhood")

n_latest = st.slider("Show last N per neighbourhood", 1, 10, 3)

latest = (
    fdf.dropna(subset=["published_date"])
       .sort_values("published_date", ascending=False)
       .groupby("neighbourhood_label")
       .head(n_latest)
       .sort_values(["neighbourhood_label", "published_date"], ascending=[True, False])
)

latest_display = latest[[
    "neighbourhood_label", "published_date", "title", "price", "price_per_sqm",
    "details", "has_elevator", "has_terrace", "full_url"
]].rename(columns={
    "neighbourhood_label": "neighbourhood",
    "published_date": "published",
    "price_per_sqm": "€/m²",
    "has_elevator": "elevator",
    "has_terrace": "terrace",
    "full_url": "url",
})

st.dataframe(
    latest_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "url":      st.column_config.LinkColumn("url"),
        "elevator": st.column_config.CheckboxColumn(),
        "terrace":  st.column_config.CheckboxColumn(),
    }
)

st.divider()

# ── All listings ───────────────────────────────────────────────────────────────

st.subheader("All listings")

display = fdf[[
    "title", "price", "price_per_sqm", "details",
    "neighbourhood_label", "has_elevator", "has_terrace",
    "bathrooms", "condition", "energy_rating", "published_date", "first_seen", "full_url"
]].rename(columns={
    "neighbourhood_label": "neighbourhood",
    "has_elevator": "elevator",
    "has_terrace": "terrace",
    "price_per_sqm": "€/m²",
    "energy_rating": "energy",
    "published_date": "published",
    "first_seen": "scraped on",
    "full_url": "url",
}).sort_values("price")

st.dataframe(
    display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "url":      st.column_config.LinkColumn("url"),
        "elevator": st.column_config.CheckboxColumn(),
        "terrace":  st.column_config.CheckboxColumn(),
    }
)

# ── Price history ──────────────────────────────────────────────────────────────

ph = load_price_history()
if not ph.empty:
    st.divider()
    st.subheader("Price changes")
    ph_display = ph.copy()
    ph_display["recorded_at"] = pd.to_datetime(ph_display["recorded_at"]).dt.strftime("%Y-%m-%d")
    st.dataframe(
        ph_display[["recorded_at", "price", "full_url"]].rename(columns={
            "recorded_at": "date",
            "full_url": "url",
        }),
        use_container_width=True,
        hide_index=True,
        column_config={"url": st.column_config.LinkColumn("url")},
    )
