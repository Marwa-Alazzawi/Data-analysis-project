

import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
 
st.set_page_config(page_title="GLP-1 Dashboard", layout="wide")
 
 
# ---------------------------------------------------------------
# 1) Load and clean the data (same steps as the notebook)
#    @st.cache_data = load the data only once, not on every click
# ---------------------------------------------------------------
@st.cache_data
def load_data():
    df_adverse_events = pd.read_csv("adverse_events.csv")
    df_drugs = pd.read_csv("drugs_overview.csv")
    df = df_adverse_events.merge(df_drugs, on="generic_name", how="left")
 
    # dates
    df["receive_date"] = pd.to_datetime(df["receive_date"])
    df["fda_first_approval_date"] = pd.to_datetime(df["fda_first_approval_date"])
 
    # years since approval
    df["years_since_approval"] = np.floor(
        (df["receive_date"] - df["fda_first_approval_date"]).dt.days / 365.25
    ).astype(int)
 
    # severity level (0 = none ... 4 = death)
    def get_severity(row):
        if row["seriousness_death"]:
            return 4
        elif row["seriousness_lifethreatening"]:
            return 3
        elif row["seriousness_hospitalization"]:
            return 2
        elif row["seriousness_disabling"]:
            return 1
        else:
            return 0
 
    df["severity_level"] = df.apply(get_severity, axis=1)
 
    # one row per report
    df_reports = (
        df.groupby("safetyreportid", as_index=False)
        .agg(
            brand_queried=("brand_queried", "first"),
            country=("country", "first"),
            patient_age=("patient_age", "first"),
            patient_sex=("patient_sex", "first"),
            severity_level=("severity_level", "max"),
        )
    )
 
    severity_labels = {
        0: "No specified serious outcome",
        1: "Disabling",
        2: "Hospitalization",
        3: "Life-threatening",
        4: "Death",
    }
    df_reports["severity_label"] = df_reports["severity_level"].map(severity_labels)
 
    return df, df_reports
 
 
df, df_reports = load_data()
 
 
# ---------------------------------------------------------------
# 2) Sidebar filter: choose brands
# ---------------------------------------------------------------
st.sidebar.header("Filter")
 
all_brands = sorted(df_reports["brand_queried"].unique())
selected_brands = st.sidebar.multiselect("Brand", all_brands, default=all_brands)
 
# keep only the selected brands
df_reports = df_reports[df_reports["brand_queried"].isin(selected_brands)]
df = df[df["brand_queried"].isin(selected_brands)]
 
 
# ---------------------------------------------------------------
# 3) Title and KPIs
# ---------------------------------------------------------------
st.title("GLP-1 Drugs: Adverse-Event Reports")
 
total_reports = len(df_reports)
serious_pct = (df_reports["severity_level"] >= 2).mean() * 100
death_pct = (df_reports["severity_level"] == 4).mean() * 100
median_age = df_reports["patient_age"].median()
female_pct = (df_reports["patient_sex"] == "Female").mean() * 100
 
# most common reaction = the reaction mentioned in the most reports
reaction_counts = df.groupby("reaction")["safetyreportid"].nunique()
top_reaction = reaction_counts.idxmax()
top_reaction_pct = reaction_counts.max() / total_reports * 100
 
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Total reports", f"{total_reports:,}")
col2.metric("Hospitalization or worse", f"{serious_pct:.1f}%")
col3.metric("Death", f"{death_pct:.1f}%")
col4.metric("Median age", f"{median_age:.0f}")
col5.metric("Female", f"{female_pct:.1f}%")
col6.metric("Most common reaction", top_reaction, f"in {top_reaction_pct:.1f}% of reports",
            delta_color="off")
 
 
# ---------------------------------------------------------------
# 4) One tab per analysis
# ---------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Severity", "Age & Sex", "Brands", "Countries", "Reactions", "Before FDA Approval"]
)
 
# --- Tab 1: Severity ---
with tab1:
    severity_plot = df_reports["severity_label"].value_counts().reset_index()
    severity_plot.columns = ["severity", "number_of_reports"]
 
    fig = px.bar(
        severity_plot,
        x="number_of_reports",
        y="severity",
        text="number_of_reports",
        title="Distribution of Adverse-Event Severity",
    )
    st.plotly_chart(fig)
 
# --- Tab 2: Age & Sex ---
with tab2:
    fig = px.box(
        df_reports,
        x="severity_label",
        y="patient_age",
        title="Patient Age by Severity",
    )
    st.plotly_chart(fig)
 
    age_sex_severity = (
        df_reports[df_reports["patient_sex"] != "Unknown"]
        .groupby(["severity_label", "patient_sex"])["patient_age"]
        .mean()
        .reset_index()
    )
    fig = px.bar(
        age_sex_severity,
        x="severity_label",
        y="patient_age",
        color="patient_sex",
        barmode="group",
        title="Mean Patient Age by Sex and Severity",
    )
    st.plotly_chart(fig)
 
# --- Tab 3: Brands ---
with tab3:
    severity_order = [
        "No specified serious outcome",
        "Disabling",
        "Hospitalization",
        "Life-threatening",
        "Death",
    ]
 
    # % of each brand's reports in every severity level (each row adds up to 100%)
    brand_severity_pct = (
        pd.crosstab(df_reports["brand_queried"], df_reports["severity_label"], normalize="index")
        * 100
    ).round(1)
    brand_severity_pct = brand_severity_pct.reindex(columns=severity_order, fill_value=0)
 
    # add the total number of reports per brand
    brand_severity_pct.insert(0, "total_reports", df_reports["brand_queried"].value_counts())
 
    # most common reaction for each brand
    most_common_reaction = (
        df.groupby(["brand_queried", "reaction"])["safetyreportid"].nunique()
        .reset_index(name="reports")
        .sort_values("reports", ascending=False)
        .drop_duplicates("brand_queried")          # keep the top reaction per brand
        .set_index("brand_queried")["reaction"]
    )
    brand_severity_pct.insert(1, "most_common_reaction", most_common_reaction)
    brand_severity_pct = brand_severity_pct.sort_values("total_reports", ascending=False)
 
    st.subheader("Severity by brand (% of each brand's reports)")
    st.dataframe(brand_severity_pct)
 
    # same numbers as a chart: one bar per brand, split into the 5 severity levels
    brand_severity_long = (
        brand_severity_pct.drop(columns=["total_reports", "most_common_reaction"])
        .reset_index()
        .melt(id_vars="brand_queried", var_name="severity", value_name="percent")
    )
    fig = px.bar(
        brand_severity_long,
        x="brand_queried",
        y="percent",
        color="severity",
        category_orders={"severity": severity_order},
        title="Severity Distribution by Brand (%)",
        labels={"brand_queried": "Brand", "percent": "% of reports", "severity": "Severity"},
    )
    st.plotly_chart(fig)
 
# --- Tab 4: Countries ---
with tab4:
    country_table = (
        df_reports["country"].value_counts().head(5).reset_index()
    )
    country_table.columns = ["country", "report_count"]
    fig = px.pie(
        country_table,
        names="country",
        values="report_count",
        title="Top 5 Reporting Countries",
    )
    st.plotly_chart(fig)
 
# --- Tab 5: Reactions ---
with tab5:
    reaction_table = (
        df.groupby("reaction")["safetyreportid"]
        .nunique()
        .reset_index(name="report_count")
        .sort_values("report_count", ascending=False)
        .head(10)
    )
 
    st.subheader("Most common reaction")
    st.metric(top_reaction, f"{reaction_counts.max():,} reports",
              f"{top_reaction_pct:.1f}% of all reports", delta_color="off")
 
    st.subheader("Top 10 reactions")
    st.dataframe(reaction_table, hide_index=True)
 
    fig = px.pie(
        reaction_table.head(10),
        names="reaction",
        values="report_count",
        title="Top 10 Most Common Adverse Reactions Reported for GLP-1 Drugs",
    )
    st.plotly_chart(fig)
 
# --- Tab 6: Before FDA approval ---
with tab6:
    pre_approval = (
        df[df["years_since_approval"] < 0]
        .groupby(["brand_queried", "years_since_approval"])["safetyreportid"]
        .nunique()
        .reset_index(name="number_of_reports")
    )
    pre_approval["years_before_approval"] = pre_approval["years_since_approval"].abs()
 
    if pre_approval.empty:
        st.write("No reports before FDA approval for the selected brands.")
    else:
        st.metric("Reports before FDA approval", pre_approval["number_of_reports"].sum())
        fig = px.bar(
            pre_approval,
            x="years_before_approval",
            y="number_of_reports",
            color="brand_queried",
            barmode="group",
            text="number_of_reports",
            title="Reports Received Before FDA Approval",
        )
        st.plotly_chart(fig)
 
 