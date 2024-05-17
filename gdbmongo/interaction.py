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

from gdbmongo import (abseil_printers, aligned_printer, boost_printers, bsonmisc_printer,
                      bsonobj_printer, date_printer, decorable_printer, lock_manager_printer,
                      objectid_printer, static_immortal_printer, status_printer,
                      string_data_printer, thread_name_printer, timestamp_printer, uuid_printer)
from gdbmongo.detect_toolchain import ToolchainVersionDetector
from gdbmongo.gdbutil import gdb_are_debug_symbols_loaded, gdb_is_libthread_db_loaded
from gdbmongo.printer_protocol import SupportsChildren, SupportsToString
from gdbmongo.stdlib_printers_loader import resolve_import

# gdb.current_objfile() would very likely be None at the moment gdbmongo.register_printers() is
# called. There also hasn't been a need to enable or disable specific pretty printers on a
# per-program basis. This is because debugging a core file isn't compatible with debugging multiple
# programs in a single GDB session. We therefore make the global registration of the pretty
# printers which was already happening here explicit.
#
# pylint: disable-next=invalid-name
_register_globally = None


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
        module.register_libstdcxx_printers(_register_globally)


def _set_thread_names(all_threads: typing.Tuple[gdb.InferiorThread, ...], /) -> None:
    """Update the name of each thread as viewed by GDB based on the contents of the
    mongo::(anonymous namespace)::ThreadNameInfo thread-local variable.
    """
    assert all_threads, "No threads. Is a program running? Is a core dump loaded?"

    if not gdb_is_libthread_db_loaded():
        warnings.warn(
            "libthread_db library is not available. Is a core dump being debugged for a platform"
            " different from its host? Output from the `info threads` command will be limited.")
        return

    if not gdb_are_debug_symbols_loaded():
        warnings.warn(
            "Debug symbols are not available. Is the executable file stripped? Unable to assign"
            " thread names from stored thread-local variables.")
        return

    original_thread = gdb.selected_thread()
    original_frame = gdb.selected_frame()

    try:
        for thread in all_threads:
            thread.switch()
            if thread_name := thread_name_printer.get_thread_name():
                thread.name = thread_name
    finally:
        if original_thread.is_valid():
            original_thread.switch()
            if original_frame.is_valid():
                original_frame.select()


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
                      boost: bool = False, mongo_extras: bool = False) -> None:
    """Register the pretty printers defined by the gdbmongo package with GDB itself.

    The pretty printer collections other than gdbmongo-essentials are defaulted to off to avoid
    conflicting with the pretty printers defined in the mongodb/mongo repository.
    """
    # pylint: disable=attribute-defined-outside-init
    # Maybe https://github.com/PyCQA/pylint/issues/4987 would help.
    pretty_printer_essentials = RegexpCollectionPrettyPrinter("gdbmongo-essentials")
    pretty_printer_essentials.enabled = essentials
    lock_manager_printer.add_printers(pretty_printer_essentials)
    gdb.printing.register_pretty_printer(_register_globally, pretty_printer_essentials)

    pretty_printer_abseil = RegexpCollectionPrettyPrinter("gdbmongo-absl")
    pretty_printer_abseil.enabled = abseil
    abseil_printers.add_printers(pretty_printer_abseil)
    gdb.printing.register_pretty_printer(_register_globally, pretty_printer_abseil)

    pretty_printer_boost = RegexpCollectionPrettyPrinter("gdbmongo-boost")
    pretty_printer_boost.enabled = boost
    boost_printers.add_printers(pretty_printer_boost)
    gdb.printing.register_pretty_printer(_register_globally, pretty_printer_boost)

    pretty_printer_mongo_extras = RegexpCollectionPrettyPrinter("gdbmongo-mongo-extras")
    pretty_printer_mongo_extras.enabled = mongo_extras
    aligned_printer.add_printers(pretty_printer_mongo_extras)
    bsonmisc_printer.add_printers(pretty_printer_mongo_extras)
    bsonobj_printer.add_printers(pretty_printer_mongo_extras)
    date_printer.add_printers(pretty_printer_mongo_extras)
    decorable_printer.add_printers(pretty_printer_mongo_extras)
    objectid_printer.add_printers(pretty_printer_mongo_extras)
    static_immortal_printer.add_printers(pretty_printer_mongo_extras)
    status_printer.add_printers(pretty_printer_mongo_extras)
    string_data_printer.add_printers(pretty_printer_mongo_extras)
    timestamp_printer.add_printers(pretty_printer_mongo_extras)
    uuid_printer.add_printers(pretty_printer_mongo_extras)
    gdb.printing.register_pretty_printer(_register_globally, pretty_printer_mongo_extras)

    def initialize_environment(executable: str, /) -> None:
        _import_libstdcxx_printers(executable, register_libstdcxx_printers=stdlib)

        if all_threads := gdb.selected_inferior().threads():
            _set_thread_names(all_threads)

    # pylint: disable-next=dangerous-default-value
    def ensure_disconnected_on_attach_first_stop(cell: list[bool] = [False], /) -> None:
        ([was_called], cell[:]) = (cell, [True])
        if not was_called:
            gdb.events.stop.disconnect(on_attach_first_stop)

    if (executable := gdb.selected_inferior().progspace.filename) is not None:
        initialize_environment(executable)
    else:

        def on_attach_first_stop(event: gdb.StopEvent) -> None:
            """Import the libstdc++ GDB pretty printers following the `attach <pid>` command being
            run in GDB.
            """
            gdb.events.stop.disconnect(on_attach_first_stop)

            # We only intend to handle the stop event when first attaching to a program. Signals and
            # breakpoints also trigger "normal stop" events but they are reported as subclasses of
            # gdb.StopEvent and so we return early for any derived types.
            #
            # pylint: disable-next=unidiomatic-typecheck
            if type(event) is not gdb.StopEvent:
                return

            if (executable := gdb.selected_inferior().progspace.filename) is None:
                return

            # Call disconnect() as soon as we have an executable file because we only want to
            # trigger the import once.
            gdb.events.before_prompt.disconnect(on_user_at_prompt)

            initialize_environment(executable)

        def on_user_at_prompt() -> None:
            """Import the libstdc++ GDB pretty printers after either the `attach <pid>` or
            `core-file <pathname>` commands were run in GDB and control has returned to the user.
            """
            ensure_disconnected_on_attach_first_stop()

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

            initialize_environment(executable)

        gdb.events.stop.connect(on_attach_first_stop)
        gdb.events.before_prompt.connect(on_user_at_prompt)
