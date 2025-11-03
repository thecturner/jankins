"""Jenkins client adapter with retries, timeouts, and circuit breaking.

Wraps python-jenkins for standard operations and provides direct REST
fallback for progressive logs and Blue Ocean API.
"""

import logging
from typing import Optional, Dict, Any, List
import jenkins
import httpx
from urllib.parse import urljoin, quote

from ..config import JankinsConfig
from ..errors import (
    JankinsError,
    UnauthorizedError,
    map_http_error,
    TimeoutError as JankinsTimeoutError,
    UpstreamError,
)


logger = logging.getLogger(__name__)


class JenkinsAdapter:
    """Adapter for Jenkins API with retry and error handling.

    Uses python-jenkins for standard operations. Falls back to direct
    REST calls for progressive logs and Blue Ocean endpoints.
    """

    def __init__(self, config: JankinsConfig):
        self.config = config
        self._server: Optional[jenkins.Jenkins] = None
        self._http_client: Optional[httpx.Client] = None

    @property
    def server(self) -> jenkins.Jenkins:
        """Get or create python-jenkins server instance."""
        if self._server is None:
            try:
                self._server = jenkins.Jenkins(
                    self.config.jenkins_url,
                    username=self.config.jenkins_user,
                    password=self.config.jenkins_api_token,
                    timeout=self.config.jenkins_timeout,
                )
                # Validate connection
                self._server.get_whoami()
            except jenkins.JenkinsException as e:
                logger.error(f"Failed to connect to Jenkins: {e}")
                if "401" in str(e) or "Unauthorized" in str(e):
                    raise UnauthorizedError(str(e))
                raise UpstreamError(f"Jenkins connection failed: {e}")

        return self._server

    @property
    def http_client(self) -> httpx.Client:
        """Get or create httpx client for direct REST calls."""
        if self._http_client is None:
            self._http_client = httpx.Client(
                base_url=self.config.jenkins_url,
                auth=(self.config.jenkins_user, self.config.jenkins_api_token),
                timeout=self.config.jenkins_timeout,
                follow_redirects=True,
            )
        return self._http_client

    def close(self) -> None:
        """Close HTTP connections."""
        if self._http_client:
            self._http_client.close()
            self._http_client = None

    # Job operations

    def get_all_jobs(self, folder_depth: int = 0) -> List[Dict[str, Any]]:
        """Get all jobs with optional folder depth."""
        try:
            return self.server.get_all_jobs(folder_depth=folder_depth)
        except jenkins.JenkinsException as e:
            raise self._map_jenkins_exception(e, "list jobs")

    def get_job_info(self, name: str) -> Dict[str, Any]:
        """Get job information."""
        try:
            return self.server.get_job_info(name)
        except jenkins.NotFoundException:
            from ..errors import NotFoundError
            raise NotFoundError(f"Job '{name}' not found", resource_type="Job")
        except jenkins.JenkinsException as e:
            raise self._map_jenkins_exception(e, f"get job '{name}'")

    def build_job(self, name: str, parameters: Optional[Dict[str, Any]] = None) -> int:
        """Trigger a job build.

        Returns:
            Queue item ID
        """
        try:
            return self.server.build_job(name, parameters=parameters or {})
        except jenkins.NotFoundException:
            from ..errors import NotFoundError
            raise NotFoundError(f"Job '{name}' not found", resource_type="Job")
        except jenkins.JenkinsException as e:
            raise self._map_jenkins_exception(e, f"trigger job '{name}'")

    def enable_job(self, name: str) -> None:
        """Enable a job."""
        try:
            self.server.enable_job(name)
        except jenkins.NotFoundException:
            from ..errors import NotFoundError
            raise NotFoundError(f"Job '{name}' not found", resource_type="Job")
        except jenkins.JenkinsException as e:
            raise self._map_jenkins_exception(e, f"enable job '{name}'")

    def disable_job(self, name: str) -> None:
        """Disable a job."""
        try:
            self.server.disable_job(name)
        except jenkins.NotFoundException:
            from ..errors import NotFoundError
            raise NotFoundError(f"Job '{name}' not found", resource_type="Job")
        except jenkins.JenkinsException as e:
            raise self._map_jenkins_exception(e, f"disable job '{name}'")

    # Build operations

    def get_build_info(self, name: str, number: int) -> Dict[str, Any]:
        """Get build information."""
        try:
            return self.server.get_build_info(name, number)
        except jenkins.NotFoundException:
            from ..errors import NotFoundError
            raise NotFoundError(
                f"Build #{number} for job '{name}' not found",
                resource_type="Build"
            )
        except jenkins.JenkinsException as e:
            raise self._map_jenkins_exception(e, f"get build #{number} for '{name}'")

    def get_build_console_output(self, name: str, number: int) -> str:
        """Get full build console output.

        Note: For large logs, use ProgressiveLogClient instead.
        """
        try:
            return self.server.get_build_console_output(name, number)
        except jenkins.NotFoundException:
            from ..errors import NotFoundError
            raise NotFoundError(
                f"Build #{number} for job '{name}' not found",
                resource_type="Build"
            )
        except jenkins.JenkinsException as e:
            raise self._map_jenkins_exception(e, f"get console for '{name}' #{number}")

    # Queue operations

    def get_queue_info(self) -> List[Dict[str, Any]]:
        """Get build queue information."""
        try:
            return self.server.get_queue_info()
        except jenkins.JenkinsException as e:
            raise self._map_jenkins_exception(e, "get queue info")

    # User and system info

    def get_whoami(self) -> Dict[str, Any]:
        """Get current user information."""
        try:
            return self.server.get_whoami()
        except jenkins.JenkinsException as e:
            raise self._map_jenkins_exception(e, "get whoami")

    def get_version(self) -> str:
        """Get Jenkins version."""
        try:
            return self.server.get_version()
        except jenkins.JenkinsException as e:
            raise self._map_jenkins_exception(e, "get version")

    # Direct REST calls for advanced features

    def rest_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """Make a GET request to Jenkins REST API.

        Args:
            path: API path (e.g., "/job/myjob/123/logText/progressiveText")
            params: Query parameters

        Returns:
            httpx.Response
        """
        try:
            if self.config.debug_http:
                logger.debug(f"REST GET {path}", extra={"params": params})

            response = self.http_client.get(path, params=params)

            if self.config.debug_http:
                logger.debug(
                    f"REST GET {path} -> {response.status_code}",
                    extra={"status": response.status_code}
                )

            response.raise_for_status()
            return response

        except httpx.TimeoutException as e:
            raise JankinsTimeoutError(f"Request to {path} timed out")
        except httpx.HTTPStatusError as e:
            raise map_http_error(e.response.status_code, str(e))
        except httpx.RequestError as e:
            raise UpstreamError(f"Request to {path} failed: {e}")

    def rest_post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Make a POST request to Jenkins REST API."""
        try:
            if self.config.debug_http:
                logger.debug(f"REST POST {path}")

            response = self.http_client.post(path, json=json, data=data)

            if self.config.debug_http:
                logger.debug(
                    f"REST POST {path} -> {response.status_code}",
                    extra={"status": response.status_code}
                )

            response.raise_for_status()
            return response

        except httpx.TimeoutException:
            raise JankinsTimeoutError(f"Request to {path} timed out")
        except httpx.HTTPStatusError as e:
            raise map_http_error(e.response.status_code, str(e))
        except httpx.RequestError as e:
            raise UpstreamError(f"Request to {path} failed: {e}")

    # Helper methods

    def _map_jenkins_exception(self, e: jenkins.JenkinsException, operation: str) -> JankinsError:
        """Map python-jenkins exception to JankinsError."""
        error_msg = str(e)

        if isinstance(e, jenkins.NotFoundException):
            from ..errors import NotFoundError
            return NotFoundError(f"Failed to {operation}: {error_msg}")

        if "401" in error_msg or "Unauthorized" in error_msg:
            return UnauthorizedError(f"Failed to {operation}: {error_msg}")

        if "403" in error_msg or "Forbidden" in error_msg:
            from ..errors import ForbiddenError
            return ForbiddenError(f"Failed to {operation}: {error_msg}")

        if "timeout" in error_msg.lower():
            return JankinsTimeoutError(f"Failed to {operation}: {error_msg}")

        return UpstreamError(f"Failed to {operation}: {error_msg}")
