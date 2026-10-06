
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="GLP-1 Adverse Event Analysis", layout="wide")

# center and control the color
st.markdown(
    """
    <h1 style="
        text-align: center;
        color: #2E86C1;
        font-size: 45px;
    ">
        GLP-1 Adverse Events Analysis
    </h1>

    <p style="
        text-align: center;
        color: gray;
        font-size: 20px;
    ">
        Analysis of GLP-1 Drug Safety Reports
    </p>
    """,
    unsafe_allow_html=True
)

st.header("Project Overview")

st.write("""
This dashboard explores GLP-1 adverse-event reports,
including patient demographics, drug brands, severity,
reactions, geographical distribution, and FDA approval information.
""")

st.image("image.jpg")
st.markdown(
    """
    <p style="
        text-align: center;
        font-size: 24px;
        font-weight: bold;
    ">
        GLP-1 Drugs
    </p>
    """,
    unsafe_allow_html=True
)
