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

import itertools
import os
import pathlib
import typing

import pytest


def find_pyfiles() -> typing.Iterator[pathlib.Path]:
    """Return an iterator of the files to format."""
    return itertools.chain(
        pathlib.Path("../gdbmongo").rglob("*.py"),
        pathlib.Path("../gdbmongo").rglob("*.pyi"),
        pathlib.Path("../stubs").rglob("*.pyi"),
        pathlib.Path("../tests").rglob("*.py"))


def run_yapf(fix: bool) -> bool:
    """Return True if YAPF reports no further changes are needed, and return False otherwise.

    This function always returns True when fix == True.
    """
    # We import the module here to suppress the PendingDeprecationWarning.
    # pylint: disable-next=import-outside-toplevel
    import yapf

    ret = yapf.main([
        "",
        "--in-place" if fix else "--diff",
        "--verbose",
    ] + [str(path) for path in find_pyfiles() if path != pathlib.Path("../gdbmongo/_version.py")])

    return ret == 0 or fix


# Adapted from the definition for distutils.util.strtobool() in Python 3.11.1 to accommodate the
# deprecation of the distutils module (PEP 632).
def strtobool(val: str) -> bool:
    """Convert a string representation of truth to True or False.

    True values are "y", "yes", "t", "true", "on", and "1".
    False values are "n", "no", "f", "false", "off", and "0".

    Raises a ValueError if `val` is any other value.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True

    if val in ("n", "no", "f", "false", "off", "0"):
        return False

    raise ValueError(f"Invalid truth value: {val!r}")


@pytest.mark.filterwarnings(r"ignore:lib2to3 package is deprecated.*:PendingDeprecationWarning")
def test_formatting() -> None:
    """Check code and tests for Python formatting errors."""
    should_fix = strtobool(os.environ.get("TOX_YAPF_FIX", "0"))
    format_ok = run_yapf(should_fix)
    assert format_ok, "Changes are needed to address formatting issues; try running `tox -e format`"
