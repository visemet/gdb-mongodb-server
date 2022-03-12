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
"""Load the module containing the libstdc++ GDB pretty printers."""

import importlib.util
import sys
import types
import typing

import gdbmongo.detect_toolchain

# The module name is somewhat arbitrary because it'll be hidden by accesses through
# gdbmongo.stdlib_printers. But gdb.libstdcxx.v6 at least matches the documentation in
# https://sourceware.org/gdb/onlinedocs/gdb/Writing-a-Pretty_002dPrinter.html.
MODULE_NAME = "gdb.libstdcxx.v6"


def resolve_import(toolchain_info: gdbmongo.detect_toolchain.ToolchainInfo,
                   /) -> typing.Tuple[types.ModuleType, typing.Callable[[], None]]:
    """Load the module containing the libstdc++ GDB pretty printers.

    Returns a pair of the gdb.libstdcxx.v6 module and a 0-argument function to register the module
    in sys.modules so later Python import statements from it can be made. In particular, invoking
    the 0-argument function will NOT have registered the pretty printers with GDB itself. The caller
    must take care to call register_libstdcxx_printers() on the returned module object.
    """
    if (libstdcxx_python_home := toolchain_info.libstdcxx_python_home) is None:
        raise ValueError("Unable to import libstdc++ GDB pretty printers")

    module_location = libstdcxx_python_home.joinpath("libstdcxx", "v6", "__init__.py")
    spec = importlib.util.spec_from_file_location(MODULE_NAME, module_location)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    # Unlike in https://docs.python.org/3.9/library/importlib.html#importing-a-source-file-directly,
    # we aren't adding an entry to sys.modules yet. It is the caller's responsibility to do so and
    # therefore helps centralize all of the registration side effects. The gdb.libstdcxx.v6 package
    # doesn't depend on there being an entry in sys.modules when it is executed anyway.
    assert spec.loader is not None
    spec.loader.exec_module(module)

    def register_module() -> None:
        sys.modules[MODULE_NAME] = module

    return module, register_module
