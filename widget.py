import streamlit as st
import pandas as pd
st.title("Streakmit Widget")
st.write("This is a simple Streamlit widget to demonstrate how to create interactive components in Streamlit.")

name=st.text_input("Enter your name:")
age=st.slider("Select your age:", 0, 100, 25)
st.write(f"Your name is {name} and you are {age} years old.")
if name:
    st.write(f"Hello, {name}! Welcome to Streakmit Widget.")


options = st.multiselect("Select your favorite colors:", ["Red", "Green", "Blue", "Yellow"])

button_clicked = st.button("Submit")
if button_clicked:
    st.write(f"You selected: {', '.join(options)}")

file_upload = st.file_uploader("Upload a file:",type=["csv","xml"])
if file_upload is not None:
    st.write("File uploaded successfully!")
    st.write(f"Filename: {file_upload.name}")
    st.write(f"File type: {file_upload.type}")
    st.write(f"File size: {file_upload.size/1024:.2f} KB")

    pd.set_option('display.max_colwidth', None)
    if file_upload.type == "text/csv":
        df = pd.read_csv(file_upload)
        st.dataframe(df)
    elif file_upload.type == "text/xml":
        xml_content = file_upload.read().decode("utf-8")
        st.text(xml_content)

