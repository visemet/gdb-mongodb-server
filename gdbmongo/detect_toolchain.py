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
import shutil
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

    gcc_version_regexp = re.compile(rb"(?:^|\x00)(GCC: \(GNU\) \d+\.\d+\.\d+)(?:\x00|$)")
    clang_version_regexp = re.compile(rb"(?:^|\x00)(MongoDB clang version \d+\.\d+\.\d+)")

    libstdcxx_python_home_v3 = pathlib.Path("/opt/mongodbtoolchain/v3/share/gcc-8.5.0/python")
    libstdcxx_python_home_v4 = pathlib.Path("/opt/mongodbtoolchain/v4/share/gcc-11.3.0/python")

    def __init__(self, executable: StrOrBytesPath, /):
        """Initialize the ToolchainVersionDetector with the pathname of an executable."""
        self.executable = executable

    @classmethod
    def locate_objcopy(cls) -> typing.Optional[str]:
        """Return the location of an objcopy executable from the MongoDB toolchain."""
        # The objcopy executable in the MongoDB v4 toolchain supports reading binaries which were
        # compiled for a different platform. We prefer using it for this reason. However, not all
        # Evergreen distros have the MongoDB v4 toolchain available and so we also allow falling
        # back to the MongoDB v3 toolchain.
        return shutil.which(
            "objcopy", path=os.pathsep.join(
                ("/opt/mongodbtoolchain/v4/bin/", "/opt/mongodbtoolchain/v3/bin/")))

    @classmethod
    def readelf(cls, executable: StrOrBytesPath, /) -> bytes:
        """Return the ELF .comment section of the executable.

        The ELF .comment section contains information about which compiler(s) were used in building
        the executable.
        """
        if (objcopy := cls.locate_objcopy()) is None:
            warnings.warn(
                "Unable to locate a known objcopy executable. Is the MongoDB toolchain installed?")
            return b""

        with tempfile.NamedTemporaryFile() as output_file:
            # objcopy overwrites the input executable when only given one positional argument.
            # /dev/null is specified as the second positional argument to simultaneously prevent the
            # executable file from being overwritten and to discard the generated copy.
            result = subprocess.run([
                objcopy, "--dump-section", f".comment={str(output_file.name)}", executable,
                "/dev/null"
            ], capture_output=True, check=False, encoding="utf-8", text=True)

            if result.returncode == 0:
                return output_file.read()

        warnings.warn(f"Unable to detect the compiler version in {shlex.quote(str(executable))}."
                      f" {result.stderr}")
        return b""

    @classmethod
    def parse_gcc_version(cls, raw_elf_section: bytes, /) -> typing.Optional[str]:
        """Extract the GCC compiler version from the ELF .comment section text.

        It is expected for a GCC compiler version to be listed due to the use of libstdc++ in all
        MongoDB binaries.
        """
        if (match := cls.gcc_version_regexp.search(raw_elf_section)) is not None:
            return match.group(1).decode()

        return None

    @classmethod
    def parse_clang_version(cls, raw_elf_section: bytes, /) -> typing.Optional[str]:
        """Extract the clang compiler version from ELF .comment section text, if present."""
        if (match := cls.clang_version_regexp.search(raw_elf_section)) is not None:
            return match.group(1).decode()

        return None

    @classmethod
    def parse_libstdcxx_python_home_from_gcc_version(cls, gcc_version: str,
                                                     /) -> typing.Optional[pathlib.Path]:
        """Return the /opt/mongodbtoolchain/vN/share/gcc-X.Y.Z/python directory associated with a
        particular GCC compiler version.
        """
        if gcc_version.endswith((" 8.5.0", " 8.3.0", " 8.2.0")):
            # The v3 toolchain was upgraded from GCC 8.2.0 to GCC 8.3.0 in BUILD-12151 and upgraded
            # again from GCC 8.3.0 to GCC 8.5.0 in BUILD-12619. The gcc-8.5.0/ directory is used for
            # binaries compiled with any of those compiler versions because we expect the machine to
            # be running the latest version of the MongoDB toolchain, even when it is for inspecting
            # older binaries.
            return cls.libstdcxx_python_home_v3

        if gcc_version.endswith((" 11.3.0", " 11.2.0")):
            # The v4 toolchain was upgraded from GCC 11.2.0 to GCC 11.3.0 in BUILD-14919 prior to
            # the official v4 toolchain rollout. The gcc-11.3.0/ directory is used for binaries
            # compiled with any of those compiler versions because we expect the machine to be
            # running the latest version of the MongoDB toolchain, even when it is for inspecting
            # older binaries.
            return cls.libstdcxx_python_home_v4

        warnings.warn(
            "Unable to determine the location of the libstdc++ GDB pretty printers. Please file a"
            " GitHub issue against https://github.com/visemet/gdb-mongodb-server and mention your "
            f"compiler version was {gcc_version}")
        return None

    @classmethod
    def parse_libstdcxx_python_home_from_clang_version(cls, clang_version: str,
                                                       /) -> typing.Optional[pathlib.Path]:
        """Return the /opt/mongodbtoolchain/vN/share/gcc-X.Y.Z/python directory associated with a
        particular Clang compiler version.
        """
        if clang_version.endswith(" 7.0.1"):
            return cls.libstdcxx_python_home_v3

        if clang_version.endswith(" 12.0.1"):
            return cls.libstdcxx_python_home_v4

        warnings.warn(
            "Unable to determine the location of the libstdc++ GDB pretty printers. Please file a"
            " GitHub issue against https://github.com/visemet/gdb-mongodb-server and mention your "
            f"compiler version was {clang_version}")
        return None

    def detect(self) -> ToolchainInfo:
        """Detect info about the MongoDB toolchain used to compile an executable."""
        if not (raw_elf_section := self.readelf(self.executable)):
            return ToolchainInfo(None, None)

        if (clang_version := self.parse_clang_version(raw_elf_section)) is not None:
            compiler = clang_version
            parse_libstdcxx_python_home = self.parse_libstdcxx_python_home_from_clang_version
        elif (gcc_version := self.parse_gcc_version(raw_elf_section)) is not None:
            compiler = gcc_version
            parse_libstdcxx_python_home = self.parse_libstdcxx_python_home_from_gcc_version
        else:
            warnings.warn(
                f"Unable to detect the compiler version in {shlex.quote(str(self.executable))}."
                " The executable doesn't appear to have been compiled with libstdc++ based on"
                f" its ELF .comment section: {raw_elf_section!r}")
            return ToolchainInfo(None, None)

        if (libstdcxx_python_home := parse_libstdcxx_python_home(compiler)) is None:
            return ToolchainInfo(None, None)

        return ToolchainInfo(compiler=compiler, libstdcxx_python_home=libstdcxx_python_home)
