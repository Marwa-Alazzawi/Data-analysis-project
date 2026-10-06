import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


# ---------------------------------------------------------
# PAGE SETTINGS
# ---------------------------------------------------------

st.set_page_config(
    page_title="GLP-1 Adverse Events Analysis",
    page_icon="💊",
    layout="wide"
)


# ---------------------------------------------------------
# TITLE
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

@st.cache_data
def load_data():

    df_adverse_events = pd.read_csv("adverse_events.csv")
    df_drugs = pd.read_csv("drugs_overview.csv")

    df = df_adverse_events.merge(
        df_drugs,
        on="generic_name",
        how="left"
    )

    # Convert dates
    df["receive_date"] = pd.to_datetime(df["receive_date"])
    df["fda_first_approval_date"] = pd.to_datetime(
        df["fda_first_approval_date"]
    )

    # FDA approval year
    df["approval_year"] = df[
        "fda_first_approval_date"
    ].dt.year

    return df


df = load_data()


# ---------------------------------------------------------
# DATA CLEANING / FEATURE ENGINEERING
# ---------------------------------------------------------

# -------------------------
# Age
# -------------------------

df_age = (
    df.groupby(
        "safetyreportid",
        as_index=False
    )["patient_age"]
    .first()
)

# KNN imputation used in the notebook
from sklearn.impute import KNNImputer

knn = KNNImputer(n_neighbors=10)

df_age[["patient_age"]] = knn.fit_transform(
    df_age[["patient_age"]]
)


# -------------------------
# Sex
# -------------------------

df_gender = df[
    ["safetyreportid", "patient_sex"]
].copy()

df_gender["patient_sex"] = (
    df_gender["patient_sex"]
    .replace("Unknown", np.nan)
)

df_gender = (
    df_gender
    .groupby(
        "safetyreportid",
        as_index=False
    )["patient_sex"]
    .first()
)

df_gender = df_gender.dropna(
    subset=["patient_sex"]
)


# -------------------------
# Severity
# -------------------------

def get_severity(row):

    if row["seriousness_death"] == True:
        return 4

    elif row["seriousness_lifethreatening"] == True:
        return 3

    elif row["seriousness_hospitalization"] == True:
        return 2

    elif row["seriousness_disabling"] == True:
        return 1

    else:
        return 0


df["severity_level"] = df.apply(
    get_severity,
    axis=1
)


df_severity = (
    df.groupby(
        "safetyreportid",
        as_index=False
    )["severity_level"]
    .max()
)


# -------------------------
# Report-level dataframe
# -------------------------

df_reports = (
    df_age
    .merge(
        df_gender,
        on="safetyreportid",
        how="outer"
    )
    .merge(
        df_severity,
        on="safetyreportid",
        how="outer"
    )
)

df_reports = df_reports.dropna(
    subset=["patient_sex"]
)


# -------------------------
# Severity labels
# -------------------------

severity_labels = {
    0: "No specified serious outcome",
    1: "Disabling",
    2: "Hospitalization",
    3: "Life-threatening",
    4: "Death"
}

df_reports["severity_label"] = (
    df_reports["severity_level"]
    .map(severity_labels)
)


# -------------------------
# Add brand
# -------------------------

df_brand = (
    df[
        ["safetyreportid", "brand_queried"]
    ]
    .drop_duplicates(
        subset="safetyreportid"
    )
)

df_reports = df_reports.merge(
    df_brand,
    on="safetyreportid",
    how="left"
)


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select Analysis",
    [
        "Project Overview",
        "Analysis 1 - Severity",
        "Analysis 2 - Age and Severity",
        "Analysis 3 - Age, Sex and Severity",
        "Analysis 4 - Brand and Severity",
        "Analysis 5 - Country",
        "Analysis 6 - FDA Approval",
        "Drug Tables"
    ]
)


# =========================================================
# PROJECT OVERVIEW
# =========================================================

if page == "Project Overview":

    st.header("Project Overview")

    st.write(
        """
        This dashboard explores adverse-event reports associated
        with GLP-1 drugs. The analysis investigates severity,
        patient demographics, drug brands, geographical reporting
        patterns and FDA approval timelines.
        """
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Reaction Records",
        f"{len(df):,}"
    )

    col2.metric(
        "Unique Safety Reports",
        f"{df['safetyreportid'].nunique():,}"
    )

    col3.metric(
        "GLP-1 Brands",
        df["brand_queried"].nunique()
    )

    st.subheader("Dataset Preview")

    st.dataframe(
        df.head(10),
        use_container_width=True
    )


# =========================================================
# ANALYSIS 1
# =========================================================

elif page == "Analysis 1 - Severity":

    st.header(
        "Analysis 1 — Distribution of Adverse-Event Severity"
    )

    severity_counts = (
        df_reports["severity_label"]
        .value_counts()
        .reset_index()
    )

    severity_counts.columns = [
        "Severity",
        "Number of Reports"
    ]

    st.subheader("Severity Table")

    st.dataframe(
        severity_counts,
        use_container_width=True,
        hide_index=True
    )

    fig = px.pie(
        severity_counts,
        names="Severity",
        values="Number of Reports",
        title="Distribution of Adverse-Event Severity"
    )

    fig.update_traces(
        textinfo="percent+label"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# =========================================================
# ANALYSIS 2
# =========================================================

elif page == "Analysis 2 - Age and Severity":

    st.header(
        "Analysis 2 — Patient Age and Adverse-Event Severity"
    )

    age_summary = (
        df_reports
        .groupby("severity_label")["patient_age"]
        .agg(["count", "mean", "median"])
        .round(2)
        .reset_index()
    )

    age_summary.columns = [
        "Severity",
        "Number of Reports",
        "Mean Age",
        "Median Age"
    ]

    st.subheader("Age Summary")

    st.dataframe(
        age_summary,
        use_container_width=True,
        hide_index=True
    )

    fig = px.box(
        df_reports,
        x="severity_label",
        y="patient_age",
        title="Patient Age Distribution by Severity",
        labels={
            "severity_label": "Severity",
            "patient_age": "Patient Age (years)"
        }
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# =========================================================
# ANALYSIS 3
# =========================================================

elif page == "Analysis 3 - Age, Sex and Severity":

    st.header(
        "Analysis 3 — Age, Sex and Adverse-Event Severity"
    )

    age_sex_severity = (
        df_reports
        .groupby(
            ["severity_label", "patient_sex"]
        )["patient_age"]
        .mean()
        .reset_index()
    )

    age_sex_severity[
        "patient_age"
    ] = age_sex_severity[
        "patient_age"
    ].round(2)

    st.subheader(
        "Mean Patient Age by Sex and Severity"
    )

    st.dataframe(
        age_sex_severity,
        use_container_width=True,
        hide_index=True
    )

    fig = px.bar(
        age_sex_severity,
        x="severity_label",
        y="patient_age",
        color="patient_sex",
        barmode="group",
        title="Mean Patient Age by Sex and Severity Level",
        labels={
            "severity_label": "Severity Level",
            "patient_age": "Mean Patient Age (years)",
            "patient_sex": "Sex"
        }
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# =========================================================
# ANALYSIS 4
# =========================================================

elif page == "Analysis 4 - Brand and Severity":

    st.header(
        "Analysis 4 — Adverse-Event Severity by GLP-1 Brand"
    )

    # This calculation was missing before the plot
    # in the notebook.
    brand_severity = (
        df_reports
        .groupby(
            ["brand_queried", "severity_label"]
        )
        .size()
        .reset_index(name="count")
    )

    st.subheader("Brand and Severity Table")

    st.dataframe(
        brand_severity,
        use_container_width=True,
        hide_index=True
    )

    severity_order = [
        "Death",
        "Life-threatening",
        "Hospitalization",
        "Disabling",
        "No specified serious outcome"
    ]

    fig = px.bar(
        brand_severity,
        x="brand_queried",
        y="count",
        facet_row="severity_label",
        text="count",
        category_orders={
            "severity_label": severity_order
        },
        title="Adverse-Event Severity by GLP-1 Brand",
        labels={
            "brand_queried": "Brand",
            "count": "Number of Reports"
        }
    )

    fig.update_yaxes(
        matches=None
    )

    fig.update_xaxes(
        showticklabels=True,
        tickangle=-45
    )

    fig.update_traces(
        textposition="outside"
    )

    fig.update_layout(
        height=1300,
        showlegend=False
    )

    fig.for_each_annotation(
        lambda a: a.update(
            text=a.text.replace(
                "severity_label=",
                ""
            )
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# =========================================================
# ANALYSIS 5
# =========================================================

elif page == "Analysis 5 - Country":

    st.header(
        "Analysis 5 — Geographical Distribution of Reports"
    )

    country_reports = (
        df[
            ["safetyreportid", "country"]
        ]
        .drop_duplicates()
    )

    country_report_table = (
        country_reports
        .groupby("country")["safetyreportid"]
        .count()
        .reset_index(
            name="report_count"
        )
        .sort_values(
            "report_count",
            ascending=False
        )
        .reset_index(drop=True)
    )

    # Percentage based on all countries
    total_reports = (
        country_report_table[
            "report_count"
        ].sum()
    )

    country_report_table[
        "percentage"
    ] = (
        country_report_table[
            "report_count"
        ]
        / total_reports
        * 100
    ).round(2)

    st.subheader(
        "Reports by Country"
    )

    st.dataframe(
        country_report_table,
        use_container_width=True,
        hide_index=True
    )

    # Top 5 for pie chart
    top_5_countries = (
        country_report_table.head(5)
    )

    fig = px.pie(
        top_5_countries,
        names="country",
        values="report_count",
        title="Top 5 Countries Reporting GLP-1 Adverse Events"
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.caption(
        "Pie-chart percentages represent the distribution "
        "within the five countries displayed."
    )


# =========================================================
# ANALYSIS 6
# =========================================================

elif page == "Analysis 6 - FDA Approval":

    st.header(
        "Analysis 6 — Timeline of FDA Approval for GLP-1 Drugs"
    )

    approval_table = (
        df[
            [
                "brand_queried",
                "manufacturer",
                "approval_year"
            ]
        ]
        .drop_duplicates()
        .sort_values("approval_year")
        .reset_index(drop=True)
    )

    st.subheader("FDA Approval Table")

    st.dataframe(
        approval_table,
        use_container_width=True,
        hide_index=True
    )

    fig = px.line(
        approval_table,
        x="approval_year",
        y="brand_queried",
        markers=True,
        hover_data=[
            "manufacturer"
        ],
        title="Timeline of FDA Approval for GLP-1 Drugs",
        labels={
            "approval_year": "FDA Approval Year",
            "brand_queried": "Brand Name",
            "manufacturer": "Manufacturer"
        }
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# =========================================================
# TABLES
# =========================================================

elif page == "Drug Tables":

    st.header(
        "GLP-1 Drug Information"
    )

    # -------------------------
    # Drug table
    # -------------------------

    st.subheader(
        "Brand, Generic Name and Manufacturer"
    )

    drug_table = (
        df[
            [
                "brand_queried",
                "generic_name",
                "manufacturer"
            ]
        ]
        .drop_duplicates()
        .sort_values(
            [
                "manufacturer",
                "brand_queried"
            ]
        )
        .reset_index(drop=True)
    )

    drug_table.columns = [
        "Brand Name",
        "Generic Name",
        "Manufacturer"
    ]

    st.dataframe(
        drug_table,
        use_container_width=True,
        hide_index=True
    )


    # -------------------------
    # Indication table
    # -------------------------

    st.subheader(
        "Drug Indications"
    )

    indication_table = (
        df[
            [
                "brand_queried",
                "generic_name",
                "indication"
            ]
        ]
        .drop_duplicates()
        .sort_values("brand_queried")
        .reset_index(drop=True)
    )

    indication_table.columns = [
        "Brand Name",
        "Generic Name",
        "Indication"
    ]

    st.dataframe(
        indication_table,
        use_container_width=True,
        hide_index=True
    )


    # -------------------------
    # Reaction table
    # -------------------------

    st.subheader(
        "Top 10 Reported Adverse Reactions"
    )

    reaction_table = (
        df
        .groupby("reaction")[
            "safetyreportid"
        ]
        .count()
        .reset_index(
            name="report_count"
        )
        .sort_values(
            "report_count",
            ascending=False
        )
        .reset_index(drop=True)
    )

    top_10_reactions = (
        reaction_table.head(10)
    )

    top_10_reactions.columns = [
        "Reaction",
        "Number of Reaction Records"
    ]

    st.dataframe(
        top_10_reactions,
        use_container_width=True,
        hide_index=True
    )