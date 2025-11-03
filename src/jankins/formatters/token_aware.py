"""Token-aware formatting utilities.

Provides tools to minimize token usage in MCP responses while
maintaining clarity and usefulness.
"""

import json
from typing import Any, Dict, List, Optional
import tiktoken

from .base import OutputFormat, compact_dict, format_duration, format_timestamp


# Token estimator (using cl100k_base which is close to Claude's tokenizer)
try:
    TOKENIZER = tiktoken.get_encoding("cl100k_base")
except Exception:
    TOKENIZER = None


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Uses tiktoken if available, otherwise falls back to word count heuristic.
    """
    if TOKENIZER:
        return len(TOKENIZER.encode(text))
    else:
        # Rough heuristic: ~0.75 tokens per word
        return int(len(text.split()) * 0.75)


class TokenAwareFormatter:
    """Formatter that produces token-efficient outputs."""

    @staticmethod
    def format_job_list(
        jobs: List[Dict[str, Any]],
        format: OutputFormat = OutputFormat.SUMMARY,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Format job list with token awareness.

        Args:
            jobs: List of job dictionaries
            format: Output format
            limit: Maximum jobs to include

        Returns:
            Formatted response
        """
        if format == OutputFormat.IDS:
            return {
                "jobs": [{"name": j["fullname"], "url": j["url"]} for j in jobs[:limit]],
                "total": len(jobs),
                "shown": min(limit, len(jobs))
            }

        if format == OutputFormat.SUMMARY:
            summary_jobs = []
            for job in jobs[:limit]:
                summary_jobs.append({
                    "name": job["fullname"],
                    "color": job.get("color", "unknown"),  # Status indicator
                    "url": job["url"]
                })
            return {
                "jobs": summary_jobs,
                "total": len(jobs),
                "shown": min(limit, len(jobs))
            }

        # FULL format
        return {
            "jobs": jobs[:limit],
            "total": len(jobs),
            "shown": min(limit, len(jobs))
        }

    @staticmethod
    def format_build(
        build: Dict[str, Any],
        format: OutputFormat = OutputFormat.SUMMARY,
    ) -> Dict[str, Any]:
        """Format build information.

        Args:
            build: Build dictionary from Jenkins
            format: Output format

        Returns:
            Formatted build data
        """
        if format == OutputFormat.IDS:
            return {
                "number": build["number"],
                "url": build["url"],
                "result": build.get("result"),
            }

        if format == OutputFormat.SUMMARY:
            return {
                "number": build["number"],
                "result": build.get("result"),
                "duration": format_duration(build.get("duration", 0)),
                "timestamp": format_timestamp(build.get("timestamp", 0)),
                "building": build.get("building", False),
                "url": build["url"],
                "changes_count": len(build.get("changeSet", {}).get("items", [])),
                "artifacts_count": len(build.get("artifacts", [])),
            }

        # FULL format
        return build

    @staticmethod
    def format_log_response(
        summary: Any,  # LogSummary
        chunks: Optional[List[Dict[str, Any]]] = None,
        format: OutputFormat = OutputFormat.SUMMARY,
    ) -> Dict[str, Any]:
        """Format log retrieval response.

        Args:
            summary: LogSummary object
            chunks: Optional list of log chunks
            format: Output format

        Returns:
            Formatted log response
        """
        if format == OutputFormat.SUMMARY:
            result = {
                "summary": {
                    "total_bytes": summary.total_bytes,
                    "total_lines": summary.total_lines,
                    "error_count": summary.error_count,
                    "warning_count": summary.warning_count,
                    "is_complete": summary.is_complete,
                },
                "last_error_lines": summary.last_error_lines[:3],  # Top 3 only
                "failing_stages": summary.failing_stages,
            }

            if chunks:
                result["available_chunks"] = len(chunks)

            return result

        # FULL format includes chunks
        result = {
            "summary": {
                "total_bytes": summary.total_bytes,
                "total_lines": summary.total_lines,
                "error_count": summary.error_count,
                "warning_count": summary.warning_count,
                "is_complete": summary.is_complete,
            },
            "last_error_lines": summary.last_error_lines,
            "failing_stages": summary.failing_stages,
        }

        if chunks:
            result["chunks"] = chunks

        return result

    @staticmethod
    def format_triage(
        hypotheses: List[str],
        top_errors: List[str],
        failing_stages: List[str],
        suspect_changes: List[Dict[str, Any]],
        next_steps: List[str],
        format: OutputFormat = OutputFormat.SUMMARY,
    ) -> Dict[str, Any]:
        """Format failure triage response.

        Args:
            hypotheses: List of failure hypotheses
            top_errors: Top error messages
            failing_stages: Failed pipeline stages
            suspect_changes: Recent changes that may have caused failure
            next_steps: Recommended next actions
            format: Output format

        Returns:
            Formatted triage response
        """
        if format == OutputFormat.SUMMARY:
            return {
                "hypotheses": hypotheses[:3],  # Top 3
                "top_errors": top_errors[:5],   # Top 5
                "failing_stages": failing_stages,
                "next_steps": next_steps[:5],   # Top 5
            }

        # FULL format
        return {
            "hypotheses": hypotheses,
            "top_errors": top_errors,
            "failing_stages": failing_stages,
            "suspect_changes": suspect_changes,
            "next_steps": next_steps,
        }

    @staticmethod
    def format_comparison(
        base_build: Dict[str, Any],
        head_build: Dict[str, Any],
        duration_delta: int,
        stage_diffs: List[Dict[str, Any]],
        test_diffs: Optional[Dict[str, Any]] = None,
        format: OutputFormat = OutputFormat.DIFF,
    ) -> Dict[str, Any]:
        """Format build comparison.

        Args:
            base_build: Base build info
            head_build: Head build info
            duration_delta: Duration difference in ms
            stage_diffs: Stage-by-stage differences
            test_diffs: Test result differences
            format: Output format

        Returns:
            Formatted comparison
        """
        if format == OutputFormat.SUMMARY or format == OutputFormat.DIFF:
            result = {
                "builds": {
                    "base": base_build["number"],
                    "head": head_build["number"],
                },
                "duration_delta": format_duration(abs(duration_delta)),
                "duration_change": "faster" if duration_delta < 0 else "slower",
                "result_changed": base_build.get("result") != head_build.get("result"),
            }

            if stage_diffs:
                result["stage_changes"] = len([s for s in stage_diffs if s.get("changed")])

            if test_diffs:
                result["test_diffs"] = {
                    "new_failures": test_diffs.get("new_failures", 0),
                    "new_passes": test_diffs.get("new_passes", 0),
                }

            return result

        # FULL format
        return {
            "base_build": base_build,
            "head_build": head_build,
            "duration_delta": duration_delta,
            "stage_diffs": stage_diffs,
            "test_diffs": test_diffs,
        }

    @staticmethod
    def add_metadata(
        data: Dict[str, Any],
        correlation_id: str,
        took_ms: int,
        format_used: OutputFormat,
    ) -> Dict[str, Any]:
        """Add standard metadata to response.

        Args:
            data: Response data
            correlation_id: Request correlation ID
            took_ms: Request duration in milliseconds
            format_used: Format that was used

        Returns:
            Data with metadata added
        """
        # Estimate tokens for the response
        response_json = json.dumps(data)
        token_estimate = estimate_tokens(response_json)

        return {
            **data,
            "_meta": {
                "correlation_id": correlation_id,
                "took_ms": took_ms,
                "format": format_used.value,
                "token_estimate": token_estimate,
            }
        }
