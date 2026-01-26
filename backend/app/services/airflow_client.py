"""
NovaSight Airflow Client
========================

Client for Apache Airflow REST API.
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from flask import current_app
import logging

logger = logging.getLogger(__name__)


@dataclass
class DagRun:
    """Represents an Airflow DAG run."""
    dag_id: str
    run_id: str
    state: str
    execution_date: datetime
    start_date: Optional[datetime]
    end_date: Optional[datetime]


@dataclass
class TaskInstance:
    """Represents an Airflow task instance."""
    task_id: str
    state: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    try_number: int


class AirflowClient:
    """Client for Airflow REST API."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize Airflow client.
        
        Args:
            base_url: Airflow webserver URL
            username: Airflow username
            password: Airflow password
        """
        self._base_url = base_url
        self._username = username
        self._password = password
        self._client = None
    
    @property
    def base_url(self) -> str:
        """Get Airflow base URL from config."""
        if self._base_url:
            return self._base_url.rstrip('/')
        return current_app.config.get("AIRFLOW_BASE_URL", "http://localhost:8080").rstrip('/')
    
    @property
    def auth(self) -> tuple:
        """Get authentication credentials."""
        username = self._username or current_app.config.get("AIRFLOW_USERNAME", "airflow")
        password = self._password or current_app.config.get("AIRFLOW_PASSWORD", "airflow")
        return (username, password)
    
    @property
    def client(self) -> httpx.Client:
        """Get HTTP client instance."""
        if self._client is None:
            self._client = httpx.Client(timeout=30.0)
        return self._client
    
    def _request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Airflow API.
        
        Args:
            method: HTTP method
            path: API path
            **kwargs: Additional request arguments
        
        Returns:
            JSON response
        """
        url = f"{self.base_url}/api/v1{path}"
        
        try:
            response = self.client.request(
                method,
                url,
                auth=self.auth,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Airflow API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Airflow API request failed: {e}")
            raise
    
    # DAG Management
    
    def list_dags(self, tags: Optional[List[str]] = None) -> List[Dict]:
        """
        List DAGs in Airflow.
        
        Args:
            tags: Filter by tags
        
        Returns:
            List of DAG details
        """
        params = {}
        if tags:
            params["tags"] = ",".join(tags)
        
        result = self._request("GET", "/dags", params=params)
        return result.get("dags", [])
    
    def get_dag(self, dag_id: str) -> Dict:
        """
        Get DAG details.
        
        Args:
            dag_id: DAG identifier
        
        Returns:
            DAG details
        """
        return self._request("GET", f"/dags/{dag_id}")
    
    def pause_dag(self, dag_id: str) -> Dict:
        """
        Pause a DAG.
        
        Args:
            dag_id: DAG identifier
        
        Returns:
            Updated DAG details
        """
        return self._request("PATCH", f"/dags/{dag_id}", json={"is_paused": True})
    
    def unpause_dag(self, dag_id: str) -> Dict:
        """
        Unpause a DAG.
        
        Args:
            dag_id: DAG identifier
        
        Returns:
            Updated DAG details
        """
        return self._request("PATCH", f"/dags/{dag_id}", json={"is_paused": False})
    
    def refresh_dag(self, dag_id: str) -> None:
        """
        Trigger DAG file refresh.
        
        Args:
            dag_id: DAG identifier
        """
        self._request("PATCH", f"/dags/{dag_id}", json={})
    
    # DAG Runs
    
    def trigger_dag(
        self,
        dag_id: str,
        conf: Optional[Dict] = None
    ) -> DagRun:
        """
        Trigger a DAG run.
        
        Args:
            dag_id: DAG identifier
            conf: Optional run configuration
        
        Returns:
            DagRun object
        """
        payload = {"conf": conf or {}}
        result = self._request("POST", f"/dags/{dag_id}/dagRuns", json=payload)
        
        return DagRun(
            dag_id=result["dag_id"],
            run_id=result["dag_run_id"],
            state=result["state"],
            execution_date=datetime.fromisoformat(result["execution_date"].replace("Z", "+00:00")),
            start_date=None,
            end_date=None
        )
    
    def get_dag_runs(
        self,
        dag_id: str,
        limit: int = 25,
        offset: int = 0
    ) -> List[DagRun]:
        """
        Get DAG run history.
        
        Args:
            dag_id: DAG identifier
            limit: Maximum runs to return
            offset: Pagination offset
        
        Returns:
            List of DagRun objects
        """
        result = self._request(
            "GET",
            f"/dags/{dag_id}/dagRuns",
            params={
                "limit": limit,
                "offset": offset,
                "order_by": "-execution_date"
            }
        )
        
        return [
            DagRun(
                dag_id=r["dag_id"],
                run_id=r["dag_run_id"],
                state=r["state"],
                execution_date=datetime.fromisoformat(r["execution_date"].replace("Z", "+00:00")),
                start_date=datetime.fromisoformat(r["start_date"].replace("Z", "+00:00")) if r.get("start_date") else None,
                end_date=datetime.fromisoformat(r["end_date"].replace("Z", "+00:00")) if r.get("end_date") else None
            )
            for r in result.get("dag_runs", [])
        ]
    
    def get_dag_run(self, dag_id: str, run_id: str) -> DagRun:
        """
        Get specific DAG run.
        
        Args:
            dag_id: DAG identifier
            run_id: Run identifier
        
        Returns:
            DagRun object
        """
        result = self._request("GET", f"/dags/{dag_id}/dagRuns/{run_id}")
        
        return DagRun(
            dag_id=result["dag_id"],
            run_id=result["dag_run_id"],
            state=result["state"],
            execution_date=datetime.fromisoformat(result["execution_date"].replace("Z", "+00:00")),
            start_date=datetime.fromisoformat(result["start_date"].replace("Z", "+00:00")) if result.get("start_date") else None,
            end_date=datetime.fromisoformat(result["end_date"].replace("Z", "+00:00")) if result.get("end_date") else None
        )
    
    # Task Instances
    
    def get_task_instances(
        self,
        dag_id: str,
        run_id: str
    ) -> List[TaskInstance]:
        """
        Get task instances for a DAG run.
        
        Args:
            dag_id: DAG identifier
            run_id: Run identifier
        
        Returns:
            List of TaskInstance objects
        """
        result = self._request(
            "GET",
            f"/dags/{dag_id}/dagRuns/{run_id}/taskInstances"
        )
        
        return [
            TaskInstance(
                task_id=t["task_id"],
                state=t["state"] or "pending",
                start_date=datetime.fromisoformat(t["start_date"].replace("Z", "+00:00")) if t.get("start_date") else None,
                end_date=datetime.fromisoformat(t["end_date"].replace("Z", "+00:00")) if t.get("end_date") else None,
                try_number=t.get("try_number", 1)
            )
            for t in result.get("task_instances", [])
        ]
    
    # Logs
    
    def get_task_logs(
        self,
        dag_id: str,
        run_id: str,
        task_id: str,
        try_number: int = 1
    ) -> str:
        """
        Get task logs.
        
        Args:
            dag_id: DAG identifier
            run_id: Run identifier
            task_id: Task identifier
            try_number: Attempt number
        
        Returns:
            Log content string
        """
        result = self._request(
            "GET",
            f"/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{try_number}"
        )
        return result.get("content", "")
