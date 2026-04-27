{{
  config(
    materialized='table',
    tags=['staging', 'tenant_novasight_demo.raw']
  )
}}WITH source AS (
    SELECT *

    FROM iceberg('s3://novasight-novasight-demo/iceberg/tenant_novasight_demo/raw/users/')

),

renamed AS (
    SELECT


        -- Tenant isolation
        tenant_id AS tenant_id,



        -- 

        id AS None,





        -- 

        username AS None,





        -- 

        role AS None,





        -- 

        branch AS None




    FROM source
)

SELECT * FROM renamed
