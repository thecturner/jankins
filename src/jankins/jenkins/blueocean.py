"""Blue Ocean API integration for pipeline graphs and advanced visualizations.

Blue Ocean provides richer pipeline data including:
- Node-level execution details
- Parallel stage visualization
- Step-level timing and logs
- Pipeline graph structure
"""

import logging
from typing import Dict, Any, List, Optional
from urllib.parse import quote

from ..errors import NotFoundError, UpstreamError

logger = logging.getLogger(__name__)


class BlueOceanClient:
    """Client for Jenkins Blue Ocean REST API.

    Blue Ocean API provides enhanced pipeline visualization data
    that's not available in the standard Jenkins API.
    """

    def __init__(self, jenkins_adapter):
        """Initialize Blue Ocean client.

        Args:
            jenkins_adapter: JenkinsAdapter instance for making REST calls
        """
        self.adapter = jenkins_adapter
        self.base_path = "/blue/rest/organizations/jenkins"

    def get_pipeline_run(
        self, job_name: str, build_number: int
    ) -> Dict[str, Any]:
        """Get Blue Ocean pipeline run data.

        Args:
            job_name: Full job name (folder/path/job)
            build_number: Build number

        Returns:
            Pipeline run data with nodes, stages, and timing
        """
        # Encode job name for URL
        encoded_name = self._encode_job_name(job_name)
        path = f"{self.base_path}/pipelines/{encoded_name}/runs/{build_number}"

        try:
            response = self.adapter.rest_get(path)
            return response.json()
        except Exception as e:
            logger.warning(f"Blue Ocean API not available for {job_name} #{build_number}: {e}")
            raise NotFoundError(
                f"Blue Ocean data not found for {job_name} #{build_number}",
                resource_type="Pipeline Run"
            )

    def get_pipeline_nodes(
        self, job_name: str, build_number: int
    ) -> List[Dict[str, Any]]:
        """Get pipeline execution nodes (stages and steps).

        Args:
            job_name: Full job name
            build_number: Build number

        Returns:
            List of pipeline nodes with execution details
        """
        encoded_name = self._encode_job_name(job_name)
        path = f"{self.base_path}/pipelines/{encoded_name}/runs/{build_number}/nodes"

        try:
            response = self.adapter.rest_get(path)
            return response.json()
        except Exception as e:
            logger.warning(f"Blue Ocean nodes not available: {e}")
            return []

    def get_node_steps(
        self, job_name: str, build_number: int, node_id: str
    ) -> List[Dict[str, Any]]:
        """Get steps within a pipeline node.

        Args:
            job_name: Full job name
            build_number: Build number
            node_id: Node ID from get_pipeline_nodes

        Returns:
            List of steps with timing and status
        """
        encoded_name = self._encode_job_name(job_name)
        path = f"{self.base_path}/pipelines/{encoded_name}/runs/{build_number}/nodes/{node_id}/steps"

        try:
            response = self.adapter.rest_get(path)
            return response.json()
        except Exception as e:
            logger.warning(f"Blue Ocean steps not available: {e}")
            return []

    def get_pipeline_graph(
        self, job_name: str, build_number: int
    ) -> Dict[str, Any]:
        """Get complete pipeline graph with stages and parallel execution.

        This provides the full execution graph including:
        - Sequential stages
        - Parallel branches
        - Stage dependencies
        - Execution timing per stage

        Args:
            job_name: Full job name
            build_number: Build number

        Returns:
            Pipeline graph structure
        """
        nodes = self.get_pipeline_nodes(job_name, build_number)

        if not nodes:
            return {
                "stages": [],
                "parallel_stages": [],
                "total_duration_ms": 0
            }

        # Build graph structure
        stages = []
        parallel_groups = {}
        total_duration = 0

        for node in nodes:
            stage_info = {
                "id": node.get("id", ""),
                "name": node.get("displayName", "Unknown"),
                "result": node.get("result", "UNKNOWN"),
                "state": node.get("state", "UNKNOWN"),
                "duration_ms": node.get("durationInMillis", 0),
                "start_time": node.get("startTime", ""),
                "type": node.get("type", "STAGE"),
            }

            # Track parallel stages
            edges = node.get("edges", [])
            if len(edges) > 1:
                # This is a parallel group
                parallel_id = node.get("id")
                if parallel_id not in parallel_groups:
                    parallel_groups[parallel_id] = []
                parallel_groups[parallel_id].append(stage_info)
            else:
                stages.append(stage_info)

            total_duration += stage_info["duration_ms"]

        return {
            "stages": stages,
            "parallel_stages": list(parallel_groups.values()),
            "total_duration_ms": total_duration,
            "node_count": len(nodes)
        }

    def get_failing_stages_detailed(
        self, job_name: str, build_number: int
    ) -> List[Dict[str, Any]]:
        """Get detailed information about failing stages.

        Args:
            job_name: Full job name
            build_number: Build number

        Returns:
            List of failing stages with error details
        """
        nodes = self.get_pipeline_nodes(job_name, build_number)
        failing = []

        for node in nodes:
            result = node.get("result", "")
            if result in ("FAILURE", "ABORTED", "UNSTABLE"):
                failing_stage = {
                    "name": node.get("displayName", "Unknown"),
                    "result": result,
                    "duration_ms": node.get("durationInMillis", 0),
                    "error": node.get("causeOfBlockage", ""),
                }

                # Get steps for this node to find error details
                steps = self.get_node_steps(job_name, build_number, node.get("id", ""))
                failing_steps = [
                    s for s in steps
                    if s.get("result") in ("FAILURE", "ABORTED")
                ]

                if failing_steps:
                    failing_stage["failing_steps"] = [
                        {
                            "name": s.get("displayName", "Unknown"),
                            "result": s.get("result", ""),
                        }
                        for s in failing_steps[:5]  # Top 5
                    ]

                failing.append(failing_stage)

        return failing

    def compare_pipeline_runs(
        self, job_name: str, base_build: int, head_build: int
    ) -> Dict[str, Any]:
        """Compare two pipeline runs for performance and result differences.

        Args:
            job_name: Full job name
            base_build: Base build number
            head_build: Head build number to compare

        Returns:
            Comparison data with stage-level differences
        """
        try:
            base_graph = self.get_pipeline_graph(job_name, base_build)
            head_graph = self.get_pipeline_graph(job_name, head_build)
        except NotFoundError:
            # Blue Ocean not available
            return {
                "stage_diffs": [],
                "duration_delta_ms": 0,
                "new_stages": [],
                "removed_stages": [],
                "available": False
            }

        # Build stage map by name
        base_stages = {s["name"]: s for s in base_graph["stages"]}
        head_stages = {s["name"]: s for s in head_graph["stages"]}

        stage_diffs = []
        for stage_name in head_stages.keys():
            if stage_name in base_stages:
                base_duration = base_stages[stage_name]["duration_ms"]
                head_duration = head_stages[stage_name]["duration_ms"]
                delta = head_duration - base_duration

                # Only include significant differences (>10% or >1sec)
                if abs(delta) > 1000 or (base_duration > 0 and abs(delta / base_duration) > 0.1):
                    stage_diffs.append({
                        "stage": stage_name,
                        "base_duration_ms": base_duration,
                        "head_duration_ms": head_duration,
                        "delta_ms": delta,
                        "base_result": base_stages[stage_name].get("result", ""),
                        "head_result": head_stages[stage_name].get("result", ""),
                    })

        # Find new and removed stages
        new_stages = [s for s in head_stages.keys() if s not in base_stages]
        removed_stages = [s for s in base_stages.keys() if s not in head_stages]

        duration_delta = head_graph["total_duration_ms"] - base_graph["total_duration_ms"]

        return {
            "stage_diffs": stage_diffs,
            "duration_delta_ms": duration_delta,
            "new_stages": new_stages,
            "removed_stages": removed_stages,
            "available": True
        }

    def _encode_job_name(self, job_name: str) -> str:
        """Encode job name for Blue Ocean API URL.

        Blue Ocean uses URL encoding for folder separators.
        Example: "folder/job" -> "folder%2Fjob"
        """
        # Replace / with %2F for folder paths
        return quote(job_name, safe="")
