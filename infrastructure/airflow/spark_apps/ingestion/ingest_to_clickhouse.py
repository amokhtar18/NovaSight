"""
PySpark application for ingesting data from various sources to ClickHouse.

This application reads data from JDBC sources (PostgreSQL, MySQL, Oracle, SQL Server)
and writes to ClickHouse, supporting both full and incremental ingestion modes.
"""
import sys
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, lit
from clickhouse_driver import Client as ClickHouseClient


class DataIngestionJob:
    """PySpark job for data ingestion."""
    
    def __init__(self, config_path: str):
        """
        Initialize ingestion job.
        
        Args:
            config_path: Path to JSON configuration file
        """
        self.config = self._load_config(config_path)
        self.spark = self._create_spark_session()
        self.ch_client = ClickHouseClient(
            host=self.config['clickhouse_config']['host'],
            port=self.config['clickhouse_config']['port'],
            database=self.config['clickhouse_config']['database']
        )
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def _create_spark_session(self) -> SparkSession:
        """Create Spark session with necessary configurations."""
        builder = SparkSession.builder \
            .appName(f"Ingestion-{self.config['datasource_id']}")
        
        # Add JDBC driver based on source type
        jdbc_jars = {
            'postgresql': '/opt/spark/jars/custom/postgresql-42.7.4.jar',
            'mysql': '/opt/spark/jars/custom/mysql-connector-j-8.2.0.jar',
            'oracle': '/opt/spark/jars/custom/ojdbc8.jar',
            'sqlserver': '/opt/spark/jars/custom/mssql-jdbc-12.4.2.jre11.jar',
        }
        
        db_type = self.config['datasource_type']
        if db_type in jdbc_jars:
            builder = builder.config('spark.jars', jdbc_jars[db_type])
        
        # Fix Oracle timezone issue (ORA-01882)
        if db_type == 'oracle':
            builder = builder.config('spark.driver.extraJavaOptions', '-Duser.timezone=UTC -Doracle.jdbc.timezoneAsRegion=false')
            builder = builder.config('spark.executor.extraJavaOptions', '-Duser.timezone=UTC -Doracle.jdbc.timezoneAsRegion=false')
        
        # Add ClickHouse JDBC driver
        builder = builder.config(
            'spark.jars',
            '/opt/spark/jars/custom/clickhouse-jdbc-0.6.3.jar'
        )
        
        return builder.getOrCreate()
    
    def _get_jdbc_url(self) -> str:
        """Build JDBC URL for source database."""
        conn = self.config['connection_config']
        db_type = self.config['datasource_type']
        
        urls = {
            'postgresql': f"jdbc:postgresql://{conn['host']}:{conn['port']}/{conn['database']}",
            'mysql': f"jdbc:mysql://{conn['host']}:{conn['port']}/{conn['database']}",
            'oracle': f"jdbc:oracle:thin:@{conn['host']}:{conn['port']}:{conn['database']}",
            'sqlserver': f"jdbc:sqlserver://{conn['host']}:{conn['port']};databaseName={conn['database']}",
        }
        
        return urls.get(db_type, urls['postgresql'])
    
    def _get_last_ingested_value(self, table_name: str, column: str):
        """Get last ingested value from ClickHouse."""
        query = f"""
            SELECT max({column}) as max_value
            FROM {table_name}
            WHERE _tenant_id = '{self.config['tenant_id']}'
        """
        try:
            result = self.ch_client.execute(query)
            return result[0][0] if result and result[0][0] else None
        except Exception as e:
            print(f"Failed to get last ingested value: {e}")
            return None
    
    def ingest_table(self, table_config: dict) -> dict:
        """
        Ingest a single table.
        
        Args:
            table_config: Table configuration dictionary
        
        Returns:
            Ingestion result dictionary
        """
        source_table = table_config['source_table']
        target_table = table_config['target_table']
        mode = table_config['mode']
        incremental_column = table_config.get('incremental_column')
        
        print(f"Ingesting {source_table} -> {target_table} (mode: {mode})")
        
        # Build source query
        if mode == 'incremental' and incremental_column:
            last_value = self._get_last_ingested_value(target_table, incremental_column)
            
            if last_value:
                query = f"""
                    (SELECT * FROM {source_table} 
                     WHERE {incremental_column} > '{last_value}'
                     ORDER BY {incremental_column}) as incremental_data
                """
            else:
                query = f"(SELECT * FROM {source_table}) as full_data"
        else:
            query = f"(SELECT * FROM {source_table}) as full_data"
        
        # Read from source using JDBC
        conn = self.config['connection_config']
        df = self.spark.read \
            .format('jdbc') \
            .option('url', self._get_jdbc_url()) \
            .option('dbtable', query) \
            .option('user', conn['username']) \
            .option('password', conn.get('password', '')) \
            .option('driver', conn['jdbc_driver']) \
            .option('fetchsize', '10000') \
            .load()
        
        # Add metadata columns
        df = df \
            .withColumn('_tenant_id', lit(self.config['tenant_id'])) \
            .withColumn('_datasource_id', lit(self.config['datasource_id'])) \
            .withColumn('_ingested_at', current_timestamp())
        
        row_count = df.count()
        print(f"Read {row_count} rows from {source_table}")
        
        if row_count == 0:
            print(f"No new data to ingest for {source_table}")
            return {'table': source_table, 'rows': 0, 'status': 'success'}
        
        # Write to ClickHouse
        ch_config = self.config['clickhouse_config']
        clickhouse_url = f"jdbc:clickhouse://{ch_config['host']}:{ch_config['port']}/{ch_config['database']}"
        
        # For incremental mode, we append; for full mode, we can overwrite
        save_mode = 'append' if mode == 'incremental' else 'overwrite'
        
        df.write \
            .format('jdbc') \
            .option('url', clickhouse_url) \
            .option('dbtable', target_table) \
            .option('driver', 'com.clickhouse.jdbc.ClickHouseDriver') \
            .option('batchsize', '10000') \
            .option('isolationLevel', 'NONE') \
            .mode(save_mode) \
            .save()
        
        print(f"Wrote {row_count} rows to ClickHouse table {target_table}")
        
        return {
            'table': source_table,
            'rows': row_count,
            'status': 'success',
            'mode': mode
        }
    
    def run(self) -> dict:
        """
        Execute ingestion for all configured tables.
        
        Returns:
            Summary dictionary with results
        """
        results = []
        
        for table_config in self.config['tables']:
            try:
                result = self.ingest_table(table_config)
                results.append(result)
            except Exception as e:
                print(f"Error ingesting {table_config['source_table']}: {str(e)}")
                import traceback
                traceback.print_exc()
                results.append({
                    'table': table_config['source_table'],
                    'rows': 0,
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Summary
        total_rows = sum(r['rows'] for r in results)
        failed = sum(1 for r in results if r['status'] == 'failed')
        
        summary = {
            'total_tables': len(results),
            'successful': len(results) - failed,
            'failed': failed,
            'total_rows': total_rows,
            'results': results
        }
        
        print(f"\n=== Ingestion Summary ===")
        print(f"Total tables: {summary['total_tables']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Total rows ingested: {summary['total_rows']}")
        
        return summary


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: ingest_to_clickhouse.py <config_path>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    job = DataIngestionJob(config_path)
    result = job.run()
    
    # Exit with error code if any table failed
    sys.exit(0 if result['failed'] == 0 else 1)
