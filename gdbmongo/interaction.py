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
import typing
import warnings

import gdb
import gdb.printing

from gdbmongo import (abseil_printers, bsonmisc_printer, bsonobj_printer, date_printer,
                      decorable_printer, lock_manager_printer, objectid_printer, status_printer,
                      string_data_printer, timestamp_printer, uuid_printer)
from gdbmongo.detect_toolchain import ToolchainVersionDetector
from gdbmongo.printer_protocol import SupportsChildren, SupportsToString
from gdbmongo.stdlib_printers_loader import resolve_import


def _import_libstdcxx_printers(executable: str, /, *, register_libstdcxx_printers: bool) -> None:
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


# pylint: disable-next=too-few-public-methods
class RegexpCollectionPrettyPrinter(gdb.printing.RegexpCollectionPrettyPrinter):
    """Pretty-printer collection which supports adding subprinters and recognizing gdb.Types based
    on a regular expression. It avoids constructing an instance of the subprinter when the given
    gdb.Value is optimized out. This enables subprinter classes to access member variables, etc. in
    their __init__() method without worrying about raising a gdb.error as a result.
    """

    def __call__(self, val: gdb.Value, /) -> typing.Union[SupportsToString, SupportsChildren, None]:
        if val.is_optimized_out:
            # Attempting to pretty-print a value which is optimized out will likely result in a
            # Python exception so we don't even bother to try.
            return None

        return super().__call__(val)


def register_printers(*, essentials: bool = True, stdlib: bool = False, abseil: bool = False,
                      mongo_extras: bool = False) -> None:
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
        bsonmisc_printer.add_printers(pretty_printer_mongo_extras)
        bsonobj_printer.add_printers(pretty_printer_mongo_extras)
        date_printer.add_printers(pretty_printer_mongo_extras)
        decorable_printer.add_printers(pretty_printer_mongo_extras)
        objectid_printer.add_printers(pretty_printer_mongo_extras)
        status_printer.add_printers(pretty_printer_mongo_extras)
        string_data_printer.add_printers(pretty_printer_mongo_extras)
        timestamp_printer.add_printers(pretty_printer_mongo_extras)
        uuid_printer.add_printers(pretty_printer_mongo_extras)
        gdb.printing.register_pretty_printer(gdb.current_objfile(), pretty_printer_mongo_extras)

    if (executable := gdb.selected_inferior().progspace.filename) is not None:
        _import_libstdcxx_printers(executable, register_libstdcxx_printers=stdlib)
    else:

        def on_user_at_prompt() -> None:
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
