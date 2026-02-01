import streamlit as st
import pandas as pd
from afexcloud.layout import bootstrap_page
from afexcloud.utils import advanced_normalize

bootstrap_page()

st.title("📊 Collection Reviewer")
c1, c2 = st.columns(2)
with c1:
    inv_f = st.file_uploader("Inventory", type="csv")
with c2:
    loc_f = st.file_uploader("Local Library", type="csv")

safe_proj = st.session_state.get("_safe_proj", "project")

if inv_f and loc_f and st.button("📊 Generate Smart Review"):
    df_inv, df_loc = pd.read_csv(inv_f), pd.read_csv(loc_f)

    inv_rows = [
        {
            "Source": "Spotify",
            "Key": f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}",
            "Name": r["Name"],
            "Artist": r["Artist"],
        }
        for _, r in df_inv.iterrows()
    ]

    loc_rows = []
    for e in df_loc.iloc[:, 0]:
        p = str(e).split(",")
        if len(p) >= 2:
            loc_rows.append(
                {
                    "Source": "Local",
                    "Key": f"{advanced_normalize(p[0])}__{advanced_normalize(p[1])}",
                    "Name": p[0],
                    "Artist": p[1],
                }
            )

    master_df = pd.concat([pd.DataFrame(inv_rows), pd.DataFrame(loc_rows)]).sort_values(
        by=["Key", "Source"]
    ).reset_index(drop=True)

    counts = master_df["Key"].value_counts()
    lone_wolf_keys = counts[counts == 1].index.tolist()

    st.metric("Mismatches", len(lone_wolf_keys), delta_color="inverse")
    st.dataframe(master_df, use_container_width=True, hide_index=True)

    st.download_button(
        "📥 Download Report",
        master_df.to_csv(index=False).encode("utf-8"),
        f"{safe_proj}_Health.csv",
        "text/csv",
    )

