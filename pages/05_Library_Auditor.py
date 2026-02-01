import streamlit as st
import pandas as pd
from afexcloud.layout import bootstrap_page
from afexcloud.utils import advanced_normalize

bootstrap_page()

st.title("💿 Library Auditor")
c1, c2 = st.columns(2)
with c1:
    inv_f = st.file_uploader("Spotify Inventory", type="csv")
with c2:
    loc_f = st.file_uploader("Local Songs", type="csv")

safe_proj = st.session_state.get("_safe_proj", "project")

if inv_f and loc_f and st.button("🔍 Run Audit"):
    df_inv, df_loc = pd.read_csv(inv_f), pd.read_csv(loc_f)
    df_inv["compare_key"] = df_inv.apply(
        lambda r: f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}", axis=1
    )
    loc_keys = {
        f"{advanced_normalize(str(e).split(',')[0])}__{advanced_normalize(str(e).split(',')[1])}"
        for e in df_loc.iloc[:, 0]
        if len(str(e).split(",")) >= 2
    }
    missing_df = df_inv[~df_inv["compare_key"].isin(loc_keys)].copy()
    st.metric("Missing Tracks", len(missing_df))
    st.dataframe(missing_df[["Original Pos", "Name", "Artist", "Album"]], use_container_width=True, hide_index=True)
    st.download_button(
        "📥 Download Missing",
        missing_df.to_csv(index=False).encode("utf-8"),
        f"{safe_proj}_Missing.csv",
        "text/csv",
    )

