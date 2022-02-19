"""Test file for checking Python linting."""

import pylint.lint
import pytest


@pytest.mark.filterwarnings(r"ignore:In astroid 3.0.0 NodeNG.statement\(\).*:DeprecationWarning")
def test_linting():
    """Check code and tests for Python linting errors."""
    runner = pylint.lint.Run(["../gdbmongo/", "../tests/"], exit=False)
    assert runner.linter.msg_status == 0, "Changes are needed to address linting issues"
