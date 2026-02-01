def _hide_pages_nav():
    # Hides Streamlit's built-in multipage nav list
    st.markdown(
        """
        <style>
        /* Hide the built-in multipage navigation (Pages list) */
        section[data-testid="stSidebar"] nav { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
