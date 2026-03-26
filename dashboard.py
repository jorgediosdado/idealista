import re
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

DB_FILE = "listings.db"

st.set_page_config(page_title="Idealista A Coruña", layout="wide")


# ── Data ──────────────────────────────────────────────────────────────────────

@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM listings", conn)
    conn.close()

    def parse_price(s):
        if not s: return None
        d = re.sub(r"[^\d]", "", s)
        return int(d) if d else None

    def parse_ppm(s):
        if not s: return None
        d = re.sub(r"[^\d]", "", s.split("€")[0])
        return int(d) if d else None

    MONTHS = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    }

    def parse_published(row):
        s = row["published"]
        ref = row["first_seen"]
        if not s or not ref:
            return None
        s = s.lower()
        m = re.search(r"(\d+)\s+de\s+(\w+)", s)
        if m:
            day = int(m.group(1))
            month = MONTHS.get(m.group(2))
            if month:
                year = ref.year if month <= ref.month else ref.year - 1
                try:
                    from datetime import date
                    return date(year, month, day)
                except ValueError:
                    pass
        return None

    df["price_num"]      = df["price"].apply(parse_price)
    df["ppm_num"]        = df["price_per_sqm"].apply(parse_ppm)
    df["first_seen"]     = pd.to_datetime(df["first_seen"])
    df["published_date"]     = df.apply(parse_published, axis=1)
    df["neighbourhood_label"] = df["neighbourhood"].str.replace("-", " ").str.title()
    df["full_url"] = "https://www.idealista.com" + df["url"]
    return df


df = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────────

st.sidebar.title("Filters")

neighbourhoods = sorted(df["neighbourhood_label"].unique())
selected_n = st.sidebar.multiselect("Neighbourhood", neighbourhoods, default=neighbourhoods)

price_min, price_max = int(df["price_num"].min()), int(df["price_num"].max())
price_range = st.sidebar.slider("Price (€)", price_min, price_max, (price_min, price_max), step=5000)

elevator   = st.sidebar.checkbox("Elevator only", value=False)
terrace    = st.sidebar.checkbox("Terrace only", value=False)

# ── Filter ────────────────────────────────────────────────────────────────────

fdf = df[df["neighbourhood_label"].isin(selected_n)]
fdf = fdf[fdf["price_num"].between(*price_range)]
if elevator: fdf = fdf[fdf["has_elevator"] == 1]
if terrace:  fdf = fdf[fdf["has_terrace"]  == 1]

# ── Header ────────────────────────────────────────────────────────────────────

st.title("🏠 Idealista — A Coruña")
st.caption(f"Data from listings.db · {len(df)} total listings scraped")

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

# ── Latest per neighbourhood ──────────────────────────────────────────────────

st.subheader("Latest listings by neighbourhood")

n_latest = st.slider("Show last N per neighbourhood", 1, 10, 3)

latest = (
    fdf.sort_values("first_seen", ascending=False)
       .groupby("neighbourhood_label")
       .head(n_latest)
       .sort_values(["neighbourhood_label", "first_seen"], ascending=[True, False])
)

latest_display = latest[[
    "neighbourhood_label", "first_seen", "title", "price", "price_per_sqm",
    "details", "has_elevator", "has_terrace", "published_date", "full_url"
]].rename(columns={
    "neighbourhood_label": "neighbourhood",
    "first_seen": "seen",
    "price_per_sqm": "€/m²",
    "has_elevator": "elevator",
    "has_terrace": "terrace",
    "published_date": "published",
    "full_url": "url",
})
latest_display["seen"] = latest_display["seen"].dt.strftime("%Y-%m-%d")

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

# ── Table ─────────────────────────────────────────────────────────────────────

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
