import streamlit as st
import pandas as pd
import numpy as np


st.title("Streakmlit App")

st.write("This is a simple Streamlit app to demonstrate how to use Streamlit for building interactive web applications.")

df= pd.DataFrame({
    'A': np.random.rand(100),
    'B': np.random.rand(100),
    'C': np.random.rand(100)
})
st.dataframe(df)

chart_data=pd.DataFrame(
    np.random.rand(20,3),
    columns=['A','B','C']
)
st.line_chart(chart_data)