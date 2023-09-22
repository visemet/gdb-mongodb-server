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
from gdbmongo.decorable_printer import DecorationIterator
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
    try:
        # The ThreadNameInfo type replaced the ThreadNameSconce type for representing the storage
        # for the thread name as part of SERVER-63852 in MongoDB 6.1 and was then subsequently
        # backported to 5.0.12 and 6.0.2. In some versions the ThreadNameInfo instance is managed
        # directly as a thread-local variable, and in other versions it is managed as a decoration
        # within the ThreadContext object.
        thread_info_type = gdb.lookup_type("mongo::(anonymous namespace)::ThreadNameInfo")
    except gdb.error as err:
        if not err.args[0].startswith("No type named "):
            raise

        # Supporting older versions will also need to consider the changes from SERVER-52821.
        return ""

    try:
        # The `tls` thread-local variable was introduced to the ThreadNameInfo::forThisThread()
        # static function as part of SERVER-66385 in MongoDB 6.1. The ThreadNameInfo instance was
        # previously managed as a decoration within the ThreadContext object.
        thread_info_pp = gdb.parse_and_eval(
            "&'mongo::(anonymous namespace)::ThreadNameInfo::forThisThread()::tls'")
    except gdb.error as err:
        if not err.args[0].startswith("No symbol "):
            raise

        if (thread_context := _get_thread_context()) == 0:
            return ""

        for decoration in DecorationIterator(thread_context.dereference()):
            if decoration.type == thread_info_type:
                thread_info = decoration.address
                break
        else:
            raise ValueError(
                "Failed to locate ThreadNameInfo decoration in ThreadContext") from None
    else:
        # The 'mongo::(anonymous namespace)::ThreadNameInfo::forThisThread():Tls' struct has a
        # trivial definition and its typeinfo can be elided.
        #
        #   struct Tls {
        #       ThreadNameInfo* info = new ThreadNameInfo;
        #   };
        #
        #   (gdb) print 'mongo::(anonymous namespace)::ThreadNameInfo::forThisThread()::tls'
        #   'mongo::(anonymous namespace)::ThreadNameInfo::forThisThread()::tls' has unknown type;
        #   cast it to its declared type
        #
        # We therefore cast what would be the Tls* to be a ThreadNameInfo** because the Tls::info
        # member variable is guaranteed to be stored at byte offset 0 of the struct.
        thread_info = thread_info_pp.cast(thread_info_type.pointer().pointer()).dereference()

    return _ThreadNameInfoPrinter(thread_info.dereference()).string() if thread_info != 0 else ""


def _get_thread_context() -> gdb.Value:
    """Return the ThreadContext object associated with the current thread."""
    thread_context_handle_p = gdb.parse_and_eval("&mongo::ThreadContext::_handle")
    thread_context_handle_type = gdb.lookup_type("mongo::ThreadContext::Handle")
    thread_context_handle_p = thread_context_handle_p.cast(thread_context_handle_type.pointer())
    return thread_context_handle_p.dereference()["instance"]["px"]


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
