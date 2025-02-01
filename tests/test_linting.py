###
# Copyright 2022-present MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###
"""Test file for checking Python linting."""

import logging
import sys
import unittest.mock

import mypy.api
import pydocstyle.cli
import pylint.lint


def test_linting() -> None:
    """Check code and tests for Python linting errors."""
    runner = pylint.lint.Run(
        ["--rcfile=../pyproject.toml", "../gdbmongo/", "../stubs/", "../tests/"], exit=False)
    lint_ok = runner.linter.msg_status == 0
    assert lint_ok, "Changes are needed to address linting issues"


def test_typechecking() -> None:
    """Check code and tests for Python type errors."""
    (normal_report, error_report, exit_status) = mypy.api.run(
        ["--config-file=../pyproject.toml", "../gdbmongo/", "../stubs/", "../tests/"])

    if normal_report:
        print("\nType checking report:\n", file=sys.stdout)
        print(normal_report, file=sys.stdout)

    if error_report:
        print("\nError report:\n", file=sys.stderr)
        print(error_report, file=sys.stderr)

    typecheck_ok = exit_status == 0
    assert typecheck_ok, "Changes are needed to address type annotation issues"


def test_docstrings() -> None:
    """Check docstrings for Python style errors."""
    with unittest.mock.patch(
            "sys.argv",
        ["", "--config=../pyproject.toml", "../gdbmongo/", "../stubs/", "../tests/"]):
        logger = logging.getLogger("pydocstyle.utils")
        # pydocstyle automatically configures its logger to level DEBUG. This leads pytest to
        # capture and display a large volume of log messages whenever there is a test assertion
        # failure. We override logging.Logger.setLevel() on pydocstyle's logger to prevent this.
        # Note that pytest automatically captures any messages at level WARNING and above.
        with unittest.mock.patch.object(logger, "setLevel"):
            exit_code = pydocstyle.cli.run_pydocstyle()

    docstrings_ok = exit_code == 0
    assert docstrings_ok, "Changes are needed to address docstring issues"
