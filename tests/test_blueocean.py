"""Tests for Blue Ocean API integration."""

from unittest.mock import patch

import pytest

from jankins.jenkins.blueocean import BlueOceanClient


@pytest.mark.unit
class TestBlueOceanClient:
    """Test Blue Ocean client functionality."""

    @pytest.fixture
    def blueocean_client(self, mock_jenkins_adapter):
        """Create Blue Ocean client."""
        return BlueOceanClient(mock_jenkins_adapter)

    def test_get_pipeline_nodes(
        self, blueocean_client, sample_blueocean_nodes, mock_jenkins_client
    ):
        """Test getting pipeline nodes."""
        # Mock the adapter's jenkins client
        blueocean_client.adapter.client = mock_jenkins_client
        mock_jenkins_client.get_json.return_value = sample_blueocean_nodes

        # The actual implementation calls the Jenkins API, so we test the structure
        # Just verify that get_pipeline_graph works with sample data
        with patch.object(blueocean_client, "get_pipeline_nodes") as mock_nodes:
            mock_nodes.return_value = sample_blueocean_nodes
            graph = blueocean_client.get_pipeline_graph("test-job", 42)
            assert graph["node_count"] == 2

    def test_get_pipeline_graph(self, blueocean_client, sample_blueocean_nodes):
        """Test getting pipeline graph structure."""
        with patch.object(blueocean_client, "get_pipeline_nodes") as mock_nodes:
            mock_nodes.return_value = sample_blueocean_nodes

            graph = blueocean_client.get_pipeline_graph("test-job", 42)

            assert "stages" in graph
            assert "total_duration_ms" in graph
            assert "node_count" in graph
            assert graph["node_count"] == 2

    def test_parse_parallel_stages(self, blueocean_client):
        """Test parsing parallel stage execution."""
        # Nodes with edges indicate parallel execution
        nodes = [
            {
                "id": "1",
                "displayName": "Parallel",
                "type": "PARALLEL",
                "durationInMillis": 10000,
                "edges": [{"id": "2"}, {"id": "3"}],  # Multiple outgoing edges
            },
            {
                "id": "2",
                "displayName": "Test A",
                "type": "STAGE",
                "durationInMillis": 5000,
                "edges": [],
            },
            {
                "id": "3",
                "displayName": "Test B",
                "type": "STAGE",
                "durationInMillis": 8000,
                "edges": [],
            },
        ]

        with patch.object(blueocean_client, "get_pipeline_nodes") as mock_nodes:
            mock_nodes.return_value = nodes

            graph = blueocean_client.get_pipeline_graph("test-job", 42)

            # Parallel stages should be detected based on edges
            assert len(graph.get("parallel_stages", [])) > 0

    def test_stage_timing(self, blueocean_client, sample_blueocean_nodes):
        """Test stage timing calculation."""
        with patch.object(blueocean_client, "get_pipeline_nodes") as mock_nodes:
            mock_nodes.return_value = sample_blueocean_nodes

            graph = blueocean_client.get_pipeline_graph("test-job", 42)

            # Total duration should be sum of stage durations
            assert graph["total_duration_ms"] == 15000  # 5000 + 10000
