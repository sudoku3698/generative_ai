import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import requests
import re

st.set_page_config(page_title="Google/Meta XML Feed to CSV", layout="wide")

st.title("Google/Meta XML Feed to CSV Converter")

source = st.radio("XML source", ["Enter URL", "Upload file"], horizontal=True)

xml_url = ""
username = ""
password = ""
uploaded_file = None

if source == "Enter URL":
    xml_url = st.text_input(
        "Enter XML Feed URL",
        placeholder="https://example.com/feed.xml"
    )

    username = st.text_input(
        "Username (optional)",
        placeholder="Username"
    )

    password = st.text_input(
        "Password (optional)",
        type="password",
        placeholder="Password"
    )
else:
    uploaded_file = st.file_uploader("Upload XML file", type=["xml"])

force_refresh = st.checkbox("Force refresh (ignore cache)")


def clean_tag(tag):
    """Remove XML namespace."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


@st.cache_data(show_spinner="Fetching XML feed...", ttl=300)
def fetch_xml(url, username, password):
    auth = (username, password) if username or password else None
    response = requests.get(url, timeout=(30, 300), auth=auth)
    response.raise_for_status()
    return response.content


@st.cache_data(show_spinner="Parsing XML feed...")
def parse_xml(xml_content):

    root = ET.fromstring(xml_content)

    rows = []

    # Process each product
    for item in root.findall(".//item"):

        row = {}

        for child in item:

            tag = clean_tag(child.tag)
            value = child.text.strip() if child.text else ""

            # --------------------------
            # PRODUCT HIGHLIGHTS
            # --------------------------
            if tag == "product_highlight":

                if ":" in value:

                    key, val = value.split(":", 1)

                    row[key.strip()] = val.strip()

                continue

            # --------------------------
            # Handle nested XML
            # --------------------------
            elif len(child):

                for subchild in child:

                    subtag = clean_tag(subchild.tag)
                    subvalue = subchild.text.strip() if subchild.text else ""

                    row[f"{tag}_{subtag}"] = subvalue

            # --------------------------
            # Normal XML fields
            # --------------------------
            else:

                if tag in row:

                    if isinstance(row[tag], list):
                        row[tag].append(value)
                    else:
                        row[tag] = [row[tag], value]

                else:
                    row[tag] = value

        # Convert lists into pipe-separated strings
        for key in row:

            if isinstance(row[key], list):
                row[key] = " | ".join(row[key])

        rows.append(row)

    # Create DataFrame
    df = pd.DataFrame(rows)

    # Sort columns alphabetically
    df = df.reindex(sorted(df.columns), axis=1)

    return df


if st.button("Load XML"):

    if source == "Enter URL" and not xml_url:
        st.warning("Please enter XML URL")
        st.stop()

    if source == "Upload file" and uploaded_file is None:
        st.warning("Please upload an XML file")
        st.stop()

    try:

        if force_refresh:
            fetch_xml.clear()
            parse_xml.clear()

        if source == "Enter URL":
            xml_content = fetch_xml(xml_url, username, password)
        else:
            xml_content = uploaded_file.getvalue()

        st.session_state["xml_df"] = parse_xml(xml_content)

    except Exception as e:
        st.error(f"Error processing XML: {e}")

if "xml_df" in st.session_state:

    df = st.session_state["xml_df"]

    st.success(f"Loaded {len(df)} products")
    st.write(f"Detected {len(df.columns)} columns")

    # Show all columns
    with st.expander("Show All Columns"):
        st.write(df.columns.tolist())

    # Analysis
    with st.expander("Column Distribution Analysis"):

        analysis_column = st.selectbox(
            "Select a column to analyze",
            df.columns,
        )

        if analysis_column:

            series = (
                df[analysis_column]
                .fillna("Missing")
                .astype(str)
                .str.strip()
                .str.replace("&gt;", ">", regex=False)
            )

            split_hierarchy = st.checkbox(
                "Split hierarchical values (e.g. Category > Subcategory)",
                value=series.str.contains(">").any(),
            )

            if split_hierarchy:
                split_series = series.str.split(">")
                max_depth = int(split_series.map(len).max())

                level = st.selectbox(
                    "Level",
                    list(range(1, max_depth + 1)),
                    format_func=lambda x: f"Level {x}",
                )

                level_series = split_series.map(
                    lambda parts: parts[level - 1].strip() if len(parts) >= level else "Missing"
                )

                st.subheader(f"{analysis_column} Distribution (Level {level})")

                value_counts = level_series.value_counts().reset_index()
                value_counts.columns = [f"{analysis_column} (Level {level})", "Count"]
            else:
                st.subheader(f"{analysis_column} Distribution")

                value_counts = series.value_counts().reset_index()
                value_counts.columns = [analysis_column, "Count"]

            st.dataframe(value_counts, use_container_width=True)
            st.bar_chart(value_counts.set_index(value_counts.columns[0]))

    # Universal search
    with st.form("search_form"):
        search = st.text_input("Search")
        st.form_submit_button("Search")

    display_df = df
    if search:
        mask = df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        display_df = df[mask]

    st.caption(f"{display_df.shape[0]} rows x {display_df.shape[1]} columns")

    view_mode = st.radio("View", ["Table", "Grid"], horizontal=True)

    if view_mode == "Table":
        st.dataframe(
            display_df,
            use_container_width=True
        )
    else:
        image_col = next((c for c in display_df.columns if "image" in c.lower()), None)
        title_col = next((c for c in display_df.columns if c.lower() in ("title", "name")), None)
        price_col = next((c for c in display_df.columns if c.lower() == "price"), None)
        sale_price_col = next((c for c in display_df.columns if "sale_price" in c.lower() or c.lower() == "saleprice"), None)
        link_col = next((c for c in display_df.columns if c.lower() == "link"), None)

        if image_col is None:
            st.info("No image column found in the data.")
        else:
            cols_per_row = 4
            items_per_page = 24
            rows = display_df.reset_index(drop=True)

            total_pages = max(1, -(-len(rows) // items_per_page))
            page = st.number_input(
                "Page", min_value=1, max_value=total_pages, value=1, step=1
            )
            st.caption(f"Page {page} of {total_pages}")

            page_start = (page - 1) * items_per_page
            page_rows = rows.iloc[page_start:page_start + items_per_page]

            with st.container(height=600):
                for start in range(0, len(page_rows), cols_per_row):
                    cols = st.columns(cols_per_row)

                    for col, (row_index, row) in zip(cols, page_rows.iloc[start:start + cols_per_row].iterrows()):
                        with col:
                            image_url = row.get(image_col)

                            if isinstance(image_url, str) and image_url.startswith("http"):
                                try:
                                    st.image(image_url, use_container_width=True)
                                except Exception:
                                    st.write("Image unavailable")
                            else:
                                st.write("No image")

                            if title_col:
                                st.caption(str(row.get(title_col, "")))

                            if price_col and sale_price_col and str(row.get(sale_price_col, "")).strip():
                                st.markdown(
                                    f"~~{row.get(price_col, '')}~~ **{row.get(sale_price_col, '')}**"
                                )
                            else:
                                if price_col:
                                    st.write(str(row.get(price_col, "")))
                                if sale_price_col:
                                    st.write(str(row.get(sale_price_col, "")))

                            if link_col:
                                product_link = row.get(link_col)
                                if isinstance(product_link, str) and product_link.startswith("http"):
                                    st.link_button(
                                        "View Product",
                                        product_link,
                                        use_container_width=True,
                                    )

    # CSV download
    csv = display_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download CSV",
        csv,
        "products.csv",
        "text/csv"
    )