"""Tests for build log analyzers."""

import pytest

from jankins.analyzers.gradle import GradleAnalyzer
from jankins.analyzers.maven import MavenAnalyzer
from jankins.analyzers.npm import NpmAnalyzer


@pytest.mark.unit
class TestMavenAnalyzer:
    """Test Maven log analyzer."""

    def test_detect_maven_log(self, sample_maven_log):
        """Test Maven log detection."""
        analyzer = MavenAnalyzer()
        assert analyzer.detect(sample_maven_log) is True

    def test_analyze_maven_log(self, sample_maven_log):
        """Test Maven log analysis."""
        analyzer = MavenAnalyzer()
        result = analyzer.analyze(sample_maven_log)

        assert result.tool_name == "maven"
        assert result.build_failed is True
        assert len(result.errors) > 0
        assert "cannot find symbol" in result.errors[0].lower()
        assert len(result.recommendations) > 0

    def test_maven_compilation_error(self):
        """Test Maven compilation error detection."""
        log = """
        [ERROR] COMPILATION ERROR
        [ERROR] /path/to/File.java:[15,10] incompatible types
        """
        analyzer = MavenAnalyzer()
        result = analyzer.analyze(log)

        assert result.build_failed is True
        assert any("incompatible types" in e.lower() for e in result.errors)

    def test_maven_dependency_error(self):
        """Test Maven dependency resolution error."""
        log = """
        [ERROR] Failed to execute goal on project test: Could not resolve dependencies
        [ERROR] Could not find artifact com.example:missing-lib:jar:1.0.0
        """
        analyzer = MavenAnalyzer()
        result = analyzer.analyze(log)

        assert result.build_failed is True
        assert any("dependency" in r.lower() for r in result.recommendations)


@pytest.mark.unit
class TestGradleAnalyzer:
    """Test Gradle log analyzer."""

    def test_detect_gradle_log(self, sample_gradle_log):
        """Test Gradle log detection."""
        analyzer = GradleAnalyzer()
        assert analyzer.detect(sample_gradle_log) is True

    def test_analyze_gradle_log(self, sample_gradle_log):
        """Test Gradle log analysis."""
        analyzer = GradleAnalyzer()
        result = analyzer.analyze(sample_gradle_log)

        assert result.tool_name == "gradle"
        assert result.build_failed is True
        assert len(result.errors) > 0
        assert len(result.recommendations) > 0

    def test_gradle_task_failure(self):
        """Test Gradle task failure detection."""
        log = """
        > Task :test FAILED
        TestClass > testMethod FAILED
            java.lang.AssertionError at TestClass.java:42
        """
        analyzer = GradleAnalyzer()
        result = analyzer.analyze(log)

        assert result.build_failed is True
        assert result.failed_tasks == [":test"]

    def test_gradle_daemon_crash(self):
        """Test Gradle daemon crash detection."""
        log = """
        FAILURE: Build failed with an exception.
        * What went wrong:
        Gradle build daemon disappeared unexpectedly
        """
        analyzer = GradleAnalyzer()
        result = analyzer.analyze(log)

        assert result.build_failed is True
        assert any("daemon" in r.lower() for r in result.recommendations)


@pytest.mark.unit
class TestNpmAnalyzer:
    """Test NPM log analyzer."""

    def test_detect_npm_log(self, sample_npm_log):
        """Test NPM log detection."""
        analyzer = NpmAnalyzer()
        assert analyzer.detect(sample_npm_log) is True

    def test_analyze_npm_log(self, sample_npm_log):
        """Test NPM log analysis."""
        analyzer = NpmAnalyzer()
        result = analyzer.analyze(sample_npm_log)

        assert result.tool_name == "npm"
        assert result.build_failed is True
        assert len(result.errors) > 0
        assert "ENOENT" in result.error_codes

    def test_npm_module_not_found(self):
        """Test NPM module not found error."""
        log = """
        npm ERR! code MODULE_NOT_FOUND
        npm ERR! Cannot find module 'missing-package'
        """
        analyzer = NpmAnalyzer()
        result = analyzer.analyze(log)

        assert result.build_failed is True
        assert "MODULE_NOT_FOUND" in result.error_codes
        assert any("npm install" in r.lower() for r in result.recommendations)

    def test_npm_memory_error(self):
        """Test NPM out of memory error."""
        log = """
        FATAL ERROR: CALL_AND_RETRY_LAST Allocation failed - JavaScript heap out of memory
        """
        analyzer = NpmAnalyzer()
        result = analyzer.analyze(log)

        assert result.build_failed is True
        assert any("memory" in r.lower() for r in result.recommendations)

    def test_yarn_detection(self):
        """Test Yarn log detection."""
        log = """
        yarn run v1.22.0
        error Command failed with exit code 1.
        """
        analyzer = NpmAnalyzer()
        assert analyzer.detect(log) is True

        result = analyzer.analyze(log)
        assert result.build_failed is True
