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
"""Proxy for the gdb.libstdcxx.v6.xmethods submodule.

This module exists so GDB pretty printers defined in the gdbmongo package can refer to
gdbmongo.stdlib_xmethods.XX types without caring around which version of the MongoDB toolchain the
libstdc++ GDB pretty printers were loaded from. The intended usage in GDB pretty printers resembles
the following Python snippet:

.. code-block:: python

    # The `from gdbmongo.stdlib_xmethods import ...` syntax cannot be used because it would attempt
    # to reference an attribute before the gdb.libstdcxx.v6 module has been registered in
    # sys.modules.
    import gdbmongo.stdlib_xmethods

    class MyPrinter:

        def __init__(self, val: gdb.Value, /) -> None:
            self.val = val
            self.cursor = val["_cursor"]

        def to_string(self) -> str:
            xmethod_worker = stdlib_xmethods.UniquePtrMethodsMatcher().match(
                self.cursor.type, "operator*")

            cursor = xmethod_worker(self.cursor)
            ...
"""

import importlib
import types
import typing

import gdbmongo.stdlib_printers_loader


def _resolve_xmethods_submodule() -> types.ModuleType:
    """Import the gdb.libstdcxx.v6.xmethods submodule."""
    return importlib.import_module(".xmethods", package=gdbmongo.stdlib_printers_loader.MODULE_NAME)


def __getattr__(name: str) -> typing.Any:
    return getattr(_resolve_xmethods_submodule(), name)


def __dir__() -> typing.List[str]:
    return dir(_resolve_xmethods_submodule())
