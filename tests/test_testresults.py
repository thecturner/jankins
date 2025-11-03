"""Tests for test result parsing."""

import pytest

from jankins.jenkins.testresults import (
    TestReport as TestReportModel,
    TestResultParserImpl as TestResultParserImplImpl,
    TestSuiteModel as TestSuiteModelModel,
)


@pytest.mark.unit
class TestTestResultParserImpl:
    """Test test result parser functionality."""

    def test_parse_test_report(self, sample_test_report):
        """Test parsing test report."""
        parser = TestResultParserImplImpl()
        report = parser.parse_test_report(sample_test_report)

        assert isinstance(report, TestReportModel)
        assert report.total_tests == 100
        assert report.passed == 98
        assert report.failed == 2
        assert report.skipped == 0

    def test_parse_test_suites(self, sample_test_report):
        """Test parsing test suites."""
        parser = TestResultParserImpl()
        report = parser.parse_test_report(sample_test_report)

        assert len(report.suites) == 1
        suite = report.suites[0]
        assert isinstance(suite, TestSuiteModel)
        assert suite.name == "TestSuiteModel1"

    def test_parse_test_cases(self, sample_test_report):
        """Test parsing test cases."""
        parser = TestResultParserImpl()
        report = parser.parse_test_report(sample_test_report)

        suite = report.suites[0]
        assert len(suite.cases) == 2

        # Check passed test
        passed_test = suite.cases[0]
        assert passed_test.name == "test_success"
        assert passed_test.status == "PASSED"
        assert passed_test.duration == 0.1

        # Check failed test
        failed_test = suite.cases[1]
        assert failed_test.name == "test_failure"
        assert failed_test.status == "FAILED"
        assert failed_test.error_details == "AssertionError: Expected 1, got 2"

    def test_pass_rate_calculation(self, sample_test_report):
        """Test pass rate calculation."""
        parser = TestResultParserImpl()
        report = parser.parse_test_report(sample_test_report)

        assert report.pass_rate == 98.0

    def test_empty_test_report(self):
        """Test parsing empty test report."""
        parser = TestResultParserImpl()
        empty_report = {
            "duration": 0,
            "failCount": 0,
            "passCount": 0,
            "skipCount": 0,
            "suites": [],
        }

        report = parser.parse_test_report(empty_report)
        assert report.total_tests == 0
        assert report.pass_rate == 0.0

    def test_get_failed_tests(self, sample_test_report):
        """Test extracting failed tests."""
        parser = TestResultParserImpl()
        report = parser.parse_test_report(sample_test_report)

        failed_tests = [
            case for suite in report.suites for case in suite.cases if case.status == "FAILED"
        ]

        assert len(failed_tests) == 1
        assert failed_tests[0].name == "test_failure"

    def test_compare_test_reports(self, sample_test_report):
        """Test comparing two test reports."""
        parser = TestResultParserImpl()

        # Create two reports
        report1 = parser.parse_test_report(sample_test_report)

        # Modify for second report
        modified_report = sample_test_report.copy()
        modified_report["failCount"] = 0
        modified_report["passCount"] = 100
        report2 = parser.parse_test_report(modified_report)

        # Compare
        assert report1.failed > report2.failed
        assert report2.pass_rate > report1.pass_rate

    def test_flaky_test_detection(self):
        """Test detecting flaky tests across builds."""
        # This would test the detect_flaky_tests logic
        # For now, basic structure test - placeholder for future implementation
        # parser = TestResultParserImpl()

        # builds_data = [
        #     {"name": "test_foo", "status": "PASSED"},
        #     {"name": "test_foo", "status": "FAILED"},
        #     {"name": "test_foo", "status": "PASSED"},
        #     {"name": "test_bar", "status": "PASSED"},
        #     {"name": "test_bar", "status": "PASSED"},
        # ]

        # test_foo changes status - flaky
        # test_bar consistent - not flaky
        # Implementation would go in the actual analyzer
        pass
