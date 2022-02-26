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

import pylint.lint
import pytest


@pytest.mark.filterwarnings(r"ignore:In astroid 3.0.0 NodeNG.statement\(\).*:DeprecationWarning")
def test_linting():
    """Check code and tests for Python linting errors."""
    runner = pylint.lint.Run(["../gdbmongo/", "../tests/", "--rcfile=../pyproject.toml"],
                             exit=False)
    lint_ok = runner.linter.msg_status == 0
    assert lint_ok, "Changes are needed to address linting issues"
