import streamlit as st
import duckdb
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

DB_PATH = "data/veteran_suicide.duckdb"

st.set_page_config(
    page_title="Veteran Suicide Prevention Dashboard",
    page_icon="🎖️",
    layout="wide"
)

@st.cache_data
def load_rates():
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
        with veteran as (
            select
                year,
                TRY_CAST(NULLIF(TRIM(CAST(total_adj_rate AS VARCHAR)), '.') AS DOUBLE) as veteran_rate_all,
                TRY_CAST(NULLIF(TRIM(CAST(male_adj_rate AS VARCHAR)), '.') AS DOUBLE) as veteran_rate_male,
                TRY_CAST(NULLIF(TRIM(CAST(female_adj_rate AS VARCHAR)), '.') AS DOUBLE) as veteran_rate_female
            from raw_va_veteran
            where year between 2001 and 2023
            and TRY_CAST(total_population AS BIGINT) > 1000000
        ),
        civilian as (
            select
                "Year" as year,
                max(case when sex = 'male' then TRY_CAST(NULLIF(TRIM(CAST("Age-Adjusted Rate" AS VARCHAR)), '.') AS DOUBLE) end) as civilian_rate_male,
                max(case when sex = 'female' then TRY_CAST(NULLIF(TRIM(CAST("Age-Adjusted Rate" AS VARCHAR)), '.') AS DOUBLE) end) as civilian_rate_female
            from raw_wisqars
            where TRY_CAST("Year" AS INTEGER) IS NOT NULL
            group by "Year"
        )
        select
            v.year,
            v.veteran_rate_all,
            v.veteran_rate_male,
            v.veteran_rate_female,
            c.civilian_rate_male,
            c.civilian_rate_female,
            round(v.veteran_rate_male - c.civilian_rate_male, 2) as male_gap,
            round(v.veteran_rate_female - c.civilian_rate_female, 2) as female_gap
        from veteran v
        left join civilian c on v.year = c.year
        order by v.year
    """).df()
    con.close()
    return df

@st.cache_data
def load_gender_gap():
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
        select
            year,
            TRY_CAST(NULLIF(TRIM(CAST(female_adj_rate AS VARCHAR)), '.') AS DOUBLE) as veteran_female_rate,
            TRY_CAST(NULLIF(TRIM(CAST(male_adj_rate AS VARCHAR)), '.') AS DOUBLE) as veteran_male_rate,
            TRY_CAST(NULLIF(TRIM(CAST(female_adj_rate AS VARCHAR)), '.') AS DOUBLE)
                / NULLIF(TRY_CAST(NULLIF(TRIM(CAST(male_adj_rate AS VARCHAR)), '.') AS DOUBLE), 0) as female_to_male_ratio
        from raw_va_veteran
        where year between 2001 and 2023
        and TRY_CAST(total_population AS BIGINT) > 1000000
        order by year
    """).df()
    con.close()
    return df

@st.cache_data
def load_vha_access():
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
        with vha as (
            select
                year,
                TRY_CAST(NULLIF(TRIM(CAST(total_adj_rate AS VARCHAR)), '.') AS DOUBLE) as vha_rate,
                TRY_CAST(NULLIF(TRIM(CAST(male_adj_rate AS VARCHAR)), '.') AS DOUBLE) as vha_rate_male,
                TRY_CAST(NULLIF(TRIM(CAST(female_adj_rate AS VARCHAR)), '.') AS DOUBLE) as vha_rate_female
            from raw_va_vha_user
            where year between 2001 and 2023
            and TRY_CAST(total_population AS BIGINT) > 1000000
        ),
        other as (
            select
                year,
                TRY_CAST(NULLIF(TRIM(CAST(total_adj_rate AS VARCHAR)), '.') AS DOUBLE) as other_rate,
                TRY_CAST(NULLIF(TRIM(CAST(male_adj_rate AS VARCHAR)), '.') AS DOUBLE) as other_rate_male,
                TRY_CAST(NULLIF(TRIM(CAST(female_adj_rate AS VARCHAR)), '.') AS DOUBLE) as other_rate_female
            from raw_va_other_veteran
            where year between 2001 and 2023
            and TRY_CAST(total_population AS BIGINT) > 1000000
        )
        select
            v.year,
            v.vha_rate,
            v.vha_rate_male,
            v.vha_rate_female,
            o.other_rate,
            o.other_rate_male,
            o.other_rate_female,
            round(o.other_rate - v.vha_rate, 2) as access_gap
        from vha v
        left join other o on v.year = o.year
        order by v.year
    """).df()
    con.close()
    return df

@st.cache_data
def load_va_state():
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
        select year, region, state, veteran_suicides, population, crude_rate
        from raw_va_state
        order by year, state
    """).df()
    con.close()
    return df

@st.cache_data
def load_sex_state():
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
        select year, state, sex, veteran_suicides
        from raw_va_state_sex
        where sex in ('Male', 'Female')
        order by state, year, sex
    """).df()
    con.close()
    return df


# --- LOAD DATA ---
rates = load_rates()
gender = load_gender_gap()
vha = load_vha_access()
va_state = load_va_state()
sex_state = load_sex_state()

# --- DERIVED ---
rates_sorted = rates.sort_values("year").copy()
rates_sorted["yoy_change"] = rates_sorted["veteran_rate_all"].pct_change() * 100
latest_vha = vha[vha["year"] == vha["year"].max()].iloc[0]
first_vha = vha[vha["year"] == vha["year"].min()].iloc[0]
other_pct = round(((latest_vha['other_rate'] - first_vha['other_rate']) / first_vha['other_rate']) * 100)
vha_pct = round(((latest_vha['vha_rate'] - first_vha['vha_rate']) / first_vha['vha_rate']) * 100)

# --- COLORS ---
NAVY = "#0D1B2A"
VET_MALE = "#1B4F8A"
VET_FEMALE = "#C0392B"
CIV_MALE = "#7FB3D3"
CIV_FEMALE = "#E8A090"
VHA_COLOR = "#2E86AB"
OTHER_COLOR = "#C0392B"
ACCENT = "#C9A84C"
SUCCESS = "#1E8449"

PALETTE = [VET_MALE, "#6C3483", VHA_COLOR, ACCENT,
           "#1E8449", "#D35400", "#7F8C8D", "#2C3E50", "#CB4335", VET_FEMALE]
PALETTE_M = ["#154360", "#1A5276", "#1F618D", "#2471A3", "#2E86C1"]
PALETTE_F = ["#922B21", "#A93226", "#C0392B", "#E74C3C", "#EC7063"]

def base_layout(**kwargs):
    layout = dict(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_color=NAVY,
        yaxis=dict(gridcolor="#eeeeee"),
        xaxis=dict(gridcolor="#eeeeee"),
        legend=dict(bgcolor="white", bordercolor="#cccccc", borderwidth=1),
        dragmode="pan",
    )
    layout.update(kwargs)
    return layout

def section_header(roman, title):
    st.markdown(f"""
    <div style="
        text-align: center;
        padding: 1.5rem 0 0.5rem 0;
        margin: 0.5rem 0 1rem 0;
        border-top: 1px solid #e0e0e0;
        border-bottom: 1px solid #e0e0e0;
    ">
        <div style="
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.25em;
            text-transform: uppercase;
            color: #2E86AB;
            margin-bottom: 0.4rem;
        ">{roman}</div>
        <div style="
            font-family: 'DM Serif Display', serif;
            font-size: 1.4rem;
            color: #0D1B2A;
            font-weight: 400;
        ">{title}</div>
    </div>
    """, unsafe_allow_html=True)

# --- STYLES ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1, h2, h3 { font-family: 'DM Serif Display', serif; }
.methodology-box {
    background-color: #f8f9fa;
    border-left: 4px solid #2E86AB;
    padding: 1rem 1.25rem;
    border-radius: 4px;
    font-size: 0.85rem;
    color: #444;
    margin-top: 1rem;
}
.callout-box {
    background-color: #EAF2FB;
    border-left: 4px solid #1B4F8A;
    padding: 1rem 1.25rem;
    border-radius: 4px;
    margin: 1rem 0;
}
.warning-box {
    background-color: #FEF9E7;
    border-left: 4px solid #C9A84C;
    padding: 1rem 1.25rem;
    border-radius: 4px;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.title("Veteran Suicide in America")
st.markdown("#### VA mental health care is working. Most at-risk veterans are not in it.")
st.markdown("*Data: VA National Veteran Suicide Prevention Annual Report 2025 · CDC WISQARS · All rates age-adjusted per 100,000*")
st.markdown("---")

# --- TOP LINE METRICS ---
latest = rates[rates["year"] == rates["year"].max()].iloc[0]
first = rates[rates["year"] == 2001].iloc[0]

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Veteran Suicide Rate (2023)",
              f"{latest['veteran_rate_all']:.1f} per 100K",
              delta=f"+{latest['veteran_rate_all'] - first['veteran_rate_all']:.1f} since 2001",
              delta_color="inverse",
              help="Age-adjusted rate per 100,000 veterans")
with col2:
    st.metric("Veterans in VHA Care",
              f"+{vha_pct}% since 2001",
              delta="Rising more slowly",
              delta_color="inverse",
              help=f"VHA user rates rose from {first_vha['vha_rate']:.1f} to {latest_vha['vha_rate']:.1f} per 100,000 since 2001")
with col3:
    st.metric("Non-VHA Veterans",
              f"+{other_pct}% since 2001",
              delta="Rising faster",
              delta_color="inverse",
              help=f"Non-VHA veteran rates rose from {first_vha['other_rate']:.1f} to {latest_vha['other_rate']:.1f} per 100,000 since 2001")
with col4:
    st.metric("6,398 Veterans Lost in 2023",
              "17.5 per day",
              help="44 fewer than in 2022, but the rate remains elevated")

st.markdown("---")

# ============================================================
# SECTION I: THE SCALE
# ============================================================
section_header("I", "The Scale")

st.subheader("Veteran suicide rates have risen dramatically since 2001.")
st.markdown("""
Both veteran and civilian suicide rates have risen since 2001. But the scale of increase
among veterans is substantially larger. Civilian male rates rose approximately 27% from
2001 to 2022. Civilian female rates rose approximately 45%. Veteran rates have risen
further and faster, and the gap between veterans and civilians has widened over the same
period. Age-adjusted rates control for the older average age of the veteran population,
so the divergence is not explained by demographics.
""")

fig_trend = go.Figure()
fig_trend.add_trace(go.Scatter(
    x=rates["year"], y=rates["veteran_rate_male"],
    name="Male Veterans", mode="lines+markers",
    line=dict(color=VET_MALE, width=2.5), marker=dict(size=5, color=VET_MALE)))
fig_trend.add_trace(go.Scatter(
    x=rates["year"], y=rates["veteran_rate_female"],
    name="Female Veterans", mode="lines+markers",
    line=dict(color=VET_FEMALE, width=2.5), marker=dict(size=5, color=VET_FEMALE)))
fig_trend.add_trace(go.Scatter(
    x=rates["year"], y=rates["civilian_rate_male"],
    name="Civilian Males", mode="lines+markers",
    line=dict(color=CIV_MALE, width=2), marker=dict(size=4, color=CIV_MALE)))
fig_trend.add_trace(go.Scatter(
    x=rates["year"], y=rates["civilian_rate_female"],
    name="Civilian Females", mode="lines+markers",
    line=dict(color=CIV_FEMALE, width=2), marker=dict(size=4, color=CIV_FEMALE)))
fig_trend.update_layout(base_layout(
    height=400,
    yaxis_title="Age-Adjusted Rate per 100,000",
    xaxis_title="Year",
    margin=dict(l=40, r=20, t=20, b=40)
))
st.plotly_chart(fig_trend, use_container_width=True, config={"scrollZoom": True})

st.markdown("**Year-over-year rate of change in overall veteran suicide rate:**")
fig_accel = go.Figure()
fig_accel.add_trace(go.Bar(
    x=rates_sorted["year"],
    y=rates_sorted["yoy_change"].round(2),
    marker_color=[VET_FEMALE if v > 0 else SUCCESS
                  for v in rates_sorted["yoy_change"].fillna(0)],
    name="YoY % Change"
))
fig_accel.add_hline(y=0, line_color=NAVY, line_width=1)
fig_accel.update_layout(base_layout(
    height=260,
    yaxis_title="Year-over-Year % Change",
    xaxis_title="Year",
    showlegend=False,
    margin=dict(l=40, r=20, t=10, b=40)
))
st.plotly_chart(fig_accel, use_container_width=True, config={"scrollZoom": True})

# ============================================================
# SECTION II: WHAT IS WORKING
# ============================================================
section_header("II", "What Is Working")

st.subheader("The difference in rate of increase between VHA and non-VHA veterans tells an important story.")
st.markdown(f"""
Both groups have seen suicide rates rise since 2001. The difference in how much tells
the story. Among veterans in VHA care, rates rose from approximately
{first_vha['vha_rate']:.1f} to {latest_vha['vha_rate']:.1f} per 100,000, an increase of
roughly {vha_pct}% over two decades. Among veterans outside the VA system, rates rose from
{first_vha['other_rate']:.1f} to {latest_vha['other_rate']:.1f} per 100,000, an increase of
roughly {other_pct}% over the same period.

That gap is not a coincidence. It reflects a difference in what happens when veterans are
connected to consistent, structured care versus when they are not.

Non-VHA veterans are not a monolithic group. They include veterans who were never enrolled,
veterans who lost eligibility, veterans who live too far from a facility to make enrollment
practical, and veterans who left the military without being connected to VA services at all.
Many have no ongoing relationship with any healthcare system. They are harder to reach,
harder to identify, and harder to support, and the data shows they are bearing the
consequence of that invisibility.
""")

st.markdown(f"""
<div class="callout-box">
VHA user rates rose approximately <strong>{vha_pct}%</strong> from 2001 to 2023
({first_vha['vha_rate']:.1f} to {latest_vha['vha_rate']:.1f} per 100,000).
Non-VHA veteran rates rose approximately <strong>{other_pct}%</strong> over the same period
({first_vha['other_rate']:.1f} to {latest_vha['other_rate']:.1f} per 100,000).
The divergence in rate of increase is the central finding of this data.
</div>
""", unsafe_allow_html=True)

fig_vha = go.Figure()
fig_vha.add_trace(go.Scatter(
    x=vha["year"], y=vha["vha_rate"],
    name="Veterans in VHA Care", mode="lines+markers",
    line=dict(color=VHA_COLOR, width=2.5), marker=dict(size=5, color=VHA_COLOR)))
fig_vha.add_trace(go.Scatter(
    x=vha["year"], y=vha["other_rate"],
    name="Veterans Outside VHA Care", mode="lines+markers",
    line=dict(color=OTHER_COLOR, width=2.5), marker=dict(size=5, color=OTHER_COLOR)))
fig_vha.update_layout(base_layout(
    height=360,
    yaxis_title="Age-Adjusted Rate per 100,000",
    xaxis_title="Year",
    margin=dict(l=40, r=20, t=20, b=40)
))
st.plotly_chart(fig_vha, use_container_width=True, config={"scrollZoom": True})

col_v1, col_v2, col_v3 = st.columns(3)
with col_v1:
    st.metric("VHA User Rate (2023)",
              f"{latest_vha['vha_rate']:.1f} per 100K",
              delta=f"+{latest_vha['vha_rate'] - first_vha['vha_rate']:.1f} since 2001",
              delta_color="inverse")
with col_v2:
    st.metric("Non-VHA Veteran Rate (2023)",
              f"{latest_vha['other_rate']:.1f} per 100K",
              delta=f"+{latest_vha['other_rate'] - first_vha['other_rate']:.1f} since 2001",
              delta_color="inverse")
with col_v3:
    st.metric("Difference in Rate of Increase",
              f"{other_pct - vha_pct} percentage points",
              help=f"Non-VHA veterans saw rates rise {other_pct}% vs {vha_pct}% for VHA users since 2001")

# ============================================================
# SECTION III: WHERE THE SYSTEM IS FAILING
# ============================================================
section_header("III", "Where the System Is Failing")

st.subheader("Populations falling outside the reach of existing systems")
st.markdown("""
The veterans driving the overall rate increase share a common thread: they are outside or
underserved by existing VA systems. Each group represents a different failure of outreach,
access, program design, or data continuity.
""")

# --- Recently Separated ---
st.markdown("### 1. Recently Separated Veterans")
st.markdown("""
The 12 months after leaving active service are the highest-risk period for many veterans.
They lose healthcare coverage, structured routine, peer community, and institutional identity
at the same time. Rates peaked in 2019 at 51.2 per 100,000 and have since declined to
41.2 in 2022, but remain well above the general veteran population average.
""")

col_p1, col_p2 = st.columns(2)
with col_p1:
    st.markdown("**By branch of service, 2022 separation cohort**")
    branch_data = {"Marine Corps": 50.9, "Army": 43.0, "Navy": 38.0, "Air Force": 29.5}
    fig_branch = go.Figure(go.Bar(
        x=list(branch_data.values()),
        y=list(branch_data.keys()),
        orientation="h",
        marker_color=[VET_FEMALE, OTHER_COLOR, VHA_COLOR, CIV_MALE],
        text=[f"{v} per 100K" for v in branch_data.values()],
        textposition="outside"
    ))
    fig_branch.update_layout(base_layout(
        height=260,
        xaxis_title="Rate per 100,000 (12 months post-separation)",
        margin=dict(l=120, r=80, t=20, b=40),
        showlegend=False
    ))
    st.plotly_chart(fig_branch, use_container_width=True)

with col_p2:
    st.markdown("**By pre-separation diagnosis, 2022 separation cohort**")
    diag_data = {
        "Substance Use Disorder": 152.6,
        "Suicidal Ideation": 130.7,
        "Mental Health Diagnosis": 63.2,
        "Overall": 41.2,
    }
    fig_diag = go.Figure(go.Bar(
        x=list(diag_data.values()),
        y=list(diag_data.keys()),
        orientation="h",
        marker_color=[VET_FEMALE, VET_FEMALE, OTHER_COLOR, VHA_COLOR],
        text=[f"{v} per 100K" for v in diag_data.values()],
        textposition="outside"
    ))
    fig_diag.update_layout(base_layout(
        height=260,
        xaxis_title="Rate per 100,000 (12 months post-separation)",
        margin=dict(l=200, r=80, t=20, b=40),
        showlegend=False
    ))
    st.plotly_chart(fig_diag, use_container_width=True)

st.markdown("""
<div class="warning-box">
<strong>The data handoff problem:</strong> The pre-separation diagnosis chart is not just a risk
stratification tool. It is evidence that the Department of Defense already has the clinical
information needed to identify high-risk veterans before they separate. Veterans with documented
suicidal ideation, substance use disorders, and mental health diagnoses are known to DoD systems
months or years before they leave service.

The problem is not a lack of data. It is the absence of a reliable, structured handoff of that
data from DoD to VA at the moment of separation. Veterans who need the most immediate connection
to care are frequently the ones who fall through the gap between two federal agencies that do not
share records in real time. A proper transition of care, built on interoperable data systems and
proactive outreach, is not a clinical aspiration. It is an infrastructure problem with a
technical solution.
</div>
""", unsafe_allow_html=True)

st.caption("Source: VA Annual Report 2025, Figures 11-13. Branch data specific to 2022 cohort.")

# --- Female Veterans ---
st.markdown("### 2. Female Veterans")
st.markdown("""
In the general population, men die by suicide at roughly 3 to 4 times the rate of women.
That gap holds among civilians. It does not hold among veterans.

Female veterans die at approximately 2.4 times the rate of civilian women. Male veterans
die at approximately 1.8 times the rate of civilian men. The relative excess is larger for
female veterans than for male veterans, despite the fact that nearly all veteran suicide
prevention research and programming has historically focused on men, who represent over
90% of the veteran population.

Female veterans are a small group in absolute numbers, which can obscure how severe their
relative risk actually is. The data suggests they are among the most underserved populations
within an already underserved group.
""")

fig_gap = go.Figure()
fig_gap.add_trace(go.Scatter(
    x=gender["year"], y=gender["veteran_female_rate"],
    name="Female Veterans", mode="lines+markers",
    line=dict(color=VET_FEMALE, width=2.5), marker=dict(size=5, color=VET_FEMALE)))
fig_gap.add_trace(go.Scatter(
    x=rates["year"], y=rates["civilian_rate_female"],
    name="Civilian Women", mode="lines+markers",
    line=dict(color=CIV_FEMALE, width=2), marker=dict(size=4, color=CIV_FEMALE)))
fig_gap.add_trace(go.Scatter(
    x=gender["year"], y=gender["veteran_male_rate"],
    name="Male Veterans (context)", mode="lines+markers",
    line=dict(color=VET_MALE, width=1.5, dash="dot"),
    marker=dict(size=3, color=VET_MALE)))
fig_gap.update_layout(base_layout(
    height=320,
    yaxis_title="Age-Adjusted Rate per 100,000",
    xaxis_title="Year",
    margin=dict(l=40, r=20, t=20, b=40)
))
st.plotly_chart(fig_gap, use_container_width=True, config={"scrollZoom": True})

year_sel = st.slider("Explore by year",
                     int(gender["year"].min()),
                     2022, 2022)
st.caption("Civilian comparison data from CDC WISQARS is available through 2022.")
row = gender[gender["year"] == year_sel].iloc[0]
civ_row = rates[rates["year"] == year_sel].iloc[0]
fv_rate = row['veteran_female_rate']
civ_rate = civ_row['civilian_rate_female']

col_fa, col_fb, col_fc = st.columns(3)
with col_fa:
    if pd.isna(fv_rate):
        st.metric("Female Veteran Rate", "Not available")
    else:
        st.metric("Female Veteran Rate", f"{fv_rate:.1f} per 100K")
with col_fb:
    if pd.isna(civ_rate):
        st.metric("Civilian Women Rate", "Not available")
    else:
        st.metric("Civilian Women Rate", f"{civ_rate:.1f} per 100K")
with col_fc:
    if pd.isna(fv_rate) or pd.isna(civ_rate) or civ_rate == 0:
        st.metric("Female Veteran Excess", "Not available")
    else:
        ratio = fv_rate / civ_rate
        st.metric("Female Veteran Excess", f"{ratio:.1f}x higher")

# --- Homeless Veterans ---
st.markdown("### 3. Homeless Veterans")
st.markdown("""
Among VHA users, those with a documented homelessness diagnosis have suicide rates that
substantially exceed all other subgroups. The disparity has more than doubled since 2001,
suggesting that homelessness intersects with suicide risk in ways that existing VA care
structures are not fully reaching.
""")

col_h1, col_h2, col_h3 = st.columns(3)
with col_h1:
    st.metric("Homeless vs. Non-Homeless VHA Users (2001)", "72.5% higher rate")
with col_h2:
    st.metric("Homeless vs. Non-Homeless VHA Users (2023)", "146% higher rate")
with col_h3:
    st.metric("Growth in Disparity Since 2001", "+73.5 percentage points",
              help="146 minus 72.5 equals 73.5 percentage points. The relative gap has more than doubled.")

st.caption("Source: VA Annual Report 2025, Figure 25. Homelessness identified via ICD codes at VHA encounters.")

st.markdown("""
<div style="
    background-color: #FDEDEC;
    border-left: 4px solid #C0392B;
    padding: 1rem 1.25rem;
    border-radius: 4px;
    margin: 1.5rem 0;
    color: #0D1B2A;
">
These populations are not mutually exclusive. A recently separated veteran experiencing
homelessness is at compounded risk. A female veteran in a rural state with no nearby VA
facility faces multiple barriers simultaneously. The data presented here looks at each
group in isolation, but the lived experience of the highest-risk veterans often involves
several of these factors at once.
</div>
""", unsafe_allow_html=True)

# --- Firearm Access ---
st.markdown("### Firearm Access as a Structural Factor")
st.markdown("""
Firearms are involved in nearly three out of four veteran suicide deaths, substantially
higher than for non-veteran adults. With a case fatality rate of approximately 85-90%,
firearm suicide attempts are rarely survived. Lethal means counseling and secure storage
programs are among the few interventions with strong evidence for impact, but they require
reaching veterans before crisis, which returns to the access problem.
""")

col_fw1, col_fw2 = st.columns(2)
with col_fw1:
    st.markdown("**Firearm involvement in suicide deaths, 2023**")
    firearm_data = {
        "Male Veterans": 74.5,
        "All Veterans": 73.3,
        "Female Veterans": 49.0,
        "Civilian Men": 58.2,
        "Civilian Women": 35.3,
        "All Non-Veterans": 52.9,
    }
    fig_fw = go.Figure(go.Bar(
        x=list(firearm_data.values()),
        y=list(firearm_data.keys()),
        orientation="h",
        marker_color=[VET_MALE, NAVY, VET_FEMALE, CIV_MALE, CIV_FEMALE, "#888888"],
        text=[f"{v}%" for v in firearm_data.values()],
        textposition="outside"
    ))
    fig_fw.update_layout(
        plot_bgcolor="white", paper_bgcolor="white", font_color=NAVY,
        yaxis=dict(gridcolor="#eeeeee"),
        xaxis=dict(range=[0, 90], gridcolor="#eeeeee"),
        legend=dict(bgcolor="white", bordercolor="#cccccc", borderwidth=1),
        dragmode="pan",
        height=300,
        xaxis_title="% of suicide deaths involving firearms",
        margin=dict(l=140, r=60, t=20, b=40),
        showlegend=False
    )
    st.plotly_chart(fig_fw, use_container_width=True)

with col_fw2:
    st.markdown("**Change in veteran method-specific suicide rates, 2001-2023**")
    method_change = {
        "Firearm": 67.0,
        "Suffocation": 53.0,
        "Other Methods": 26.3,
        "Poisoning": -16.3,
    }
    fig_method = go.Figure(go.Bar(
        x=list(method_change.values()),
        y=list(method_change.keys()),
        orientation="h",
        marker_color=[VET_FEMALE if v > 0 else SUCCESS for v in method_change.values()],
        text=[f"+{v}%" if v > 0 else f"{v}%" for v in method_change.values()],
        textposition="outside"
    ))
    fig_method.add_vline(x=0, line_color=NAVY, line_width=1)
    fig_method.update_layout(
        plot_bgcolor="white", paper_bgcolor="white", font_color=NAVY,
        yaxis=dict(gridcolor="#eeeeee"),
        xaxis=dict(range=[-30, 90], gridcolor="#eeeeee"),
        legend=dict(bgcolor="white", bordercolor="#cccccc", borderwidth=1),
        dragmode="pan",
        height=300,
        xaxis_title="% change since 2001",
        margin=dict(l=120, r=60, t=20, b=40),
        showlegend=False
    )
    st.plotly_chart(fig_method, use_container_width=True)

st.caption("Source: VA Annual Report 2025, Figures 14-17 and Table 4.")

# ============================================================
# SECTION IV: WHERE TO INTERVENE
# ============================================================
section_header("IV", "Where to Intervene")

st.subheader("The geography of the crisis")
st.markdown("""
The states with the highest veteran suicide rates tend to be rural, with lower population
density and greater distances between veterans and VA facilities. These are the conditions
where telehealth, data-driven outreach, and digital care coordination have the highest
potential to close the access gap.

Reaching veterans outside the VA system before crisis is as much a technology and
infrastructure problem as a clinical one.
""")

st.markdown("""
<div class="callout-box">
<strong>The access gap in geographic terms:</strong> Veterans not connected to VA care are the
fastest-growing risk group. Identifying them, reaching them, and connecting them to care
requires data infrastructure, outreach platforms, and telehealth capacity, particularly
in rural and high-rate states.
</div>
""", unsafe_allow_html=True)

col_f1, col_f2 = st.columns(2)
with col_f1:
    regions = sorted(va_state["region"].dropna().unique().tolist())
    region_sel = st.multiselect("Highlight region on map", regions,
                                placeholder="All regions shown by default")
with col_f2:
    year_min = int(va_state["year"].min())
    year_max = int(va_state["year"].max())
    year_range = st.slider("Year range", year_min, year_max, (2019, 2023))

state_list = sorted(va_state["state"].dropna().unique().tolist())
state_sel = st.multiselect(
    "Compare specific states (max 5)",
    state_list,
    placeholder="Select up to 5 states to compare",
    max_selections=5
)

map_df = va_state[
    (va_state["year"] >= year_range[0]) &
    (va_state["year"] <= year_range[1])
].copy()

map_agg = map_df.groupby(["state", "region"]).agg(
    veteran_suicides=("veteran_suicides", "sum"),
    population=("population", "sum")
).reset_index()
map_agg["crude_rate"] = (map_agg["veteran_suicides"] / map_agg["population"] * 100000).round(2)
map_agg = map_agg.sort_values("crude_rate", ascending=False)

state_abbrev = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY"
}
map_agg["abbrev"] = map_agg["state"].map(state_abbrev)
map_agg = map_agg.dropna(subset=["abbrev"])

map_highlighted = set()
if region_sel:
    region_states = va_state[va_state["region"].isin(region_sel)]["state"].unique()
    map_highlighted.update(region_states)

fig_map = go.Figure()
if map_highlighted:
    fig_map.add_trace(go.Choropleth(
        locations=map_agg["abbrev"],
        z=[1] * len(map_agg),
        locationmode="USA-states",
        colorscale=[[0, "#eeeeee"], [1, "#eeeeee"]],
        showscale=False,
        hoverinfo="skip",
        marker_line_color="white",
        marker_line_width=0.5
    ))
    highlight_df = map_agg[map_agg["state"].isin(map_highlighted)]
else:
    highlight_df = map_agg

fig_map.add_trace(go.Choropleth(
    locations=highlight_df["abbrev"],
    z=highlight_df["crude_rate"],
    locationmode="USA-states",
    colorscale=[
        [0, "#FEF9E7"],
        [0.3, "#F4D03F"],
        [0.6, "#E67E22"],
        [1, "#922B21"]
    ],
    zmin=map_agg["crude_rate"].min(),
    zmax=map_agg["crude_rate"].max(),
    colorbar_title="Rate per 100K",
    hovertemplate="<b>%{text}</b><br>Veteran Suicide Rate: %{z:.1f} per 100K<extra></extra>",
    text=highlight_df["state"],
    marker_line_color="white",
    marker_line_width=0.5
))

fig_map.update_layout(
    geo=dict(scope="usa", bgcolor="white"),
    paper_bgcolor="white",
    font_color=NAVY,
    margin=dict(l=0, r=0, t=0, b=0),
    height=500
)
st.plotly_chart(fig_map, use_container_width=True)

if state_sel:
    nat_avg = va_state.groupby("year").apply(
        lambda x: (x["veteran_suicides"].sum() / x["population"].sum() * 100000)
    ).reset_index()
    nat_avg.columns = ["year", "national_rate"]

    st.markdown("#### Trend comparison: selected states vs. national veteran average")
    fig_compare = go.Figure()
    fig_compare.add_trace(go.Scatter(
        x=nat_avg["year"], y=nat_avg["national_rate"],
        name="National Veteran Avg", mode="lines",
        line=dict(color="#cccccc", width=2, dash="dash")))
    for i, state in enumerate(sorted(state_sel)):
        state_trend = va_state[va_state["state"] == state].sort_values("year")
        color = PALETTE[i % len(PALETTE)]
        fig_compare.add_trace(go.Scatter(
            x=state_trend["year"], y=state_trend["crude_rate"],
            name=state, mode="lines+markers",
            line=dict(color=color, width=2.5),
            marker=dict(size=5, color=color)))
    fig_compare.update_layout(base_layout(
        height=360,
        yaxis_title="Veteran suicide rate per 100,000",
        xaxis_title="Year",
        margin=dict(l=40, r=20, t=20, b=40)
    ))
    st.plotly_chart(fig_compare, use_container_width=True, config={"scrollZoom": True})

    st.markdown("#### Male vs. female veteran suicide deaths: selected states")
    st.caption("Raw death counts shown. Sex-specific population denominators are not publicly "
               "available at the state level. Cells with fewer than 10 deaths are suppressed "
               "by the VA and appear as gaps.")
    fig_sex = go.Figure()
    for i, state in enumerate(sorted(state_sel)):
        male_data = sex_state[(sex_state["state"] == state) & (sex_state["sex"] == "Male")]
        female_data = sex_state[(sex_state["state"] == state) & (sex_state["sex"] == "Female")]
        cm = PALETTE_M[i % len(PALETTE_M)]
        cf = PALETTE_F[i % len(PALETTE_F)]
        fig_sex.add_trace(go.Scatter(
            x=male_data["year"], y=male_data["veteran_suicides"],
            name=f"{state} — Male", mode="lines+markers",
            line=dict(color=cm, width=2), marker=dict(size=4, color=cm)))
        fig_sex.add_trace(go.Scatter(
            x=female_data["year"], y=female_data["veteran_suicides"],
            name=f"{state} — Female", mode="lines+markers",
            line=dict(color=cf, width=2, dash="dot"), marker=dict(size=4, color=cf)))
    fig_sex.update_layout(base_layout(
        height=320,
        yaxis_title="Veteran suicide deaths (count)",
        xaxis_title="Year",
        margin=dict(l=40, r=20, t=20, b=40)
    ))
    st.plotly_chart(fig_sex, use_container_width=True, config={"scrollZoom": True})

    st.markdown("#### Key stats for selected states (most recent year)")
    metric_cols = st.columns(min(len(state_sel), 4))
    for i, state in enumerate(sorted(state_sel)):
        state_rows = va_state[va_state["state"] == state].sort_values("year")
        if len(state_rows) == 0:
            continue
        latest_s = state_rows.iloc[-1]
        first_s = state_rows.iloc[0]
        with metric_cols[i % len(metric_cols)]:
            rate_val = latest_s['crude_rate']
            first_val = first_s['crude_rate']
            if pd.isna(rate_val):
                st.metric(state, "Suppressed",
                          help="Fewer than 10 deaths in most recent year")
            else:
                delta = f"{rate_val - first_val:+.1f} since {int(first_s['year'])}" if not pd.isna(first_val) else None
                st.metric(
                    state,
                    f"{rate_val:.1f} per 100K",
                    delta=delta,
                    delta_color="inverse"
                )

st.markdown("---")

col_m1, col_m2 = st.columns(2)
with col_m1:
    st.markdown("**Highest rate states (selected period)**")
    for _, r in map_agg.head(5).iterrows():
        st.markdown(f"- {r['state']}: {r['crude_rate']:.1f} per 100K")
with col_m2:
    st.markdown("**Lowest rate states (selected period)**")
    for _, r in map_agg.tail(5).iterrows():
        st.markdown(f"- {r['state']}: {r['crude_rate']:.1f} per 100K")

st.caption("Source: VA State Data Appendix 2025. Veteran-specific suicide rates. "
           "National average in comparison chart is veteran-specific.")

# --- SUMMARY ---
st.markdown("---")
st.subheader("What the Data Points To")
st.markdown("""
Taken together, the findings across this dashboard describe a system with clear structural gaps.
The veterans at highest risk are often those least connected to existing care infrastructure,
and the barriers are not primarily clinical. They are logistical, geographic, and technological.
""")

col_s1, col_s2 = st.columns(2)

with col_s1:
    st.markdown("""
    **Continuity of care at separation**
    DoD holds clinical data on high-risk veterans before they separate. Veterans with documented
    suicidal ideation face post-separation suicide rates of 130.7 per 100,000 in the following
    12 months. That information exists. What does not exist is a reliable, real-time handoff
    of that data to VA at the moment of transition. Building that bridge is an infrastructure
    problem, not a clinical one.

    **Female veterans**
    Female veterans die by suicide at a higher relative rate compared to their civilian peers
    than male veterans do. They represent a small share of the veteran population, which
    has historically meant less research attention, less program development, and less
    data granularity. The suppression of female veteran data at the state level in this
    dashboard is itself a reflection of how small and undercounted this population remains.

    **Veterans outside the VA system**
    Non-VHA veterans are the fastest-growing risk group, with rates rising 65% since 2001
    compared to 18% among VHA users. Many have no ongoing relationship with any healthcare
    system. Reaching them requires knowing where they are, which requires data systems that
    can identify and locate veterans who have never enrolled in VA care.
    """)

with col_s2:
    st.markdown("""
    **Rural and high-rate states**
    The states with the highest veteran suicide rates are disproportionately rural. Distance
    from VA facilities is a documented barrier to enrollment and care. Telehealth has expanded
    access significantly, but its reach depends on broadband infrastructure, device access,
    and proactive outreach to veterans who may not know what is available to them.

    **Homeless veterans**
    Among VHA users, those with a homelessness diagnosis face suicide rates 146% higher than
    those without. The disparity has more than doubled since 2001. Homeless veterans are often
    cycling between VA systems, emergency services, and periods of no contact at all. Consistent
    care coordination across those transitions is a data and systems problem as much as a
    clinical one.

    **Firearm access**
    Firearms are involved in 73% of veteran suicide deaths. The case fatality rate for firearm
    suicide attempts is approximately 85-90%. Lethal means counseling and secure storage programs
    have evidence behind them, but they only work if veterans are in contact with someone who
    can provide them. Every gap in outreach and access is also a gap in lethal means intervention.
    """)

st.markdown("""
<div class="callout-box">
The common thread across each of these gaps is not a shortage of clinical knowledge about
what works. It is a shortage of the infrastructure needed to reach veterans before crisis,
maintain continuity across transitions, and share data across the federal systems that
collectively hold the information needed to act. Those are solvable problems.
</div>
""", unsafe_allow_html=True)

# --- METHODOLOGY ---
st.markdown("---")
st.subheader("Data Sources and Methodology")
st.markdown("""
<div class="methodology-box">

<strong>Rate methodology:</strong> All national trend rates are age-adjusted per 100,000 population.
Age adjustment uses the VA standard direct adjustment methodology, controlling for differences
in age distribution between the veteran and civilian populations. State-level rates from the VA
State Data Appendix are unadjusted crude rates due to data availability at the state level.

<strong>Veteran definition:</strong> Individuals identified as veterans on U.S. death certificates.
VHA user status is defined as having at least one VHA inpatient or outpatient encounter in the
year prior to or the year of death.

<strong>Suppression:</strong> State-level data for cells with fewer than 10 deaths are suppressed
by the VA and appear as null values in this dashboard. Sex-stratified state data is particularly
affected in smaller states and for female veterans.

<strong>Data coverage:</strong> National veteran trend data covers 2001-2023. State-level data
covers 2001-2023. Post-separation data covers separation cohorts 2010-2022. CDC WISQARS
civilian comparison data covers 2001-2022.

<strong>Sources:</strong> VA Office of Suicide Prevention, 2025 National Veteran Suicide Prevention
Annual Report (data through 2023); VA State Data Appendix 2025; CDC WISQARS Fatal Injury Reports.

</div>
""", unsafe_allow_html=True)

st.markdown("---")
st.caption("Built with Python, dbt, DuckDB, and Streamlit. "
           "Data: VA Office of Suicide Prevention · CDC WISQARS · 2025 National Veteran Suicide Prevention Annual Report.")