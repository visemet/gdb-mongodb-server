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
"""Register the pretty printers defined by the gdbmongo package with GDB itself."""

import re
import warnings

import gdb
from gdb.printing import RegexpCollectionPrettyPrinter

from gdbmongo import abseil_printers, decorable_printer, lock_manager_printer
from gdbmongo.detect_toolchain import ToolchainVersionDetector
from gdbmongo.stdlib_printers_loader import resolve_import


def _import_libstdcxx_printers(executable, *, register_libstdcxx_printers):
    """Import the version of the libstdc++ GDB pretty printers corresponding to the version of the
    MongoDB toolchain the executable was compiled with. Register the imported module on sys.modules
    and optionally register the pretty printers with GDB itself, if requested.
    """

    detector = ToolchainVersionDetector(executable)
    toolchain_info = detector.detect()

    (module, register_module) = resolve_import(toolchain_info)
    register_module()

    if register_libstdcxx_printers:
        module.register_libstdcxx_printers(gdb.current_objfile())


def register_printers(*, essentials=True, stdlib=False, abseil=False, mongo_extras=False):
    """Register the pretty printers defined by the gdbmongo package with GDB itself.

    The pretty printer collections other than gdbmongo-essentials are defaulted to off to avoid
    conflicting with the pretty printers defined in the mongodb/mongo repository.
    """

    if essentials:
        # It would be weird to not register these pretty printers given the whole purpose of the
        # gdbmongo package, but a user can always choose to disable them explicitly so we may as
        # well offer the option for consistency with the others.
        pretty_printer_essentials = RegexpCollectionPrettyPrinter("gdbmongo-essentials")
        lock_manager_printer.add_printers(pretty_printer_essentials)
        gdb.printing.register_pretty_printer(gdb.current_objfile(), pretty_printer_essentials)

    if abseil:
        pretty_printer_abseil = RegexpCollectionPrettyPrinter("gdbmongo-absl")
        abseil_printers.add_printers(pretty_printer_abseil)
        gdb.printing.register_pretty_printer(gdb.current_objfile(), pretty_printer_abseil)

    if mongo_extras:
        pretty_printer_mongo_extras = RegexpCollectionPrettyPrinter("gdbmongo-mongo-extras")
        decorable_printer.add_printers(pretty_printer_mongo_extras)
        gdb.printing.register_pretty_printer(gdb.current_objfile(), pretty_printer_mongo_extras)

    if (executable := gdb.selected_inferior().progspace.filename) is not None:
        _import_libstdcxx_printers(executable, register_libstdcxx_printers=stdlib)
    else:

        def on_user_at_prompt():
            """Import the libstdc++ GDB pretty printers when either the `attach <pid>` or
            `core-file <pathname>` commands are run in GDB.
            """

            if (executable := gdb.selected_inferior().progspace.filename) is None:
                # The `attach` command would have filled in the filename so we only need to check if
                # a core dump has been loaded with the executable file also being loaded.
                target_info = gdb.execute("info target", to_string=True)
                if re.match(r"^Local core dump file:", target_info):
                    warnings.warn(
                        "Unable to locate the libstdc++ GDB pretty printers without an executable"
                        " file. Try running the `file` command with the path to the executable file"
                        " and reloading the core dump with the `core-file` command")
                return

            # Call disconnect() as soon as we have an executable file because we only want to
            # trigger the import once.
            gdb.events.before_prompt.disconnect(on_user_at_prompt)

            _import_libstdcxx_printers(executable, register_libstdcxx_printers=stdlib)

        gdb.events.before_prompt.connect(on_user_at_prompt)
