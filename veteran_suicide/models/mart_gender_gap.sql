select
    year,
    TRY_CAST(NULLIF(TRIM(CAST(female_crude_rate AS VARCHAR)), '.') AS DOUBLE) as veteran_female_rate,
    TRY_CAST(NULLIF(TRIM(CAST(male_crude_rate AS VARCHAR)), '.') AS DOUBLE) as veteran_male_rate,
    TRY_CAST(NULLIF(TRIM(CAST(female_crude_rate AS VARCHAR)), '.') AS DOUBLE)
        / NULLIF(TRY_CAST(NULLIF(TRIM(CAST(male_crude_rate AS VARCHAR)), '.') AS DOUBLE), 0) as female_to_male_ratio
from raw_va_veteran
where year between 2001 and 2023
order by year