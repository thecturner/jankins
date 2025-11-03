"""Progressive log retrieval client for Jenkins.

Uses Jenkins progressiveText API for efficient log streaming and retrieval
with byte offsets, avoiding full log downloads.
"""

import re
import logging
from typing import Optional, Tuple, List
from dataclasses import dataclass

from .adapter import JenkinsAdapter


logger = logging.getLogger(__name__)


@dataclass
class LogChunk:
    """A chunk of log data with metadata."""
    text: str
    start: int
    end: int
    has_more: bool


@dataclass
class LogSummary:
    """Summary of log content for token-efficient responses."""
    total_bytes: int
    total_lines: int
    error_count: int
    warning_count: int
    last_error_lines: List[str]
    failing_stages: List[str]
    is_complete: bool


class ProgressiveLogClient:
    """Client for retrieving Jenkins logs progressively.

    Uses the progressiveText API to fetch logs in chunks, supporting
    byte offsets and server-side filtering.
    """

    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    SECRET_MASK = re.compile(r'\*{4,}')  # Jenkins masks secrets with ****

    def __init__(self, adapter: JenkinsAdapter):
        self.adapter = adapter

    def get_progressive_text(
        self,
        job_name: str,
        build_number: int,
        start: int = 0,
    ) -> Tuple[str, int, bool]:
        """Get progressive log text from Jenkins.

        Args:
            job_name: Full job name (folder/subfolder/job)
            build_number: Build number
            start: Starting byte offset

        Returns:
            Tuple of (text, next_start, has_more)
        """
        # Encode job name for URL
        encoded_job = "/".join(f"job/{part}" for part in job_name.split("/"))
        path = f"/{encoded_job}/{build_number}/logText/progressiveText"

        response = self.adapter.rest_get(path, params={"start": start})

        # Get next offset from X-Text-Size header
        text_size = response.headers.get("X-Text-Size")
        next_start = int(text_size) if text_size else start + len(response.content)

        # Check if more data is available
        has_more = response.headers.get("X-More-Data", "false").lower() == "true"

        return response.text, next_start, has_more

    def get_log_chunk(
        self,
        job_name: str,
        build_number: int,
        start: int = 0,
        max_bytes: Optional[int] = None,
    ) -> LogChunk:
        """Get a chunk of log with byte limit.

        Args:
            job_name: Job name
            build_number: Build number
            start: Starting byte offset
            max_bytes: Maximum bytes to retrieve

        Returns:
            LogChunk with text and metadata
        """
        text, next_start, has_more = self.get_progressive_text(
            job_name,
            build_number,
            start=start
        )

        # Truncate if exceeds max_bytes
        if max_bytes and len(text.encode('utf-8')) > max_bytes:
            # Truncate to max_bytes, ensuring we don't split multi-byte characters
            text_bytes = text.encode('utf-8')[:max_bytes]
            text = text_bytes.decode('utf-8', errors='ignore')
            has_more = True

        return LogChunk(
            text=text,
            start=start,
            end=next_start,
            has_more=has_more
        )

    def get_tail(
        self,
        job_name: str,
        build_number: int,
        max_bytes: int,
    ) -> LogChunk:
        """Get the tail of a log (last N bytes).

        Args:
            job_name: Job name
            build_number: Build number
            max_bytes: Maximum bytes from end

        Returns:
            LogChunk with tail content
        """
        # First, get the total size by fetching from offset 0
        _, total_size, _ = self.get_progressive_text(job_name, build_number, start=0)

        # Calculate start offset for tail
        start = max(0, total_size - max_bytes)

        return self.get_log_chunk(job_name, build_number, start=start, max_bytes=max_bytes)

    def filter_log(
        self,
        text: str,
        pattern: Optional[str] = None,
        include_levels: Optional[List[str]] = None,
        redact: bool = False,
    ) -> str:
        """Filter and process log text.

        Args:
            text: Raw log text
            pattern: Regex pattern to match (only include matching lines)
            include_levels: Log levels to include (e.g., ["ERROR", "WARN"])
            redact: Remove ANSI codes and secret masks

        Returns:
            Filtered log text
        """
        lines = text.split('\n')
        filtered_lines = []

        for line in lines:
            # Apply level filter
            if include_levels:
                if not any(level in line for level in include_levels):
                    continue

            # Apply regex pattern
            if pattern:
                if not re.search(pattern, line):
                    continue

            # Apply redaction
            if redact:
                line = self.ANSI_ESCAPE.sub('', line)
                line = self.SECRET_MASK.sub('[REDACTED]', line)

            filtered_lines.append(line)

        return '\n'.join(filtered_lines)

    def summarize_log(
        self,
        job_name: str,
        build_number: int,
        max_bytes: int,
    ) -> LogSummary:
        """Generate a token-efficient summary of log content.

        Args:
            job_name: Job name
            build_number: Build number
            max_bytes: Maximum bytes to analyze

        Returns:
            LogSummary with key metrics
        """
        # Get tail of log for analysis
        chunk = self.get_tail(job_name, build_number, max_bytes)
        lines = chunk.text.split('\n')

        # Count errors and warnings
        error_count = sum(1 for line in lines if 'ERROR' in line.upper())
        warning_count = sum(1 for line in lines if 'WARN' in line.upper())

        # Extract last error lines (up to 5)
        error_lines = [line for line in lines if 'ERROR' in line.upper()]
        last_error_lines = error_lines[-5:] if error_lines else []

        # Detect failing stages (common in pipeline logs)
        failing_stages = []
        stage_fail_pattern = re.compile(r'Stage "([^"]+)" (failed|FAILED)')
        for line in lines:
            match = stage_fail_pattern.search(line)
            if match:
                failing_stages.append(match.group(1))

        return LogSummary(
            total_bytes=chunk.end,
            total_lines=len(lines),
            error_count=error_count,
            warning_count=warning_count,
            last_error_lines=last_error_lines,
            failing_stages=list(set(failing_stages)),  # Deduplicate
            is_complete=not chunk.has_more
        )

    def search_log(
        self,
        job_name: str,
        build_number: int,
        pattern: str,
        window_lines: int = 5,
        max_bytes: int = 1048576,  # 1MB default
    ) -> List[Tuple[int, str]]:
        """Search log for pattern and return matching lines with context.

        Args:
            job_name: Job name
            build_number: Build number
            pattern: Regex pattern to search for
            window_lines: Lines of context before/after match
            max_bytes: Maximum bytes to search

        Returns:
            List of (line_number, context_text) tuples
        """
        # Get log chunk
        chunk = self.get_log_chunk(job_name, build_number, start=0, max_bytes=max_bytes)
        lines = chunk.text.split('\n')

        matches = []
        pattern_re = re.compile(pattern)

        for i, line in enumerate(lines):
            if pattern_re.search(line):
                # Extract context window
                start_line = max(0, i - window_lines)
                end_line = min(len(lines), i + window_lines + 1)
                context = '\n'.join(lines[start_line:end_line])
                matches.append((i + 1, context))  # Line numbers are 1-indexed

        return matches
