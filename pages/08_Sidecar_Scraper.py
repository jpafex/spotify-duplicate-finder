import streamlit as st
import pandas as pd
import time
import random

from afexcloud.layout import bootstrap_page
from afexcloud.utils import hunt_dna

bootstrap_page()

st.title("🕵️ Sidecar Musical Scraper")
st.info("No API Costs. Using public music databases to build your DNA logs.")

inv_f = st.file_uploader("Upload Inventory CSV", type="csv")
safe_proj = st.session_state.get("_safe_proj", "project")

if inv_f:
    df_inv = pd.read_csv(inv_f)
    if st.button("🚀 Start Multi-Source Scrape"):
        results, prog = [], st.progress(0)
        status_text = st.empty()

        for i, row in df_inv.iterrows():
            status_text.write(f"Scraping ({i+1}/{len(df_inv)}): **{row['Name']}**")
            k, b, src = hunt_dna(row["Name"], row["Artist"])
            results.append({"Key": k, "BPM": b, "Source": src})
            prog.progress((i + 1) / len(df_inv))
            time.sleep(random.uniform(0.8, 1.5))

        df_final = pd.concat([df_inv, pd.DataFrame(results)], axis=1)
        st.success("DNA Hunt Complete!")
        st.dataframe(df_final, use_container_width=True, hide_index=True)

        st.download_button(
            "📥 Download Master DJ Log",
            df_final.to_csv(index=False).encode("utf-8"),
            f"{safe_proj}_Master_DJ_Log.csv",
            "text/csv",
        )

