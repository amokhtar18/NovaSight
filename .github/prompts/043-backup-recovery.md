# 043 - Backup and Recovery

## Metadata

```yaml
prompt_id: "043"
phase: 6
agent: "@infrastructure"
model: "sonnet 4.5"
priority: P0
estimated_effort: "3 days"
dependencies: ["002", "038"]
```

## Objective

Implement backup and recovery procedures for all data stores.

## Task Description

Create automated backup systems with point-in-time recovery capabilities.

## Requirements

### PostgreSQL Backup

```yaml
# backup/postgresql/backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgresql-backup
  namespace: novasight
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: backup-sa
          containers:
            - name: backup
              image: postgres:15
              command:
                - /bin/bash
                - -c
                - |
                  set -e
                  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
                  BACKUP_FILE="postgresql_${TIMESTAMP}.sql.gz"
                  
                  echo "Starting PostgreSQL backup..."
                  pg_dumpall -h $PGHOST -U $PGUSER | gzip > /backup/${BACKUP_FILE}
                  
                  echo "Uploading to S3..."
                  aws s3 cp /backup/${BACKUP_FILE} s3://${S3_BUCKET}/postgresql/${BACKUP_FILE}
                  
                  echo "Cleaning up local file..."
                  rm /backup/${BACKUP_FILE}
                  
                  echo "Backup completed: ${BACKUP_FILE}"
              env:
                - name: PGHOST
                  value: postgresql-service
                - name: PGUSER
                  valueFrom:
                    secretKeyRef:
                      name: postgresql-credentials
                      key: username
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: postgresql-credentials
                      key: password
                - name: S3_BUCKET
                  value: novasight-backups
              volumeMounts:
                - name: backup-volume
                  mountPath: /backup
          volumes:
            - name: backup-volume
              emptyDir: {}
          restartPolicy: OnFailure
```

### ClickHouse Backup

```yaml
# backup/clickhouse/backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: clickhouse-backup
  namespace: novasight
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: altinity/clickhouse-backup:2.4.0
              command:
                - /bin/bash
                - -c
                - |
                  set -e
                  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
                  
                  echo "Creating ClickHouse backup..."
                  clickhouse-backup create "backup_${TIMESTAMP}"
                  
                  echo "Uploading to S3..."
                  clickhouse-backup upload "backup_${TIMESTAMP}"
                  
                  echo "Cleaning old backups..."
                  clickhouse-backup delete local "backup_${TIMESTAMP}"
                  
                  # Keep only last 7 days of backups
                  clickhouse-backup list remote | tail -n +8 | while read backup; do
                    clickhouse-backup delete remote "$backup"
                  done
                  
                  echo "Backup completed"
              volumeMounts:
                - name: config
                  mountPath: /etc/clickhouse-backup/config.yml
                  subPath: config.yml
          volumes:
            - name: config
              configMap:
                name: clickhouse-backup-config
          restartPolicy: OnFailure

---
# backup/clickhouse/config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: clickhouse-backup-config
  namespace: novasight
data:
  config.yml: |
    general:
      remote_storage: s3
      max_file_size: 1099511627776
      disable_progress_bar: true
    
    clickhouse:
      host: clickhouse-service
      port: 9000
      username: default
      password_file: /etc/secrets/clickhouse-password
    
    s3:
      bucket: novasight-backups
      path: clickhouse
      region: us-east-1
      compression_format: gzip
```

### Backup Service

```python
# backend/app/services/backup_service.py
import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.utils.logger import get_logger

logger = get_logger('backup')

class BackupService:
    """Service for managing backups."""
    
    def __init__(self, bucket: str, region: str = 'us-east-1'):
        self.bucket = bucket
        self.s3 = boto3.client('s3', region_name=region)
    
    def list_backups(
        self,
        service: str,
        days: int = 30
    ) -> List[Dict]:
        """List available backups for a service."""
        prefix = f'{service}/'
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        response = self.s3.list_objects_v2(
            Bucket=self.bucket,
            Prefix=prefix
        )
        
        backups = []
        for obj in response.get('Contents', []):
            if obj['LastModified'].replace(tzinfo=None) > cutoff:
                backups.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'created_at': obj['LastModified'].isoformat(),
                    'service': service,
                })
        
        return sorted(backups, key=lambda x: x['created_at'], reverse=True)
    
    def get_backup_url(self, key: str, expires: int = 3600) -> str:
        """Get a presigned URL for downloading a backup."""
        return self.s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': key},
            ExpiresIn=expires
        )
    
    def trigger_backup(self, service: str) -> Dict:
        """Trigger an immediate backup for a service."""
        from kubernetes import client, config
        
        config.load_incluster_config()
        batch_v1 = client.BatchV1Api()
        
        # Get the CronJob
        cronjob_name = f'{service}-backup'
        cronjob = batch_v1.read_namespaced_cron_job(
            cronjob_name, 'novasight'
        )
        
        # Create a Job from the CronJob template
        job_name = f'{cronjob_name}-manual-{int(datetime.utcnow().timestamp())}'
        job = client.V1Job(
            metadata=client.V1ObjectMeta(name=job_name),
            spec=cronjob.spec.job_template.spec
        )
        
        batch_v1.create_namespaced_job('novasight', job)
        
        logger.info(f'Triggered manual backup: {job_name}')
        
        return {
            'job_name': job_name,
            'service': service,
            'status': 'triggered'
        }
    
    def restore_postgresql(
        self,
        backup_key: str,
        target_database: str
    ) -> Dict:
        """Restore PostgreSQL from backup."""
        logger.info(f'Starting PostgreSQL restore from {backup_key}')
        
        # Download backup
        local_file = f'/tmp/{backup_key.split("/")[-1]}'
        self.s3.download_file(self.bucket, backup_key, local_file)
        
        # Restore (this would typically run in a Job)
        # For safety, create new database with timestamp
        restore_db = f'{target_database}_restore_{int(datetime.utcnow().timestamp())}'
        
        return {
            'status': 'restore_initiated',
            'source': backup_key,
            'target_database': restore_db,
        }


class PointInTimeRecovery:
    """Point-in-time recovery for PostgreSQL."""
    
    def __init__(self, wal_bucket: str):
        self.wal_bucket = wal_bucket
        self.s3 = boto3.client('s3')
    
    def get_recovery_points(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """Get available recovery points in a time range."""
        # List WAL files in the range
        response = self.s3.list_objects_v2(
            Bucket=self.wal_bucket,
            Prefix='wal/'
        )
        
        points = []
        for obj in response.get('Contents', []):
            obj_time = obj['LastModified'].replace(tzinfo=None)
            if start_time <= obj_time <= end_time:
                points.append({
                    'timestamp': obj_time.isoformat(),
                    'wal_file': obj['Key'],
                })
        
        return points
    
    def recover_to_point(
        self,
        target_time: datetime,
        base_backup: str
    ) -> Dict:
        """Initiate point-in-time recovery."""
        logger.info(
            f'Initiating PITR to {target_time.isoformat()} '
            f'from base {base_backup}'
        )
        
        # This would trigger a Kubernetes Job with:
        # 1. Restore base backup
        # 2. Apply WAL files up to target_time
        # 3. Start PostgreSQL in recovery mode
        
        return {
            'status': 'recovery_initiated',
            'target_time': target_time.isoformat(),
            'base_backup': base_backup,
        }
```

### Recovery Runbook

```markdown
# backup/docs/RECOVERY_RUNBOOK.md

# NovaSight Recovery Runbook

## PostgreSQL Recovery

### Full Restore
```bash
# 1. List available backups
aws s3 ls s3://novasight-backups/postgresql/

# 2. Download backup
aws s3 cp s3://novasight-backups/postgresql/postgresql_20240115_020000.sql.gz /tmp/

# 3. Create new database
psql -h $PGHOST -U $PGUSER -c "CREATE DATABASE novasight_restore;"

# 4. Restore
gunzip -c /tmp/postgresql_20240115_020000.sql.gz | psql -h $PGHOST -U $PGUSER -d novasight_restore

# 5. Verify data
psql -h $PGHOST -U $PGUSER -d novasight_restore -c "SELECT COUNT(*) FROM tenants;"

# 6. Swap databases (during maintenance window)
psql -h $PGHOST -U $PGUSER -c "ALTER DATABASE novasight RENAME TO novasight_old;"
psql -h $PGHOST -U $PGUSER -c "ALTER DATABASE novasight_restore RENAME TO novasight;"
```

### Point-in-Time Recovery
```bash
# Use pg_basebackup + WAL replay
# See: docs/pitr-recovery.md
```

## ClickHouse Recovery

### Full Restore
```bash
# 1. List backups
clickhouse-backup list remote

# 2. Download backup
clickhouse-backup download backup_20240115_020000

# 3. Restore
clickhouse-backup restore backup_20240115_020000

# 4. Verify
clickhouse-client --query "SELECT count() FROM system.tables WHERE database NOT IN ('system', 'information_schema');"
```

## Tenant-Specific Recovery

For recovering a single tenant's data, use the tenant isolation scripts:
```bash
./scripts/restore-tenant.sh --tenant-id UUID --backup-date 2024-01-15
```
```

## Expected Output

```
backup/
├── postgresql/
│   ├── backup-cronjob.yaml
│   └── wal-archiver.yaml
├── clickhouse/
│   ├── backup-cronjob.yaml
│   └── config.yaml
├── redis/
│   └── backup-cronjob.yaml
├── scripts/
│   ├── restore-postgresql.sh
│   ├── restore-clickhouse.sh
│   └── restore-tenant.sh
└── docs/
    ├── RECOVERY_RUNBOOK.md
    └── PITR_RECOVERY.md
```

## Acceptance Criteria

- [ ] PostgreSQL backups every 6 hours
- [ ] ClickHouse backups daily
- [ ] Redis RDB snapshots configured
- [ ] Backups stored in S3
- [ ] Encryption at rest enabled
- [ ] Retention policy: 30 days
- [ ] Point-in-time recovery works
- [ ] Restore tested and documented
- [ ] Monitoring for backup failures

## Reference Documents

- [Infrastructure Agent](../agents/infrastructure-agent.agent.md)
- [Database Setup](./002-database-setup.md)
