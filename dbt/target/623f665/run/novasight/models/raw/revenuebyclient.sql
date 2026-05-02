
  
    
    
    
        
         


        insert into `tenant_novasight_demo`.`revenuebyclient`
        ("branch_name", "month", "client", "client_category", "care_type", "speciality", "service_category_code", "service_category", "service_code", "service_description", "episodes", "revenue", "qty", "_dlt_load_id", "_dlt_id")

SELECT *
FROM s3(
    'http://minio:9000/tenant-novasight-demo/lake/tenant_novasight_demo_raw/revenuebyclient/*.jsonl',
    'minioadmin',
    'minioadmin',
    'JSONEachRow',
    'auto',
    'gzip'
)
  