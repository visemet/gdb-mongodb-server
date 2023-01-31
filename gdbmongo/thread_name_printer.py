###
# Copyright 2023-present MongoDB, Inc.
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
"""Pretty-printer for the mongo::(anonymous namespace)::ThreadNameInfo type."""

import typing

import gdb

from gdbmongo import stdlib_printers
from gdbmongo.printer_protocol import SupportsDisplayHint
from gdbmongo.string_data_printer import StdStringPrinter, ValueAsPythonStringMixin


def get_thread_name() -> str:
    """Return the full name associated with the selected thread.

    mongo::(anonymous namespace)::ThreadNameInfo is stored a thread-local variable to record the
    thread's full name for use by MongoDB's logging subsystem and GDB. This data is useful in the
    context of GDB because thread names are otherwise limited to 16 bytes by the Linux kernel.
    Furthermore, core dumps do not record the thread names which were made visible to the kernel.
    mongo::(anonymous namespace)::ThreadNameInfo is therefore the only memory location where the
    thread's name is recorded in a core dump.
    """
    thread_info = gdb.parse_and_eval(
        "&'mongo::(anonymous namespace)::ThreadNameInfo::forThisThread()::tls'").dereference()

    # The 'mongo::(anonymous namespace)::ThreadNameInfo::forThisThread():Tls' struct has a trivial
    # definition and its typeinfo can be elided.
    #
    #   struct Tls {
    #       ThreadNameInfo* info = new ThreadNameInfo;
    #   };
    #
    #   (gdb) print 'mongo::(anonymous namespace)::ThreadNameInfo::forThisThread()::tls'
    #   '[...]ThreadNameInfo::forThisThread()::tls' has unknown type; cast it to its declared type
    #
    # We therefore cast what would be the Tls* to be a ThreadNameInfo* because the Tls::info member
    # variable is guaranteed to be stored at byte offset 0 of the struct.
    thread_info = thread_info.cast(
        gdb.lookup_type("mongo::(anonymous namespace)::ThreadNameInfo").pointer())

    return _ThreadNameInfoPrinter(thread_info).string() if thread_info != 0 else ""


# mongo::(anonymous namespace)::ThreadNameInfo isn't a type which is likely to be printed so we
# don't bother registering it with GDB.
class _ThreadNameInfoPrinter(SupportsDisplayHint, ValueAsPythonStringMixin):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::(anonymous namespace)::ThreadNameInfo."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val

    @staticmethod
    def display_hint() -> typing.Literal["string"]:
        return "string"

    def to_string(self) -> str:
        thread_name = stdlib_printers.SharedPointerPrinter(
            "std::shared_ptr", self.val["_h"]["_ptr"]).pointer.dereference()

        return StdStringPrinter(thread_name).string()
