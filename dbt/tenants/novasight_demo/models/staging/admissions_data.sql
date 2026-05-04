{{
  config(
    materialized='table',

    schema='staging',

    tags=['staging', 'tenant_novasight_demo.raw']
  )
}}WITH source AS (
    SELECT *

    FROM iceberg('s3://tenant-novasight-demo/iceberg/tenant_novasight_demo/raw/admissions/')

),

renamed AS (
    SELECT


        -- Tenant isolation
        tenant_id AS tenant_id,



        -- 


        admission_no,





        -- 


        patient_id,





        -- 


        episode_no,





        -- 


        admit_date,





        -- 


        physical_discharge_date




    FROM source
)

SELECT * FROM renamed
