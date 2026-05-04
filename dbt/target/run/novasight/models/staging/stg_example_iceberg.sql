

  create or replace view `tenant_335daa54-4884-4929-9e15-76806804a872`.`stg_example_iceberg` 
  
    
  
  
    
    
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
                    
                    