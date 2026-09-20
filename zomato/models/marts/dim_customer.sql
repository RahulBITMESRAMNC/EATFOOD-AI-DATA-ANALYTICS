select 
customer_id,
customer_name,
email,
age,
Case WHEN age<25 then 'Gen z'
     WHEN age<40 then 'Millennial'
     WHEN age<25 then 'Gen X'
     WHEN age is null then 'Unknown'
     ELSE 'Boomer' END as age_segment,

gender,
marital_status,
occupation,
income_band,
education,
family_size
from {{ref('stg_users')}}
