
    
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  select id from `dbt_tenant_novasight_demo_staging`.`audit_smoke` where id < 1
  
  
    ) dbt_internal_test