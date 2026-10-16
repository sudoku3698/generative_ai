import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import requests
import re
from st_aggrid import AgGrid, GridOptionsBuilder

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

    # Column filters
    #
    # Resets happen in on_click callbacks, which run before the script reruns,
    # so the new value is in place when the widget is drawn. Popping the key
    # and calling st.rerun() did not reliably reset the widget.
    #
    # Options come from the full df, not from the rows left by earlier filters.
    # Narrowed options changed every time an earlier filter changed, and
    # Streamlit then reset the later widgets - so clearing one filter wiped
    # the others too.
    def reset_filter(key, value):
        st.session_state[key] = value

    def clear_all_filters():
        for key in [k for k in st.session_state if str(k).startswith("filter_widget_")]:
            del st.session_state[key]
        st.session_state["sidebar_filter_columns"] = []

    with st.sidebar:
        st.header("Filters")

        st.button("Clear all filters", on_click=clear_all_filters)

        filter_columns = st.multiselect(
            "Filter by column", df.columns, key="sidebar_filter_columns"
        )

        filtered_df = df
        for col in filter_columns:
            widget_key = f"filter_widget_{col}"

            if pd.api.types.is_numeric_dtype(df[col]):
                if df[col].dropna().empty:
                    continue
                min_val, max_val = float(df[col].min()), float(df[col].max())
                if min_val == max_val:
                    st.write(f"{col}: {min_val}")
                    continue
                default = (min_val, max_val)
                st.session_state.setdefault(widget_key, default)
                selected_range = st.slider(col, min_val, max_val, key=widget_key)
                filtered_df = filtered_df[filtered_df[col].between(*selected_range)]
            else:
                default = sorted(df[col].dropna().astype(str).unique().tolist())
                st.session_state.setdefault(widget_key, default)
                selected_values = st.multiselect(col, default, key=widget_key)
                filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected_values)]

            st.button(
                f"Clear '{col}' filter",
                key=f"clear_{col}",
                on_click=reset_filter,
                args=(widget_key, default),
            )

            st.divider()

    # Universal search
    with st.form("search_form"):
        search = st.text_input("Search")
        st.form_submit_button("Search")

    display_df = filtered_df
    if search:
        mask = filtered_df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        display_df = filtered_df[mask]

    with st.expander("Show/Hide Columns"):
        visible_columns = st.multiselect(
            "Columns to display", df.columns, default=list(df.columns)
        )

    if visible_columns:
        display_df = display_df[visible_columns]

    st.caption(f"{display_df.shape[0]} rows x {display_df.shape[1]} columns")

    view_mode = st.radio("View", ["Table", "Grid"], horizontal=True)

    if view_mode == "Table":
        st.session_state.setdefault("grid_reset_counter", 0)

        if st.button("Clear table filters"):
            st.session_state["grid_reset_counter"] += 1
            st.rerun()

        grid_builder = GridOptionsBuilder.from_dataframe(display_df)
        grid_builder.configure_default_column(
            filter=True,
            floatingFilter=True,
            sortable=True,
            resizable=True,
            minWidth=160,
            wrapHeaderText=True,
            autoHeaderHeight=True,
        )
        for col in display_df.columns:
            if pd.api.types.is_numeric_dtype(display_df[col]):
                grid_builder.configure_column(col, filter="agNumberColumnFilter")
            elif pd.api.types.is_datetime64_any_dtype(display_df[col]):
                grid_builder.configure_column(col, filter="agDateColumnFilter")
            else:
                grid_builder.configure_column(col, filter="agTextColumnFilter")

        grid_options = grid_builder.build()
        grid_options["enableCellTextSelection"] = True
        grid_options["ensureDomOrder"] = True

        AgGrid(
            display_df,
            gridOptions=grid_options,
            height=500,
            fit_columns_on_grid_load=False,
            key=f"aggrid_{st.session_state['grid_reset_counter']}",
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