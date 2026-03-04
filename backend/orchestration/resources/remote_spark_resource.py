"""
NovaSight Dagster Resources — Remote Spark
============================================

Remote Spark resource for executing spark-submit on a remote Spark cluster.
Supports SSH, Docker, local, and Spark REST Submission API modes.

Features:
- SSH-based remote execution
- Spark REST Submission API (standalone clusters, no CLI needed)
- Dynamic configuration from database
- Support for multiple cluster types
- Secure credential management
- Job monitoring and log retrieval
"""

from dagster import ConfigurableResource, InitResourceContext
from typing import Optional, Dict, Any, List
import logging
import subprocess
import tempfile
import os
import time
import json
from pathlib import Path
from dataclasses import dataclass

try:
    import requests as http_requests
except ImportError:
    http_requests = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class SparkJobResult:
    """Result of a Spark job execution."""
    success: bool
    return_code: int
    stdout: str
    stderr: str
    application_id: Optional[str] = None
    tracking_url: Optional[str] = None
    duration_ms: Optional[int] = None


class RemoteSparkResource(ConfigurableResource):
    """
    Dagster resource for executing spark-submit on a remote Spark cluster.
    
    Supports multiple execution modes:
    1. SSH + spark-submit: Connects via SSH and runs spark-submit on remote host
    2. Spark REST API: Uses Spark REST submission API (standalone mode)
    3. Livy: Uses Apache Livy REST API for job submission
    4. Docker: Uses docker exec to run spark-submit in a Docker container
    
    Configuration is loaded from database, allowing dynamic updates via admin UI.
    """
    
    # SSH Configuration (for SSH mode)
    ssh_host: str = ""
    ssh_port: int = 22
    ssh_user: str = "spark"
    ssh_key_path: Optional[str] = None
    ssh_password: Optional[str] = None  # Alternative to key
    
    # Spark Configuration
    spark_master: str = "spark://spark-master:7077"
    spark_home: str = "/opt/spark"
    deploy_mode: str = "client"  # client or cluster
    
    # Resource allocation
    driver_memory: str = "2g"
    executor_memory: str = "2g"
    executor_cores: int = 2
    num_executors: int = 2
    
    # Remote paths
    remote_jobs_dir: str = "/opt/spark/jobs"
    remote_jars_dir: str = "/opt/spark/jars"
    
    # Execution mode: ssh, docker, rest, livy, local
    execution_mode: str = "ssh"
    
    # Docker configuration (for docker mode)
    docker_container: str = "novasight-spark-master"
    
    # REST API configuration (for rest mode — Spark Standalone only)
    spark_rest_url: str = "http://spark-master:6066"
    
    # Livy configuration (for Livy mode)
    livy_url: Optional[str] = None
    
    def _get_dynamic_config(self) -> Optional[Dict[str, Any]]:
        """Fetch Spark configuration from database."""
        try:
            import sys
            if '/app' not in sys.path:
                sys.path.insert(0, '/app')
            
            from app.platform.infrastructure import InfrastructureConfigProvider
            
            provider = InfrastructureConfigProvider()
            config = provider.get_spark_config()
            
            if config:
                return {
                    "spark_master": config.master_url,
                    "driver_memory": config.driver_memory,
                    "executor_memory": config.executor_memory,
                    "executor_cores": config.executor_cores,
                    "additional_configs": config.additional_configs,
                    "ssh_host": getattr(config, 'ssh_host', self.ssh_host),
                    "ssh_user": getattr(config, 'ssh_user', self.ssh_user),
                    "ssh_key_path": getattr(config, 'ssh_key_path', self.ssh_key_path),
                    "deploy_mode": getattr(config, 'deploy_mode', self.deploy_mode),
                }
        except Exception as e:
            logger.warning(f"Failed to get dynamic Spark config: {e}")
        
        return None
    
    def _build_spark_submit_command(
        self,
        app_path: str,
        app_args: Optional[List[str]] = None,
        spark_config: Optional[Dict[str, str]] = None,
        py_files: Optional[List[str]] = None,
        jars: Optional[List[str]] = None,
        job_resource_config: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Build the spark-submit command with all options.
        
        Infrastructure config provides the cluster connection (master URL, deploy mode).
        Job-level resource config overrides resource allocation (memory, cores, executors).
        
        Args:
            app_path: Path to the Spark application
            app_args: Arguments to pass to the application
            spark_config: Additional Spark --conf key=value pairs
            py_files: Additional Python files to distribute
            jars: Additional JAR files to include
            job_resource_config: Per-job resource overrides
                (driver_memory, executor_memory, executor_cores, num_executors,
                 additional_configs)
        """
        dynamic_config = self._get_dynamic_config() or {}
        job_rc = job_resource_config or {}
        
        # Cluster connection — ONLY from infrastructure config
        master = dynamic_config.get("spark_master", self.spark_master)
        deploy_mode = dynamic_config.get("deploy_mode", self.deploy_mode)
        
        # Resource allocation — job-level overrides > infra defaults > class defaults
        driver_mem = job_rc.get("driver_memory") or dynamic_config.get("driver_memory", self.driver_memory)
        executor_mem = job_rc.get("executor_memory") or dynamic_config.get("executor_memory", self.executor_memory)
        executor_cores = job_rc.get("executor_cores") or dynamic_config.get("executor_cores", self.executor_cores)
        num_executors = job_rc.get("num_executors") or dynamic_config.get("num_executors", self.num_executors)
        
        # Additional configs — merge infra defaults with job-level overrides
        additional_configs = {**dynamic_config.get("additional_configs", {}), **job_rc.get("additional_configs", {})}
        
        cmd = [
            f"{self.spark_home}/bin/spark-submit",
            "--master", master,
            "--deploy-mode", deploy_mode,
            "--driver-memory", str(driver_mem),
            "--executor-memory", str(executor_mem),
            "--executor-cores", str(executor_cores),
            "--num-executors", str(num_executors),
        ]
        
        # Add additional stored configs
        for key, value in additional_configs.items():
            cmd.extend(["--conf", f"{key}={value}"])
        
        # Add runtime spark config
        if spark_config:
            for key, value in spark_config.items():
                cmd.extend(["--conf", f"{key}={value}"])
        
        # Add py-files (additional Python dependencies)
        if py_files:
            cmd.extend(["--py-files", ",".join(py_files)])
        
        # Add JARs
        if jars:
            cmd.extend(["--jars", ",".join(jars)])
        
        # Add application path
        cmd.append(app_path)
        
        # Add application arguments
        if app_args:
            cmd.extend(app_args)
        
        return cmd
    
    def _execute_via_ssh(
        self,
        command: List[str],
        timeout: int = 3600,
    ) -> SparkJobResult:
        """Execute spark-submit command via SSH."""
        import time
        start_time = time.time()
        
        dynamic_config = self._get_dynamic_config() or {}
        ssh_host = dynamic_config.get("ssh_host", self.ssh_host)
        ssh_user = dynamic_config.get("ssh_user", self.ssh_user)
        ssh_key = dynamic_config.get("ssh_key_path", self.ssh_key_path)
        
        if not ssh_host:
            raise ValueError("SSH host is not configured for remote Spark execution")
        
        # Build SSH command
        ssh_cmd = ["ssh"]
        
        # Add SSH options
        ssh_cmd.extend(["-o", "StrictHostKeyChecking=no"])
        ssh_cmd.extend(["-o", "BatchMode=yes"])
        ssh_cmd.extend(["-o", f"ConnectTimeout=30"])
        
        if ssh_key:
            ssh_cmd.extend(["-i", ssh_key])
        
        ssh_cmd.extend(["-p", str(self.ssh_port)])
        ssh_cmd.append(f"{ssh_user}@{ssh_host}")
        
        # Add the spark-submit command as a quoted string
        spark_cmd_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in command)
        ssh_cmd.append(spark_cmd_str)
        
        logger.info(f"Executing remote spark-submit: ssh {ssh_user}@{ssh_host} '{spark_cmd_str[:100]}...'")
        
        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Parse application ID from output if available
            app_id = self._parse_application_id(result.stdout + result.stderr)
            
            return SparkJobResult(
                success=result.returncode == 0,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                application_id=app_id,
                duration_ms=duration_ms,
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"Spark job timed out after {timeout} seconds")
            return SparkJobResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=f"Job timed out after {timeout} seconds",
            )
        except Exception as e:
            logger.error(f"Failed to execute remote spark-submit: {e}")
            return SparkJobResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(e),
            )
    
    def _execute_via_local(
        self,
        command: List[str],
        timeout: int = 3600,
    ) -> SparkJobResult:
        """Execute spark-submit locally (for local/dev mode)."""
        import time
        start_time = time.time()
        
        logger.info(f"Executing local spark-submit: {' '.join(command[:5])}...")
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            app_id = self._parse_application_id(result.stdout + result.stderr)
            
            return SparkJobResult(
                success=result.returncode == 0,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                application_id=app_id,
                duration_ms=duration_ms,
            )
        except subprocess.TimeoutExpired:
            return SparkJobResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=f"Job timed out after {timeout} seconds",
            )
        except Exception as e:
            return SparkJobResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(e),
            )
    
    def _parse_application_id(self, output: str) -> Optional[str]:
        """Parse Spark application ID from output."""
        import re
        
        # Pattern for standalone mode
        match = re.search(r"app-\d{14}-\d+", output)
        if match:
            return match.group(0)
        
        # Pattern for YARN mode
        match = re.search(r"application_\d+_\d+", output)
        if match:
            return match.group(0)
        
        return None
    
    def _execute_via_docker(
        self,
        command: List[str],
        timeout: int = 3600,
    ) -> SparkJobResult:
        """
        Execute spark-submit via docker exec in the Spark master container.
        
        This is the recommended mode for Docker-based development environments
        where Spark runs as containers on the same Docker network.
        """
        import time
        start_time = time.time()
        
        dynamic_config = self._get_dynamic_config() or {}
        container = dynamic_config.get("docker_container", self.docker_container)
        
        # Build docker exec command
        docker_cmd = [
            "docker", "exec", container,
        ]
        docker_cmd.extend(command)
        
        logger.info(f"Executing spark-submit via Docker: docker exec {container} spark-submit...")
        
        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            app_id = self._parse_application_id(result.stdout + result.stderr)
            
            return SparkJobResult(
                success=result.returncode == 0,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                application_id=app_id,
                duration_ms=duration_ms,
            )
        except subprocess.TimeoutExpired:
            logger.error(f"Docker Spark job timed out after {timeout} seconds")
            return SparkJobResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=f"Job timed out after {timeout} seconds",
            )
        except FileNotFoundError:
            logger.error("Docker command not found. Is Docker installed?")
            return SparkJobResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr="Docker command not found. Ensure Docker is installed and accessible.",
            )
        except Exception as e:
            logger.error(f"Failed to execute spark-submit via Docker: {e}")
            return SparkJobResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(e),
            )

    def _execute_via_rest(
        self,
        app_path: str,
        app_args: Optional[List[str]] = None,
        spark_config: Optional[Dict[str, str]] = None,
        py_files: Optional[List[str]] = None,
        timeout: int = 3600,
        job_resource_config: Optional[Dict[str, Any]] = None,
    ) -> SparkJobResult:
        """
        Submit a Spark application via the Spark REST Submission API.
        
        Cluster connection comes from infrastructure config.
        Resource allocation can be overridden per-job via job_resource_config.
        
        Requires:
        - Spark Standalone cluster with REST submission enabled (default)
        - Job file accessible to Spark master via shared volume
        - deploy-mode: cluster (enforced by REST API)
        """
        if http_requests is None:
            return SparkJobResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr="'requests' library is not installed. Run: pip install requests",
            )
        
        start_time = time.time()
        
        dynamic_config = self._get_dynamic_config() or {}
        job_rc = job_resource_config or {}
        
        # Cluster connection — ONLY from infrastructure config
        rest_url = dynamic_config.get("spark_rest_url", self.spark_rest_url).rstrip("/")
        master = dynamic_config.get("spark_master", self.spark_master)
        
        # Resource allocation — job-level overrides > infra defaults > class defaults
        driver_mem = job_rc.get("driver_memory") or dynamic_config.get("driver_memory", self.driver_memory)
        executor_mem = job_rc.get("executor_memory") or dynamic_config.get("executor_memory", self.executor_memory)
        executor_cores = job_rc.get("executor_cores") or dynamic_config.get("executor_cores", self.executor_cores)
        num_executors = job_rc.get("num_executors") or dynamic_config.get("num_executors", self.num_executors)
        
        # Additional configs — merge infra defaults with job-level overrides
        additional_configs = {**dynamic_config.get("additional_configs", {}), **job_rc.get("additional_configs", {})}
        
        # Build Spark properties
        # spark.app.name and spark.jars are required by the REST protocol validation
        # Default JDBC drivers for database connectivity
        # Use extraClassPath so the driver and executors load JARs from local paths
        # (each node must have these JARs available via shared volume mount)
        jdbc_jars_glob = "/opt/spark/jars/custom/*"
        default_jdbc_jars = ",".join([
            "/opt/spark/jars/custom/postgresql-42.7.4.jar",
            "/opt/spark/jars/custom/mysql-connector-j-8.2.0.jar",
            "/opt/spark/jars/custom/clickhouse-jdbc-0.6.3.jar",
            "/opt/spark/jars/custom/mssql-jdbc-12.4.2.jre11.jar",
            "/opt/spark/jars/custom/ojdbc8.jar",
        ])
        spark_properties = {
            "spark.app.name": f"NovaSight_{Path(app_path).stem}",
            "spark.master": master,
            "spark.submit.deployMode": "cluster",
            "spark.driver.memory": driver_mem,
            "spark.executor.memory": executor_mem,
            "spark.executor.cores": str(executor_cores),
            "spark.cores.max": str(executor_cores * num_executors),
            "spark.jars": "",
            "spark.driver.extraClassPath": jdbc_jars_glob,
            "spark.executor.extraClassPath": jdbc_jars_glob,
            "spark.submit.pyFiles": ",".join(py_files) if py_files else "",
        }
        
        # Merge additional configs
        for key, value in additional_configs.items():
            spark_properties[key] = str(value)
        
        # Merge runtime spark config
        if spark_config:
            for key, value in spark_config.items():
                spark_properties[key] = str(value)
        
        # Build REST submission payload for PySpark
        # The Spark REST API was designed for JVM submissions. For PySpark:
        # - mainClass must be org.apache.spark.deploy.PythonRunner  
        # - appResource should point to a dummy/empty jar (Spark requires it)
        # - appArgs must start with the Python file path, followed by any user args
        # PythonRunner.main() reads args[0] as the Python file to execute.
        python_file_uri = f"file://{app_path}"
        full_app_args = [python_file_uri] + (app_args or [])
        
        payload = {
            "action": "CreateSubmissionRequest",
            "appResource": python_file_uri,
            "clientSparkVersion": "3.5.4",
            "mainClass": "org.apache.spark.deploy.PythonRunner",
            "sparkProperties": spark_properties,
            "environmentVariables": {
                "PYSPARK_PYTHON": "python3",
            },
            "appArgs": full_app_args,
        }
        
        submit_url = f"{rest_url}/v1/submissions/create"
        logger.info(f"Submitting Spark job via REST API: {submit_url}")
        logger.debug(f"Payload: appResource={payload['appResource']}, args={payload['appArgs']}")
        
        try:
            # Submit the job
            resp = http_requests.post(submit_url, json=payload, timeout=30)
            resp.raise_for_status()
            submit_result = resp.json()
            
            if not submit_result.get("success"):
                msg = submit_result.get("message", "Unknown submission error")
                logger.error(f"Spark REST submission failed: {msg}")
                return SparkJobResult(
                    success=False,
                    return_code=1,
                    stdout=json.dumps(submit_result, indent=2),
                    stderr=msg,
                )
            
            submission_id = submit_result.get("submissionId", "")
            logger.info(f"Spark job submitted: {submission_id}")
            
            # Poll for completion
            status_url = f"{rest_url}/v1/submissions/status/{submission_id}"
            poll_interval = 5  # seconds
            terminal_states = {"FINISHED", "FAILED", "KILLED", "ERROR", "NOT_FOUND"}
            final_state = "UNKNOWN"
            
            while (time.time() - start_time) < timeout:
                time.sleep(poll_interval)
                
                try:
                    status_resp = http_requests.get(status_url, timeout=10)
                    status_resp.raise_for_status()
                    status_data = status_resp.json()
                    driver_state = status_data.get("driverState", "UNKNOWN")
                    
                    logger.debug(f"Spark job {submission_id} state: {driver_state}")
                    
                    if driver_state in terminal_states:
                        final_state = driver_state
                        break
                        
                except http_requests.RequestException as poll_err:
                    logger.warning(f"Failed to poll Spark job status: {poll_err}")
                    # Continue polling — transient network errors shouldn't abort
                    continue
            else:
                # Timeout reached
                logger.error(f"Spark job {submission_id} timed out after {timeout}s")
                # Attempt to kill the job
                try:
                    kill_url = f"{rest_url}/v1/submissions/kill/{submission_id}"
                    http_requests.post(kill_url, timeout=10)
                except Exception:
                    pass
                
                return SparkJobResult(
                    success=False,
                    return_code=-1,
                    stdout="",
                    stderr=f"Job {submission_id} timed out after {timeout} seconds",
                    application_id=submission_id,
                    duration_ms=int((time.time() - start_time) * 1000),
                )
            
            duration_ms = int((time.time() - start_time) * 1000)
            success = final_state == "FINISHED"
            
            # Build result message
            stdout_msg = json.dumps({
                "submissionId": submission_id,
                "driverState": final_state,
                "duration_ms": duration_ms,
            }, indent=2)
            
            stderr_msg = "" if success else f"Spark job {submission_id} ended with state: {final_state}"
            
            logger.info(f"Spark job {submission_id} completed: state={final_state}, duration={duration_ms}ms")
            
            return SparkJobResult(
                success=success,
                return_code=0 if success else 1,
                stdout=stdout_msg,
                stderr=stderr_msg,
                application_id=submission_id,
                duration_ms=duration_ms,
            )
            
        except http_requests.ConnectionError:
            logger.error(f"Cannot connect to Spark REST API at {rest_url}")
            return SparkJobResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=f"Cannot connect to Spark REST API at {rest_url}. "
                       f"Ensure spark-master is running and port 6066 is accessible.",
            )
        except http_requests.RequestException as e:
            logger.error(f"Spark REST API request failed: {e}")
            return SparkJobResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=f"Spark REST API error: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Unexpected error during REST submission: {e}")
            return SparkJobResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(e),
            )

    def copy_job_to_remote(
        self,
        local_path: str,
        remote_path: Optional[str] = None,
    ) -> str:
        """
        Copy a job file to the remote Spark server.
        
        For REST/docker mode: copies to the shared volume (/opt/spark/jobs)
        accessible to both backend and Spark workers.
        For SSH mode: copies via SCP to the remote Spark host.
        For local mode: returns the local path as-is.
        
        Args:
            local_path: Path to the local job file
            remote_path: Optional remote path. If not specified, uses remote_jobs_dir.
        
        Returns:
            Remote path where the file was copied
        """
        import shutil
        
        dynamic_config = self._get_dynamic_config() or {}
        ssh_host = dynamic_config.get("ssh_host", self.ssh_host)
        ssh_user = dynamic_config.get("ssh_user", self.ssh_user)
        ssh_key = dynamic_config.get("ssh_key_path", self.ssh_key_path)
        execution_mode = dynamic_config.get("execution_mode", self.execution_mode)
        
        local_file = Path(local_path)
        
        if execution_mode in ("rest", "docker"):
            # REST/docker mode: copy to shared volume accessible by Spark workers
            jobs_dir = Path(dynamic_config.get("remote_jobs_dir", self.remote_jobs_dir))
            jobs_dir.mkdir(parents=True, exist_ok=True)
            dest_path = jobs_dir / local_file.name
            
            if str(local_file) != str(dest_path):
                shutil.copy2(str(local_file), str(dest_path))
                logger.info(f"Copied job to shared volume: {local_path} -> {dest_path}")
            else:
                logger.info(f"Job already on shared volume: {dest_path}")
            
            return str(dest_path)
        
        if not ssh_host:
            # Local mode - just return the local path
            return local_path
        
        local_file = Path(local_path)
        if remote_path is None:
            remote_path = f"{self.remote_jobs_dir}/{local_file.name}"
        
        # Build SCP command
        scp_cmd = ["scp"]
        scp_cmd.extend(["-o", "StrictHostKeyChecking=no"])
        
        if ssh_key:
            scp_cmd.extend(["-i", ssh_key])
        
        scp_cmd.extend(["-P", str(self.ssh_port)])
        scp_cmd.append(local_path)
        scp_cmd.append(f"{ssh_user}@{ssh_host}:{remote_path}")
        
        logger.info(f"Copying job to remote: {local_path} -> {ssh_host}:{remote_path}")
        
        result = subprocess.run(scp_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to copy file to remote: {result.stderr}")
        
        return remote_path
    
    def submit_job(
        self,
        app_path: str,
        app_args: Optional[List[str]] = None,
        spark_config: Optional[Dict[str, str]] = None,
        py_files: Optional[List[str]] = None,
        jars: Optional[List[str]] = None,
        timeout: int = 3600,
        copy_to_remote: bool = True,
        job_resource_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Submit a Spark application to the remote cluster.
        
        Cluster connection (master URL, SSH) comes from infrastructure config.
        Resource allocation can be overridden per-job via job_resource_config.
        
        Args:
            app_path: Path to the Spark application (Python file)
            app_args: Arguments to pass to the application
            spark_config: Additional Spark --conf key=value pairs
            py_files: Additional Python files to distribute
            jars: Additional JAR files to include
            timeout: Job timeout in seconds
            copy_to_remote: Whether to copy the job file to remote before execution
            job_resource_config: Per-job resource overrides
                (driver_memory, executor_memory, executor_cores, num_executors,
                 additional_configs)
        
        Returns:
            Dict with success, stdout, stderr, application_id, etc.
        """
        dynamic_config = self._get_dynamic_config() or {}
        ssh_host = dynamic_config.get("ssh_host", self.ssh_host)
        execution_mode = dynamic_config.get("execution_mode", self.execution_mode)
        
        # Copy job to shared volume / remote if needed
        remote_app_path = app_path
        if copy_to_remote:
            if ssh_host and execution_mode == "ssh":
                try:
                    remote_app_path = self.copy_job_to_remote(app_path)
                except Exception as e:
                    logger.warning(f"Failed to copy job to remote, assuming it exists: {e}")
                    remote_app_path = f"{self.remote_jobs_dir}/{Path(app_path).name}"
            elif execution_mode in ("rest", "docker"):
                try:
                    remote_app_path = self.copy_job_to_remote(app_path)
                except Exception as e:
                    logger.warning(f"Failed to copy job to shared volume: {e}")
                    remote_app_path = app_path
        
        # Build command
        command = self._build_spark_submit_command(
            app_path=remote_app_path,
            app_args=app_args,
            spark_config=spark_config,
            py_files=py_files,
            jars=jars,
            job_resource_config=job_resource_config,
        )
        
        # Execute based on mode
        execution_mode = dynamic_config.get("execution_mode", self.execution_mode)
        
        if execution_mode == "rest" or execution_mode == "docker":
            # REST mode: submit via Spark REST Submission API (Standalone)
            # Also the default for "docker" mode — no Docker CLI needed
            result = self._execute_via_rest(
                app_path=remote_app_path,
                app_args=app_args,
                spark_config=spark_config,
                py_files=py_files,
                timeout=timeout,
                job_resource_config=job_resource_config,
            )
        elif ssh_host and execution_mode == "ssh":
            result = self._execute_via_ssh(command, timeout)
        else:
            result = self._execute_via_local(command, timeout)
        
        return {
            "success": result.success,
            "return_code": result.return_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "application_id": result.application_id,
            "tracking_url": result.tracking_url,
            "duration_ms": result.duration_ms,
        }
    
    def get_job_status(self, application_id: str) -> Dict[str, Any]:
        """
        Get the status of a running/completed Spark job.
        
        Uses Spark REST API when available (rest/docker mode),
        otherwise returns unknown for SSH/local modes.
        
        Args:
            application_id: Spark application ID
        
        Returns:
            Dict with status, progress, and other metrics
        """
        dynamic_config = self._get_dynamic_config() or {}
        execution_mode = dynamic_config.get("execution_mode", self.execution_mode)
        
        if execution_mode in ("rest", "docker") and http_requests:
            rest_url = dynamic_config.get("spark_rest_url", self.spark_rest_url).rstrip("/")
            try:
                resp = http_requests.get(
                    f"{rest_url}/v1/submissions/status/{application_id}",
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "application_id": application_id,
                    "status": data.get("driverState", "UNKNOWN"),
                    "worker_id": data.get("workerId", ""),
                    "worker_host": data.get("workerHostPort", ""),
                    "message": f"Driver state: {data.get('driverState', 'UNKNOWN')}",
                }
            except Exception as e:
                logger.warning(f"Failed to get job status via REST: {e}")
        
        return {
            "application_id": application_id,
            "status": "UNKNOWN",
            "message": "Status checking not available for current execution mode",
        }
    
    def kill_job(self, application_id: str) -> bool:
        """
        Kill a running Spark job.
        
        Uses Spark REST API when available (rest/docker mode),
        otherwise falls back to SSH/local spark-class kill.
        
        Args:
            application_id: Spark application ID
        
        Returns:
            True if job was killed successfully
        """
        dynamic_config = self._get_dynamic_config() or {}
        execution_mode = dynamic_config.get("execution_mode", self.execution_mode)
        
        # REST mode — kill via REST API
        if execution_mode in ("rest", "docker") and http_requests:
            rest_url = dynamic_config.get("spark_rest_url", self.spark_rest_url).rstrip("/")
            try:
                resp = http_requests.post(
                    f"{rest_url}/v1/submissions/kill/{application_id}",
                    timeout=15,
                )
                data = resp.json()
                success = data.get("success", False)
                logger.info(f"Kill job {application_id} via REST: success={success}")
                return success
            except Exception as e:
                logger.error(f"Failed to kill job via REST API: {e}")
                return False
        
        # SSH / local fallback
        ssh_host = dynamic_config.get("ssh_host", self.ssh_host)
        ssh_user = dynamic_config.get("ssh_user", self.ssh_user)
        ssh_key = dynamic_config.get("ssh_key_path", self.ssh_key_path)
        
        # Use dynamic master URL (from DB) with fallback to static default
        master = dynamic_config.get("spark_master", self.spark_master)
        spark_home = dynamic_config.get("spark_home", self.spark_home)
        
        if not ssh_host:
            # Local mode - use spark-class to kill
            cmd = [
                f"{spark_home}/bin/spark-class",
                "org.apache.spark.deploy.Client",
                "kill",
                master,
                application_id,
            ]
        else:
            # Build SSH command to kill remote job
            ssh_cmd = ["ssh"]
            if ssh_key:
                ssh_cmd.extend(["-i", ssh_key])
            ssh_cmd.extend(["-p", str(self.ssh_port)])
            ssh_cmd.append(f"{ssh_user}@{ssh_host}")
            
            kill_cmd = f"{spark_home}/bin/spark-class org.apache.spark.deploy.Client kill {master} {application_id}"
            ssh_cmd.append(kill_cmd)
            cmd = ssh_cmd
        
        logger.info(f"Killing Spark job: {application_id}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0


class DynamicRemoteSparkResource(RemoteSparkResource):
    """
    Remote Spark resource with fully dynamic configuration from database.
    
    All settings are loaded from the infrastructure configuration at runtime,
    allowing administrators to update Spark cluster settings via the UI
    with immediate effect on new jobs.
    
    Execution modes:
    - 'rest': Submit via Spark REST Submission API (recommended for Standalone)
    - 'docker': Alias for 'rest' mode — uses REST API instead of docker exec
    - 'ssh': Connect to remote Spark server via SSH and run spark-submit
    - 'local': Run spark-submit locally (requires Spark client installed)
    """
    
    # Override with sensible defaults that will be replaced by DB config
    ssh_host: str = ""
    spark_master: str = "spark://spark-master:7077"
    execution_mode: str = "docker"  # Default; both 'docker' and 'rest' use REST API
    docker_container: str = "novasight-spark-master"
    spark_rest_url: str = "http://spark-master:6066"
    
    def _get_dynamic_config(self) -> Optional[Dict[str, Any]]:
        """Fetch complete Spark configuration from database."""
        try:
            import sys
            import os
            if '/app' not in sys.path:
                sys.path.insert(0, '/app')
            
            from app.platform.infrastructure import InfrastructureConfigProvider
            
            provider = InfrastructureConfigProvider()
            config = provider.get_spark_config()
            
            if config:
                ssh_host = getattr(config, 'ssh_host', '') or ""
                
                # Determine execution mode based on configuration
                # If SSH host is configured, use SSH mode
                # If docker_container is set, use docker mode
                # Otherwise fall back to local
                execution_mode = getattr(config, 'execution_mode', None)
                if not execution_mode:
                    if ssh_host:
                        execution_mode = "ssh"
                    else:
                        # Check environment for Docker mode
                        execution_mode = os.environ.get(
                            "SPARK_EXECUTION_MODE", "docker"
                        )
                
                # Build comprehensive config from DB
                return {
                    "spark_master": config.master_url,
                    "driver_memory": config.driver_memory,
                    "executor_memory": config.executor_memory,
                    "executor_cores": config.executor_cores,
                    "num_executors": getattr(config, 'num_executors', 2),
                    "additional_configs": config.additional_configs or {},
                    "ssh_host": ssh_host,
                    "ssh_port": getattr(config, 'ssh_port', 22),
                    "ssh_user": getattr(config, 'ssh_user', 'spark'),
                    "ssh_key_path": getattr(config, 'ssh_key_path', None),
                    "deploy_mode": getattr(config, 'deploy_mode', 'client'),
                    "remote_jobs_dir": getattr(config, 'remote_jobs_dir', '/opt/spark/jobs'),
                    "spark_home": getattr(config, 'spark_home', '/opt/spark'),
                    "execution_mode": execution_mode,
                    "docker_container": os.environ.get(
                        "SPARK_MASTER_CONTAINER", "novasight-spark-master"
                    ),
                    "spark_rest_url": os.environ.get(
                        "SPARK_REST_URL", "http://spark-master:6066"
                    ),
                }
        except Exception as e:
            logger.warning(f"Failed to get dynamic Spark config: {e}")
        
        return None
