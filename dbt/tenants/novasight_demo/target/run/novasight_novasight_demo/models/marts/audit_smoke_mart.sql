
  
    
    
    
        
         


        insert into `dbt_tenant_novasight_demo_marts`.`audit_smoke_mart`
        ("id", "msg")
select * from `dbt_tenant_novasight_demo_staging`.`audit_smoke`
  