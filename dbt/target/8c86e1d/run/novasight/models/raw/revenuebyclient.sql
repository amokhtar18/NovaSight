
  
    
    
    
        
         


        insert into `tenant_novasight_demo`.`revenuebyclient__dbt_backup`
        ("branch_name", "d_branch_id", "mrn", "creditor", "company", "unified_speciality", "attendance_type", "category", "product", "revenue", "yearmonth", "_dlt_load_id", "_dlt_id")

SELECT *
FROM s3(
    'http://minio:9000/tenant-novasight-demo/lake/tenant_novasight_demo_raw/revenuebyclient/*.jsonl',
    'minioadmin',
    'minioadmin',
    'JSONEachRow',
    'auto',
    'gzip'
)
  