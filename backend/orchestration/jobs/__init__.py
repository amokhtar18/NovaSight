"""
NovaSight Dagster Jobs
======================

Unified job definitions for PySpark execution on remote Spark clusters.
"""

from orchestration.jobs.dagster_job_builder import (
    DagsterJobBuilder,
    SparkJobConfig,
    load_all_dagster_jobs,
    load_all_schedules,
    generate_pyspark_code,
    write_job_to_file,
    copy_to_remote_spark,
    execute_remote_spark_submit,
    update_stats,
    aggregate_pipeline_results,
)

__all__ = [
    "DagsterJobBuilder",
    "SparkJobConfig",
    "load_all_dagster_jobs",
    "load_all_schedules",
    "generate_pyspark_code",
    "write_job_to_file",
    "copy_to_remote_spark",
    "execute_remote_spark_submit",
    "update_stats",
    "aggregate_pipeline_results",
]
