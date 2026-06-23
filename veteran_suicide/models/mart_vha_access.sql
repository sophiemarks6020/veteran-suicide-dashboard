with vha as (
    select
        year,
        CAST(total_crude_rate AS DOUBLE) as vha_rate,
        CAST(male_crude_rate AS DOUBLE) as vha_rate_male,
        CAST(female_crude_rate AS DOUBLE) as vha_rate_female
    from raw_va_vha_user
    where year between 2001 and 2023
),

other as (
    select
        year,
        CAST(total_crude_rate AS DOUBLE) as other_rate,
        CAST(male_crude_rate AS DOUBLE) as other_rate_male,
        CAST(female_crude_rate AS DOUBLE) as other_rate_female
    from raw_va_other_veteran
    where year between 2001 and 2023
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