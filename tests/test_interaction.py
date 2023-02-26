###
# Copyright 2023-present MongoDB, Inc.
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
"""Test file for the interaction.py module."""

import subprocess
import tempfile
import typing

FAKE_GDBINIT = """\
set confirm off
set python print-stack full

python
import gdbmongo

# Skip importing the libstdc++ GDB pretty printers. This enables running GDB with an executable file
# but without that executable file needing to be a real MongoDB binary.
def init_mock():
    from unittest.mock import Mock
    from gdbmongo import interaction
    interaction.resolve_import = Mock(return_value=("", lambda: None))

init_mock()
del init_mock

gdbmongo.register_printers()
end
"""


def run_interactive_gdb(
        input_commands: str, /, *,
        executable: typing.Optional[str] = None) -> subprocess.CompletedProcess[str]:
    """Launch a GDB session with the in-development version of the gdbmongo package loaded.

    The input commands are submitted by acting as though a human is typing in a series of commands.
    The `quit` command is automatically added as the final command.

    All output and/or errors from running the commands are captured and returned.
    """
    assert not input_commands or input_commands[-1] == "\n"
    input_commands += "quit\n"

    # Setting PYTHONPATH to the root of the gdb-mongodb-server repository makes it so
    # `import gdbmongo` will refer to the in-development version of gdbmongo without needing to
    # install the package into the MongoDB toolchain Python to test it.
    #
    # Setting XDG_CACHE_HOME to any value suppresses the
    # "Couldn't determine a path for the index cache directory." warning message. /dev/null is used
    # because the index cache directory isn't needed for these Python tests.
    env = dict(PYTHONPATH="..", XDG_CACHE_HOME="/dev/null")

    with tempfile.NamedTemporaryFile(mode="wt") as command_file:
        command_file.write(FAKE_GDBINIT)
        command_file.flush()

        argv = [
            "/opt/mongodbtoolchain/v4/bin/gdb", "--silent", "-nx", "--init-command",
            command_file.name
        ]

        if executable is not None:
            argv.append(executable)

        return subprocess.run(argv, text=True, capture_output=True, check=True,
                              input=input_commands, env=env)


def test_gdb_at_prompt_no_target() -> None:
    """Check that no GDB errors are emitted from displaying the prompt when there isn't an
    executable file loaded, or a core dump file loaded, or a live process attached.
    """
    stderr = run_interactive_gdb("\n" * 10).stderr
    assert not stderr, stderr


def test_gdb_initial_start_with_executable() -> None:
    """Check that no GDB errors are emitted from launching GDB with an executable file."""
    stderr = run_interactive_gdb("", executable="/bin/ls").stderr
    assert not stderr, stderr
