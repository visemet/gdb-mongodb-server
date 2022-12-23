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
"""Test file for the stdlib_printers.py and stdlib_printers_loader.py modules."""

import pathlib
import sys
import typing
import unittest.mock

import pytest

from gdbmongo.detect_toolchain import ToolchainInfo
import gdbmongo.stdlib_printers
from gdbmongo.stdlib_printers_loader import resolve_import


@pytest.fixture
def unload_libstdcxx_printers() -> typing.Generator[None, None, None]:
    """Remove the gdb.libstdcxx.v6 package and its submodules from sys.modules."""
    yield
    sys.modules.pop("gdb.libstdcxx.v6", None)
    sys.modules.pop("gdb.libstdcxx.v6.printers", None)


@pytest.mark.parametrize(("toolchain_info", ), (
    pytest.param(
        ToolchainInfo("GCC: (GNU) 8.5.0",
                      pathlib.Path("/opt/mongodbtoolchain/v3/share/gcc-8.5.0/python")),
        id="v3/gcc-8.5.0"),
    pytest.param(
        ToolchainInfo("GCC: (GNU) 11.2.0",
                      pathlib.Path("/opt/mongodbtoolchain/v4/share/gcc-11.3.0/python")),
        id="v4/gcc-11.2.0"),
))
@pytest.mark.usefixtures("unload_libstdcxx_printers")
@unittest.mock.patch.dict("sys.modules", gdb=unittest.mock.MagicMock())
def test_can_load_module_from_toolchain(toolchain_info: ToolchainInfo) -> None:
    """Check that the gdb.libstdcxx.v6 package can be loaded without error for the corresponding
    version of the MongoDB toolchain.
    """
    (module, _register_module) = resolve_import(toolchain_info)
    assert module.register_libstdcxx_printers is not None


@pytest.mark.usefixtures("unload_libstdcxx_printers")
@unittest.mock.patch.dict("sys.modules", gdb=unittest.mock.MagicMock())
class TestStdlibPrinters:
    """Container for test cases so each runs with mocks and fixtures applied."""

    toolchain_info = ToolchainInfo("GCC: (GNU) 8.5.0",
                                   pathlib.Path("/opt/mongodbtoolchain/v3/share/gcc-8.5.0/python"))

    def test_no_side_effects_from_loading_module(self) -> None:
        """Check that calling resolve_import() won't modify sys.modules automatically."""
        current_modules = frozenset(sys.modules.keys())
        resolve_import(self.toolchain_info)
        assert current_modules == sys.modules.keys()

    def test_can_import_module_after_registering(self) -> None:
        """Check that the gdb.libstdcxx.v6 module is only available to import after the returned
        register_module() function has been called.
        """
        (_module, register_module) = resolve_import(self.toolchain_info)
        assert "gdb.libstdcxx.v6" not in sys.modules
        assert "gdb.libstdcxx.v6.printers" not in sys.modules
        register_module()
        assert "gdb.libstdcxx.v6" in sys.modules
        assert "gdb.libstdcxx.v6.printers" not in sys.modules

    def test_can_reference_printer_after_registering(self) -> None:
        """Check that pretty printer classes are only available to import after the returned
        register_module() function has been called.
        """
        (_module, register_module) = resolve_import(self.toolchain_info)
        with pytest.raises(ModuleNotFoundError, match=r"No module named 'gdb.libstdcxx'"):
            _ = gdbmongo.stdlib_printers.UniquePointerPrinter
        register_module()
        assert gdbmongo.stdlib_printers.UniquePointerPrinter is not None

    def test_can_list_printer_names_after_registering(self) -> None:
        """Check that pretty printer classes are only available to list after the returned
        register_module() function has been called.
        """
        (_module, register_module) = resolve_import(self.toolchain_info)
        with pytest.raises(ModuleNotFoundError, match=r"No module named 'gdb.libstdcxx'"):
            dir(gdbmongo.stdlib_printers)
        register_module()
        assert "UniquePointerPrinter" in dir(gdbmongo.stdlib_printers)
