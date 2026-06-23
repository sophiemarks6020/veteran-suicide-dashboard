import duckdb
import pandas as pd

DB_PATH = "data/veteran_suicide.duckdb"
con = duckdb.connect(DB_PATH)

def load_va_sheet(sheet_name):
    df = pd.read_excel(
        "data/raw/National_Suicide_Data_Appendix_2021-2023_508.xlsx",
        sheet_name=sheet_name,
        header=2
    )
    # Rename columns by position — most reliable given messy headers
    clean = [
        'year', 'total_deaths', 'total_population', 'total_crude_rate', 'total_adj_rate',
        'male_deaths', 'male_population', 'male_crude_rate', 'male_adj_rate',
        'female_deaths', 'female_population', 'female_crude_rate', 'female_adj_rate'
    ]
    df.columns = clean[:len(df.columns)]
    # Drop rows where year is not a valid integer
    df = df[pd.to_numeric(df['year'], errors='coerce').notna()].copy()
    df['year'] = df['year'].astype(int)
    return df

# VA Veteran
df = load_va_sheet('Veteran')
con.execute("DROP TABLE IF EXISTS raw_va_veteran")
con.execute("CREATE TABLE raw_va_veteran AS SELECT * FROM df")
print("✓ raw_va_veteran")

# VA VHA User
df = load_va_sheet('Recent Veteran VHA User')
con.execute("DROP TABLE IF EXISTS raw_va_vha_user")
con.execute("CREATE TABLE raw_va_vha_user AS SELECT * FROM df")
print("✓ raw_va_vha_user")

# VA Other Veteran
df = load_va_sheet('Other Veteran')
con.execute("DROP TABLE IF EXISTS raw_va_other_veteran")
con.execute("CREATE TABLE raw_va_other_veteran AS SELECT * FROM df")
print("✓ raw_va_other_veteran")

# WISQARS national (men + women CSVs)
df_men = pd.read_csv("data/raw/reports-data-men-export.csv")
df_men["sex"] = "male"
df_women = pd.read_csv("data/raw/reports-data-women-export.csv")
df_women["sex"] = "female"
df = pd.concat([df_men, df_women], ignore_index=True)
con.execute("DROP TABLE IF EXISTS raw_wisqars")
con.execute("CREATE TABLE raw_wisqars AS SELECT * FROM df")
print("✓ raw_wisqars")

# WISQARS race (national, 2001-2020)
df = pd.read_csv("data/raw/wisqars_race.csv", skiprows=0)
df = df[df["Race"].isin([
    "White", "Black",
    "American Indian / Alaska Native",
    "Asian / HI Native / Pac. Islander"
])].copy()
df = df.rename(columns={
    "Race": "race",
    "Deaths": "deaths",
    "Population": "population",
    "Crude Rate": "crude_rate",
    "Age-Adjusted Rate": "age_adjusted_rate"
})
df = df[["race", "deaths", "population", "crude_rate", "age_adjusted_rate"]]
for col in ["deaths", "population"]:
    df[col] = df[col].astype(str).str.replace(",", "").str.strip()
    df[col] = pd.to_numeric(df[col], errors="coerce")
df["crude_rate"] = pd.to_numeric(df["crude_rate"], errors="coerce")
df["age_adjusted_rate"] = pd.to_numeric(df["age_adjusted_rate"], errors="coerce")
con.execute("DROP TABLE IF EXISTS raw_wisqars_race")
con.execute("CREATE TABLE raw_wisqars_race AS SELECT * FROM df")
print("✓ raw_wisqars_race")

# WISQARS state male
df_male = pd.read_csv("data/raw/wisqars_state_male.csv")
df_male["sex"] = "male"
for col in ["Deaths", "Population"]:
    df_male[col] = df_male[col].astype(str).str.replace(",", "").str.strip()
    df_male[col] = pd.to_numeric(df_male[col], errors="coerce")
df_male["Crude Rate"] = pd.to_numeric(df_male["Crude Rate"], errors="coerce")
df_male["Age-Adjusted Rate"] = pd.to_numeric(df_male["Age-Adjusted Rate"], errors="coerce")

# WISQARS state female
df_female = pd.read_csv("data/raw/wisqars_state_female.csv")
df_female["sex"] = "female"
for col in ["Deaths", "Population"]:
    df_female[col] = df_female[col].astype(str).str.replace(",", "").str.strip()
    df_female[col] = pd.to_numeric(df_female[col], errors="coerce")
df_female["Crude Rate"] = pd.to_numeric(df_female["Crude Rate"], errors="coerce")
df_female["Age-Adjusted Rate"] = pd.to_numeric(df_female["Age-Adjusted Rate"], errors="coerce")

df_state = pd.concat([df_male, df_female], ignore_index=True)
df_state = df_state.rename(columns={
    "State": "state",
    "Deaths": "deaths",
    "Population": "population",
    "Crude Rate": "crude_rate",
    "Age-Adjusted Rate": "age_adjusted_rate"
})
df_state = df_state[["state", "sex", "deaths", "population", "crude_rate", "age_adjusted_rate"]]
con.execute("DROP TABLE IF EXISTS raw_wisqars_state")
con.execute("CREATE TABLE raw_wisqars_state AS SELECT * FROM df_state")
print("✓ raw_wisqars_state")

# VA State Appendix - Veteran Suicides by State
df = pd.read_excel('data/raw/va_state_appendix.xlsx', sheet_name='Veteran Suicides by State', header=2)
df.columns = ['year', 'region', 'state', 'veteran_suicides', 'population', 'crude_rate']
df = df[pd.to_numeric(df['year'], errors='coerce').notna()].copy()
df['year'] = df['year'].astype(int)
df['population'] = pd.to_numeric(df['population'], errors='coerce')
df['crude_rate'] = pd.to_numeric(df['crude_rate'], errors='coerce')
df['veteran_suicides'] = pd.to_numeric(df['veteran_suicides'], errors='coerce')
con.execute("DROP TABLE IF EXISTS raw_va_state")
con.execute("CREATE TABLE raw_va_state AS SELECT * FROM df")
print("✓ raw_va_state")

# VA State Appendix - Veteran Suicides by Sex
df = pd.read_excel('data/raw/va_state_appendix.xlsx', sheet_name='Veteran Suicides by Sex', header=2)
df.columns = ['year', 'region', 'state', 'sex', 'veteran_suicides']
df = df[pd.to_numeric(df['year'], errors='coerce').notna()].copy()
df['year'] = df['year'].astype(int)
# suppressed values like <10 become null
df['veteran_suicides'] = pd.to_numeric(df['veteran_suicides'], errors='coerce')
con.execute("DROP TABLE IF EXISTS raw_va_state_sex")
con.execute("CREATE TABLE raw_va_state_sex AS SELECT * FROM df")
print("✓ raw_va_state_sex")

con.close()
print("\nAll tables loaded successfully.")