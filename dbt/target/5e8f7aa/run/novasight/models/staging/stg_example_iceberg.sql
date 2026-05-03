

  create or replace view `tenant_novasight_demo`.`stg_example_iceberg` 
  
    
  
  
    
    
  as (
    




  -- Non-lake targets: Create empty placeholder
  -- (marts should use ref() to the actual materialized source)
  SELECT
    NULL as id,
    NULL as name,
    now() as _loaded_at
  WHERE 1 = 0
  

    
  )
      
      
                    -- end_of_sql
                    
                    