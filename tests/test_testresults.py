"""Tests for test result parsing."""

import pytest

from jankins.jenkins.testresults import TestCase as _TestCase
from jankins.jenkins.testresults import TestReport as _TestReport
from jankins.jenkins.testresults import TestSuite as _TestSuite


@pytest.mark.unit
class TestTestResultParser:
    """Test test result data classes."""

    def test_test_report_creation(self):
        """Test creating test report."""
        report = _TestReport(
            total_tests=100, passed=98, failed=2, skipped=0, errors=0, duration=15.5, suites=[]
        )

        assert report.total_tests == 100
        assert report.passed == 98
        assert report.failed == 2
        assert report.skipped == 0

    def test_test_suite_creation(self):
        """Test creating test suite."""
        suite = _TestSuite(
            name="TestSuite1",
            tests=2,
            failures=1,
            errors=0,
            skipped=0,
            duration=0.3,
            test_cases=[],
        )

        assert suite.name == "TestSuite1"
        assert suite.tests == 2
        assert suite.failures == 1

    def test_test_case_creation(self):
        """Test creating test cases."""
        passed_test = _TestCase(
            name="test_success",
            class_name="test.TestClass",
            status="PASSED",
            duration=0.1,
        )

        assert passed_test.name == "test_success"
        assert passed_test.status == "PASSED"
        assert passed_test.duration == 0.1

        failed_test = _TestCase(
            name="test_failure",
            class_name="test.TestClass",
            status="FAILED",
            duration=0.2,
            error_message="AssertionError: Expected 1, got 2",
        )

        assert failed_test.name == "test_failure"
        assert failed_test.status == "FAILED"
        assert failed_test.error_message == "AssertionError: Expected 1, got 2"

    def test_pass_rate_calculation(self):
        """Test pass rate calculation."""
        report = _TestReport(
            total_tests=100, passed=98, failed=2, skipped=0, errors=0, duration=15.5, suites=[]
        )

        assert report.pass_rate == 98.0

    def test_empty_test_report(self):
        """Test empty test report."""
        empty_report = _TestReport(
            total_tests=0, passed=0, failed=0, skipped=0, errors=0, duration=0, suites=[]
        )
        assert empty_report.total_tests == 0
        assert empty_report.pass_rate == 0.0

    def test_get_failed_tests(self):
        """Test extracting failed tests."""
        failed_case = _TestCase(
            name="test_failure",
            class_name="test.TestClass",
            status="FAILED",
            duration=0.2,
            error_message="AssertionError",
        )
        passed_case = _TestCase(
            name="test_success",
            class_name="test.TestClass",
            status="PASSED",
            duration=0.1,
        )

        suite = _TestSuite(
            name="TestSuite1",
            tests=2,
            failures=1,
            errors=0,
            skipped=0,
            duration=0.3,
            test_cases=[passed_case, failed_case],
        )

        report = _TestReport(
            total_tests=2, passed=1, failed=1, skipped=0, errors=0, duration=0.3, suites=[suite]
        )

        failed_tests = [
            case for suite in report.suites for case in suite.test_cases if case.status == "FAILED"
        ]

        assert len(failed_tests) == 1
        assert failed_tests[0].name == "test_failure"

    def test_compare_test_reports(self):
        """Test comparing two test reports."""
        report1 = _TestReport(
            total_tests=100, passed=98, failed=2, skipped=0, errors=0, duration=15.5, suites=[]
        )

        report2 = _TestReport(
            total_tests=100, passed=100, failed=0, skipped=0, errors=0, duration=15.5, suites=[]
        )

        # Compare
        assert report1.failed > report2.failed
        assert report2.pass_rate > report1.pass_rate

    def test_flaky_test_detection(self):
        """Test flaky test detection placeholder."""
        # This would test the detect_flaky_tests logic
        # For now, basic structure test - placeholder for future implementation
        pass
