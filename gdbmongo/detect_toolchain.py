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
"""Detect info about the MongoDB toolchain used to compile an executable."""

import os
import pathlib
import re
import shlex
import subprocess
import tempfile
import typing
import warnings


class ToolchainInfo(typing.NamedTuple):
    """Info about the MongoDB toolchain used to compile an executable."""
    compiler: typing.Optional[str]
    libstdcxx_python_home: typing.Optional[pathlib.Path]


StrOrBytesPath = typing.Union[str, bytes, os.PathLike]


class ToolchainVersionDetector:
    """Detect info about the MongoDB toolchain used to compile an executable."""

    objcopy = "/opt/mongodbtoolchain/v3/bin/objcopy"

    gcc_version_regexp = re.compile(rb"(?:^|\x00)(GCC: \(GNU\) \d+\.\d+\.\d+)(?:\x00|$)")
    clang_version_regexp = re.compile(rb"(?:^|\x00)(MongoDB clang version \d+\.\d+\.\d+)")

    def __init__(self, executable: StrOrBytesPath):
        """Initialize the ToolchainVersionDetector with the pathname of an executable."""
        self.executable = executable

    @classmethod
    def readelf(cls, executable: StrOrBytesPath) -> bytes:
        """Return the ELF .comment section of the executable.

        The ELF .comment section contains information about which compiler(s) were used in building
        the executable."""

        with tempfile.NamedTemporaryFile() as output_file:
            result = subprocess.run(
                [cls.objcopy, "--dump-section", f".comment={str(output_file.name)}", executable],
                capture_output=True, check=False, encoding="utf-8", text=True)

            if result.returncode == 0:
                return output_file.read()

        warnings.warn(
            f"Unable to detect the compiler version in {shlex.quote(str(executable))}. Is the"
            f" MongoDB toolchain installed? {result.stderr}")
        return b""

    @classmethod
    def parse_gcc_version(cls, raw_elf_section: bytes,
                          executable: StrOrBytesPath) -> typing.Optional[str]:
        """Extract the GCC compiler version from the ELF .comment section text.

        It is expected for a GCC compiler version to be listed due to the use of libstdc++ in all
        MongoDB binaries."""

        if (match := cls.gcc_version_regexp.search(raw_elf_section)) is not None:
            return match.group(1).decode()

        warnings.warn(
            f"Unable to detect the compiler version in {shlex.quote(str(executable))}."
            " The executable doesn't appear to have been compiled with libstdc++ based on its ELF"
            f" .comment section: {raw_elf_section!r}")
        return None

    @classmethod
    def parse_clang_version(cls, raw_elf_section: bytes) -> typing.Optional[str]:
        """Extract the clang compiler version from ELF .comment section text, if present."""
        if (match := cls.clang_version_regexp.search(raw_elf_section)) is not None:
            return match.group(1).decode()

        return None

    @classmethod
    def parse_libstdcxx_python_home(cls, gcc_version: str) -> typing.Optional[pathlib.Path]:
        """Return the /opt/mongodbtoolchain/vN/share/gcc-X.Y.Z/python directory associated with a
        particular GCC compiler version."""

        if gcc_version.endswith(" 8.5.0"):
            return pathlib.Path("/opt/mongodbtoolchain/v3/share/gcc-8.5.0/python")

        if gcc_version.endswith(" 11.2.0"):
            return pathlib.Path("/opt/mongodbtoolchain/v4/share/gcc-11.2.0/python")

        warnings.warn(
            f"Unable to determine the location of the libstdc++ GDB pretty printers. Please file a"
            f" GitHub issue and mention your compiler version was {gcc_version}")
        return None

    def detect(self) -> ToolchainInfo:
        """Detect info about the MongoDB toolchain used to compile an executable."""
        if not (raw_elf_section := self.readelf(self.executable)):
            return ToolchainInfo(None, None)

        if (gcc_version := self.parse_gcc_version(raw_elf_section, self.executable)) is None:
            return ToolchainInfo(None, None)

        if (libstdcxx_python_home := self.parse_libstdcxx_python_home(gcc_version)) is None:
            return ToolchainInfo(None, None)

        if (clang_version := self.parse_clang_version(raw_elf_section)) is not None:
            compiler = clang_version
        else:
            compiler = gcc_version

        return ToolchainInfo(compiler=compiler, libstdcxx_python_home=libstdcxx_python_home)
