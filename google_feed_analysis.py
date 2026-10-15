import streamlit as st
import requests
import xml.etree.ElementTree as ET
from collections import Counter
from requests.auth import HTTPBasicAuth
import pandas as pd
from urllib.parse import urlparse, parse_qs

pd.set_option('display.max_colwidth', None)

# Function to fetch XML data from URL with authentication
def fetch_xml_from_url(url):
    response = requests.get(url, auth=HTTPBasicAuth('nj0', 'nj0'))
    if response.status_code == 200:
        return response.text
    else:
        st.error(f"Failed to fetch XML. Status code: {response.status_code}")
        return None

def get_data(xml_data, gid_list_to_find):
    tree = ET.ElementTree(ET.fromstring(xml_data))
    root = tree.getroot()
    ns = {'g': 'http://base.google.com/ns/1.0'}
    items = root.findall('./channel/item', ns)
    
    data = []
    total_items = len(items)   # 👈 total feed items
    for item in items:
        item_group_id = item.find('g:item_group_id', ns).text if item.find('g:item_group_id', ns) is not None else None
        if not gid_list_to_find or item_group_id in gid_list_to_find:
            record = {
                'id': item.find('g:id', ns).text if item.find('g:id', ns) is not None else None,
                'title': item.find('title').text if item.find('title') is not None else None,
                'description': item.find('description').text if item.find('description') is not None else None,
                'google_product_category': item.find('g:google_product_category', ns).text if item.find('g:google_product_category', ns) is not None else None,
                'product_type': item.find('g:product_type', ns).text if item.find('g:product_type', ns) is not None else None,
                'price': item.find('g:price', ns).text if item.find('g:price', ns) is not None else None,
                'sale_price': item.find('g:sale_price', ns).text if item.find('g:price', ns) is not None else None,
                'availability': item.find('g:availability', ns).text if item.find('g:availability', ns) is not None else None,
                'gender': item.find('g:gender', ns).text if item.find('g:gender', ns) is not None else None,
                'color': item.find('g:color', ns).text if item.find('g:color', ns) is not None else None,
                'link': item.find('link', ns).text if item.find('link', ns) is not None else None,
                'custom_label_0':item.find('g:custom_label_0', ns).text if item.find('g:custom_label_0', ns) is not None else None,
                'image_url': item.find('g:image_link', ns).text if item.find('g:image_link', ns) is not None else None,
                'additional_image_link':item.find('g:additional_image_link',ns).text if item.find('g:additional_image_link', ns) is not None else None,
                'product_highlight':item.find('g:product_highlight', ns).text if item.find('g:product_highlight', ns) is not None else None,
            }
            data.append(record)
    
    return pd.DataFrame(data), total_items

# Streamlit UI
st.title("Google/Meta Feed Analysis")

url = st.text_input("Enter XML Feed URL:", value='https://diamondsfactory.ca/index.php?route=feed/facebook_feed_threecolor')
gid_input = st.text_input("Enter GID to find (comma-separated):", value='CLRN05685_01')

if st.button("Fetch and Analyze"):
    gid_list_to_find = [g.strip() for g in gid_input.split(',')]
    xml_data = fetch_xml_from_url(url)
    if xml_data:
        df,total_items = get_data(xml_data.strip(), gid_list_to_find)
        st.dataframe(df)
        st.write(f"Total items found: {len(df)} out of {total_items}")
