import pandas as pd
import streamlit as st

st.set_page_config(page_title="CSV Viewer", layout="wide")
st.title("CSV Viewer")

uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    st.caption(f"{df.shape[0]} rows x {df.shape[1]} columns")

    search = st.text_input("Search")
    if search:
        mask = df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
        df = df[mask]

    event = st.dataframe(
        df,
        use_container_width=True,
        height=300,
        on_select="rerun",
        selection_mode="single-row",
    )

    selected_rows = event.selection.rows
    if selected_rows:
        st.subheader("Row details")
        row = df.iloc[selected_rows[0]]
        st.table(row.astype(str))
else:
    st.info("Upload a CSV file to view its data.")
