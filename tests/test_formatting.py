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
"""Test file for checking Python formatting."""

import distutils.util
import os

import pytest


def run_yapf(yapf, fix: bool) -> bool:
    """Return True if YAPF reports no further changes are needed, and return False otherwise.

    This function always returns True when fix == True."""

    ret = yapf.main([
        None,
        "--in-place" if fix else "--diff",
        "--recursive",
        "--verbose",
        "../gdbmongo/",
        "../tests/",
    ])

    return ret == 0 or fix


@pytest.mark.filterwarnings(r"ignore:lib2to3 package is deprecated.*:PendingDeprecationWarning")
def test_formatting():
    """Check code and tests for Python formatting errors."""
    # We import the module here to suppress the PendingDeprecationWarning.
    # pylint: disable-next=import-outside-toplevel
    import yapf

    should_fix = distutils.util.strtobool(os.environ.get("TOX_YAPF_FIX", "0"))
    format_ok = run_yapf(yapf, should_fix)
    assert format_ok, "Changes are needed to address formatting issues; try running `tox -e format`"
