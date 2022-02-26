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
"""Proxy for the gdb.libstdcxx.v6.printers submodule.

This module exists so GDB pretty printers defined in the gdbmongo package can refer to
gdbmongo.stdlib_printers.XX types without caring around which version of the MongoDB toolchain the
libstdc++ GDB pretty printers were loaded from. The intended usage in GDB pretty printers resembles
the following Python snippet:

.. code-block:: python

    # The `from gdbmongo.stdlib_printers import ...` syntax cannot be used because it would attempt
    # to reference an attribute before the gdb.libstdcxx.v6 module has been registered in
    # sys.modules.
    import gdbmongo.stdlib_printers

    class MyPrinter:

        def __init__(self, val):
            self.val = val
            self.cursor = val["_cursor"]

        def to_string(self):
            # The class is aliased here as a local variable for some brevity.
            UniquePointerPrinter = gdbmongo.stdlib_printers.UniquePointerPrinter
            cursor = UniquePointerPrinter("std::unique_ptr", self.cursor).pointer.dereference()
            ...
"""

import importlib
import types
import typing

import gdbmongo.stdlib_printers_loader


def _resolve_printers_submodule() -> types.ModuleType:
    """Import the gdb.libstdcxx.v6.printers submodule."""
    return importlib.import_module(".printers", package=gdbmongo.stdlib_printers_loader.MODULE_NAME)


def __getattr__(name: str) -> typing.Any:
    return getattr(_resolve_printers_submodule(), name)


def __dir__() -> typing.List[str]:
    return dir(_resolve_printers_submodule())
