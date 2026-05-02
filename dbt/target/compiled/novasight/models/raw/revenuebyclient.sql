

SELECT *
FROM s3(
    'http://minio:9000/tenant-novasight-demo/lake/tenant_novasight_demo_raw/revenuebyclient/*.jsonl',
    'minioadmin',
    'minioadmin',
    'JSONEachRow',
    'auto',
    'gzip'
)