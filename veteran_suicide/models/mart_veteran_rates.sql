with veteran as (
    select
        year,
        CAST(total_crude_rate AS DOUBLE) as veteran_rate_all,
        CAST(male_crude_rate AS DOUBLE) as veteran_rate_male,
        CAST(female_crude_rate AS DOUBLE) as veteran_rate_female
    from raw_va_veteran
    where year between 2001 and 2023
),

civilian as (
    select
        "Year" as year,
        max(case when sex = 'male' then CAST("Crude Rate" AS DOUBLE) end) as civilian_rate_male,
        max(case when sex = 'female' then CAST("Crude Rate" AS DOUBLE) end) as civilian_rate_female
    from raw_wisqars
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