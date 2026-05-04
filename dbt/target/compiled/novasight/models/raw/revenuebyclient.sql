

SELECT *
FROM s3(
    'http://minio:9000/tenant-335daa54-4884-4929-9e15-76806804a872/lake/tenant_335daa54-4884-4929-9e15-76806804a872_raw/revenuebyclient/*.jsonl',
    'minioadmin',
    'minioadmin',
    'JSONEachRow',
    'auto',
    'gzip'
)