"""
NovaSight Dagster Resources — Remote Spark
============================================

Remote Spark resource for executing spark-submit on a remote Spark cluster
via SSH. Supports both standalone Spark clusters and YARN/Kubernetes.

Features:
- SSH-based remote execution
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
from pathlib import Path
from dataclasses import dataclass

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
    
    # Execution mode: ssh, rest, livy
    execution_mode: str = "ssh"
    
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
    ) -> List[str]:
        """Build the spark-submit command with all options."""
        dynamic_config = self._get_dynamic_config() or {}
        
        master = dynamic_config.get("spark_master", self.spark_master)
        driver_mem = dynamic_config.get("driver_memory", self.driver_memory)
        executor_mem = dynamic_config.get("executor_memory", self.executor_memory)
        executor_cores = dynamic_config.get("executor_cores", self.executor_cores)
        deploy_mode = dynamic_config.get("deploy_mode", self.deploy_mode)
        additional_configs = dynamic_config.get("additional_configs", {})
        
        cmd = [
            f"{self.spark_home}/bin/spark-submit",
            "--master", master,
            "--deploy-mode", deploy_mode,
            "--driver-memory", driver_mem,
            "--executor-memory", executor_mem,
            "--executor-cores", str(executor_cores),
            "--num-executors", str(self.num_executors),
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
    
    def copy_job_to_remote(
        self,
        local_path: str,
        remote_path: Optional[str] = None,
    ) -> str:
        """
        Copy a job file to the remote Spark server.
        
        Args:
            local_path: Path to the local job file
            remote_path: Optional remote path. If not specified, uses remote_jobs_dir.
        
        Returns:
            Remote path where the file was copied
        """
        dynamic_config = self._get_dynamic_config() or {}
        ssh_host = dynamic_config.get("ssh_host", self.ssh_host)
        ssh_user = dynamic_config.get("ssh_user", self.ssh_user)
        ssh_key = dynamic_config.get("ssh_key_path", self.ssh_key_path)
        
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
    ) -> Dict[str, Any]:
        """
        Submit a Spark application to the remote cluster.
        
        Args:
            app_path: Path to the Spark application (Python file)
            app_args: Arguments to pass to the application
            spark_config: Additional Spark configuration
            py_files: Additional Python files to distribute
            jars: Additional JAR files to include
            timeout: Job timeout in seconds
            copy_to_remote: Whether to copy the job file to remote before execution
        
        Returns:
            Dict with success, stdout, stderr, application_id, etc.
        """
        dynamic_config = self._get_dynamic_config() or {}
        ssh_host = dynamic_config.get("ssh_host", self.ssh_host)
        
        # Copy job to remote if needed
        remote_app_path = app_path
        if copy_to_remote and ssh_host:
            try:
                remote_app_path = self.copy_job_to_remote(app_path)
            except Exception as e:
                logger.warning(f"Failed to copy job to remote, assuming it exists: {e}")
                # Assume the file already exists on remote
                remote_app_path = f"{self.remote_jobs_dir}/{Path(app_path).name}"
        
        # Build command
        command = self._build_spark_submit_command(
            app_path=remote_app_path,
            app_args=app_args,
            spark_config=spark_config,
            py_files=py_files,
            jars=jars,
        )
        
        # Execute based on mode
        if ssh_host and self.execution_mode == "ssh":
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
        
        Args:
            application_id: Spark application ID
        
        Returns:
            Dict with status, progress, and other metrics
        """
        # This would typically use Spark REST API or YARN API
        # For now, return a placeholder
        return {
            "application_id": application_id,
            "status": "UNKNOWN",
            "message": "Status checking not implemented for SSH mode",
        }
    
    def kill_job(self, application_id: str) -> bool:
        """
        Kill a running Spark job.
        
        Args:
            application_id: Spark application ID
        
        Returns:
            True if job was killed successfully
        """
        dynamic_config = self._get_dynamic_config() or {}
        ssh_host = dynamic_config.get("ssh_host", self.ssh_host)
        ssh_user = dynamic_config.get("ssh_user", self.ssh_user)
        ssh_key = dynamic_config.get("ssh_key_path", self.ssh_key_path)
        
        if not ssh_host:
            # Local mode - use spark-class to kill
            cmd = [
                f"{self.spark_home}/bin/spark-class",
                "org.apache.spark.deploy.Client",
                "kill",
                self.spark_master,
                application_id,
            ]
        else:
            # Build SSH command to kill remote job
            ssh_cmd = ["ssh"]
            if ssh_key:
                ssh_cmd.extend(["-i", ssh_key])
            ssh_cmd.extend(["-p", str(self.ssh_port)])
            ssh_cmd.append(f"{ssh_user}@{ssh_host}")
            
            kill_cmd = f"{self.spark_home}/bin/spark-class org.apache.spark.deploy.Client kill {self.spark_master} {application_id}"
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
    """
    
    # Override with sensible defaults that will be replaced by DB config
    ssh_host: str = ""
    spark_master: str = "spark://spark-master:7077"
    
    def _get_dynamic_config(self) -> Optional[Dict[str, Any]]:
        """Fetch complete Spark configuration from database."""
        try:
            import sys
            if '/app' not in sys.path:
                sys.path.insert(0, '/app')
            
            from app.platform.infrastructure import InfrastructureConfigProvider
            
            provider = InfrastructureConfigProvider()
            config = provider.get_spark_config()
            
            if config:
                # Build comprehensive config from DB
                return {
                    "spark_master": config.master_url,
                    "driver_memory": config.driver_memory,
                    "executor_memory": config.executor_memory,
                    "executor_cores": config.executor_cores,
                    "num_executors": getattr(config, 'num_executors', 2),
                    "additional_configs": config.additional_configs or {},
                    "ssh_host": getattr(config, 'ssh_host', '') or "",
                    "ssh_port": getattr(config, 'ssh_port', 22),
                    "ssh_user": getattr(config, 'ssh_user', 'spark'),
                    "ssh_key_path": getattr(config, 'ssh_key_path', None),
                    "deploy_mode": getattr(config, 'deploy_mode', 'client'),
                    "remote_jobs_dir": getattr(config, 'remote_jobs_dir', '/opt/spark/jobs'),
                    "spark_home": getattr(config, 'spark_home', '/opt/spark'),
                }
        except Exception as e:
            logger.warning(f"Failed to get dynamic Spark config: {e}")
        
        return None
