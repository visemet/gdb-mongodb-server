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
"""Test file for the detect_toolchain.py module."""

import pathlib
import shutil
import tarfile
import tempfile
import urllib.request

import pytest

from gdbmongo.detect_toolchain import ToolchainInfo, ToolchainVersionDetector


@pytest.mark.parametrize(
    ("raw_elf_section", "expected"),
    (
        pytest.param(b"\x00GCC: (GNU) 8.5.0\x00", "GCC: (GNU) 8.5.0", id="gcc-simple"),
        pytest.param(
            # pylint: disable-next=line-too-long
            b"\x00GCC: (GNU) 8.5.0\x00MongoDB clang version 7.0.1 (tags/RELEASE_701/final) (based on LLVM 7.0.1)\x00",
            "GCC: (GNU) 8.5.0",
            id="gcc-with-clang"),
        pytest.param(b"\x00GCC: (GNU) 8.2.1 20180905 (Red Hat 8.2.1-3)\x00GCC: (GNU) 11.2.0\x00",
                     "GCC: (GNU) 11.2.0", id="gcc-with-multiple-gcc"),
        pytest.param(
            # pylint: disable-next=line-too-long
            b"GCC: (GNU) 8.5.0\x00Linker: LLD 7.0.1\x00MongoDB clang version 7.0.1 (tags/RELEASE_701/final) (based on LLVM 7.0.1)\x00\x00",
            "GCC: (GNU) 8.5.0",
            id="gcc-with-clang-and-lld"),
    ))
def test_parse_gcc_version(raw_elf_section: bytes, expected: str):
    """Check the extracted GCC compiler version from a sample ELF .comment section."""
    assert ToolchainVersionDetector.parse_gcc_version(raw_elf_section, executable="") == expected


@pytest.mark.parametrize(
    ("raw_elf_section", "expected"),
    (
        pytest.param(b"\x00GCC: (GNU) 8.5.0\x00", None, id="clang-missing"),
        pytest.param(
            # pylint: disable-next=line-too-long
            b"\x00MongoDB clang version 7.0.1 (tags/RELEASE_701/final) (based on LLVM 7.0.1)\x00",
            "MongoDB clang version 7.0.1",
            id="clang-simple"),
        pytest.param(
            # pylint: disable-next=line-too-long
            b"\x00GCC: (GNU) 8.2.1 20180905 (Red Hat 8.2.1-3)\x00GCC: (GNU) 11.2.0\x00MongoDB clang version 12.0.1 (git@github.com:10gen/toolchain-builder.git c6da1cf7f0b4b60d53566305e59857d3d540dcf7)\x00",
            "MongoDB clang version 12.0.1",
            id="clang-with-multiple-gcc"),
    ))
def test_parse_clang_version(raw_elf_section: bytes, expected: str):
    """Check the extracted clang compiler version from a sample ELF .comment section."""
    clang_version = ToolchainVersionDetector.parse_clang_version(raw_elf_section)

    if expected is None:
        assert clang_version is None
    else:
        assert clang_version == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    (
        pytest.param(
            # pylint: disable-next=line-too-long
            "https://mciuploads.s3.amazonaws.com/mongodb-mongo-master/ubuntu1804-debug-suggested/125deb74c63c74f46b0c53f49d3b229592b510bb/binaries/mongo-mongodb_mongo_master_ubuntu1804_debug_suggested_125deb74c63c74f46b0c53f49d3b229592b510bb_22_02_20_01_54_48.tgz",
            ToolchainInfo("GCC: (GNU) 8.5.0",
                          pathlib.Path("/opt/mongodbtoolchain/v3/share/gcc-8.5.0/python")),
            id="v3-gcc"),
        pytest.param(
            # pylint: disable-next=line-too-long
            "https://mciuploads.s3.amazonaws.com/mongodb-mongo-master/ubuntu1804-debug-aubsan-lite-required/125deb74c63c74f46b0c53f49d3b229592b510bb/binaries/mongo-mongodb_mongo_master_ubuntu1804_debug_aubsan_lite_required_125deb74c63c74f46b0c53f49d3b229592b510bb_22_02_20_01_54_48.tgz",
            ToolchainInfo("MongoDB clang version 7.0.1",
                          pathlib.Path("/opt/mongodbtoolchain/v3/share/gcc-8.5.0/python")),
            id="v3-clang"),
        pytest.param(
            # pylint: disable-next=line-too-long
            "https://mciuploads.s3.amazonaws.com/mongodb-mongo-master/enterprise-rhel80-dynamic-v4gcc-debug-experimental/125deb74c63c74f46b0c53f49d3b229592b510bb/binaries/mongo-mongodb_mongo_master_enterprise_rhel80_dynamic_v4gcc_debug_experimental_125deb74c63c74f46b0c53f49d3b229592b510bb_22_02_20_01_54_48.tgz",
            ToolchainInfo("GCC: (GNU) 11.2.0",
                          pathlib.Path("/opt/mongodbtoolchain/v4/share/gcc-11.2.0/python")),
            id="v4-gcc"),
        pytest.param(
            # pylint: disable-next=line-too-long
            "https://mciuploads.s3.amazonaws.com/mongodb-mongo-master/enterprise-rhel80-dynamic-v4clang-debug-experimental/125deb74c63c74f46b0c53f49d3b229592b510bb/binaries/mongo-mongodb_mongo_master_enterprise_rhel80_dynamic_v4clang_debug_experimental_125deb74c63c74f46b0c53f49d3b229592b510bb_22_02_20_01_54_48.tgz",
            ToolchainInfo("MongoDB clang version 12.0.1",
                          pathlib.Path("/opt/mongodbtoolchain/v4/share/gcc-11.2.0/python")),
            id="v4-clang"),
    ))
def test_detected_toolchain_from_real_executable(url: str, expected: ToolchainInfo):
    """Check the toolchain info for a real mongod executable."""
    with tempfile.NamedTemporaryFile() as output_file:
        with urllib.request.urlopen(url) as response:
            with tarfile.open(fileobj=response, mode="r|gz") as tarball:
                while (tarinfo := tarball.next()) is not None:
                    if tarinfo.isfile() and pathlib.Path(tarinfo.path).name == "mongod":
                        shutil.copyfileobj(tarball.extractfile(tarinfo), output_file)
                        output_file.flush()
                        break
                else:
                    pytest.fail("Did not extract a mongod executable from the provided url")

        detector = ToolchainVersionDetector(output_file.name)
        assert detector.detect() == expected
