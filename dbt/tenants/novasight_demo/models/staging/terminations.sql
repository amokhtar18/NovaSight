{{
  config(
    materialized='table',

    schema='staging',

    tags=['staging', 'tenant_novasight_demo.raw']
  )
}}WITH source AS (
    SELECT *

    FROM iceberg('s3://tenant-novasight-demo/iceberg/tenant_novasight_demo/raw/terminations/')

),

renamed AS (
    SELECT


        -- Tenant isolation
        tenant_id AS tenant_id,



        -- 

        id AS None,





        -- 

        branch AS None,





        -- 

        staff_id AS None,





        -- 

        nid AS None,





        -- 

        name AS None,





        -- 

        department AS None,





        -- 

        position AS None,





        -- 

        nationality AS None,





        -- 

        hire_date AS None,





        -- 

        contract_start_date AS None,





        -- 

        contract_end_date AS None,





        -- 

        termination_reason AS None,





        -- 

        notes AS None,





        -- 

        termination_date AS None,





        -- 

        entry_user AS None,





        -- 

        created_at AS None




    FROM source
)

SELECT * FROM renamed
