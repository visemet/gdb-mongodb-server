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
"""Pretty-printers for Status-related error types."""

import typing

import gdb

from gdbmongo import stdlib_xmethods
from gdbmongo.printer_protocol import SupportsChildren, SupportsToString


# pylint: disable-next=too-few-public-methods
class ErrorExtraInfoPrinter(SupportsToString):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::ErrorExtraInfo.

    The presence of this pretty printer suppresses the vtbl-related information GDB displays by
    default for base classes with virtual methods.

        <mongo::ErrorExtraInfo> = {
          _vptr.ErrorExtraInfo = 0x7ffff... <vtable for ...>
        },

    The mongo::ErrorExtraInfo base class doesn't have any interesting data members and so the
    virtual table information ends up being noise for the reader.
    """

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val

    def to_string(self) -> str:
        # Returning a string from to_string() is what suppresses the vtbl-related information.
        # Displaying the address of the ErrorExtraInfo is somewhat arbitrary but at least keeps the
        # GDB output more compact.
        return hex(int(self.val.address))


# pylint: disable-next=too-few-public-methods
class ErrorInfoPrinter(SupportsChildren):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::ErrorInfo."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val
        self.code = val["code"]
        self.reason = val["reason"]
        self.extra = val["extra"]

    def children(self) -> typing.Iterator[typing.Tuple[str, gdb.Value]]:
        yield ("code", self.code)
        yield ("reason", self.reason)

        xmethod_worker = stdlib_xmethods.SharedPtrMethodsMatcher().match(self.extra.type, "get")

        if (extra_info_ptr := xmethod_worker(self.extra)) != 0:
            extra_info = extra_info_ptr.dereference()
            # The ErrorExtraInfo object must be cast to the derived type for GDB to actually display
            # its members from the derived type.
            yield ("extra", extra_info.cast(extra_info.dynamic_type))


# pylint: disable-next=too-few-public-methods
class StatusPrinter(SupportsToString):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::Status."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val

        error = val["_error"]
        if error.type.code != gdb.TYPE_CODE_PTR:
            # The type of the `Status::_error` member was changed from ErrorInfo* to
            # boost::intrusive_ptr<ErrorInfo> as part of SERVER-52904 in MongoDB 5.1.
            error = error["px"]

        self.error = error

    def to_string(self) -> typing.Union[str, gdb.Value]:
        if self.error == 0:
            return "Status::OK()"

        # We display the error Status directly as the ErrorInfo object. This keeps the GDB output
        # more compact by omitting the mention of the "_error" field.
        return self.error.dereference()


# pylint: disable-next=too-few-public-methods
class StatusWithPrinter(SupportsToString):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::StatusWith<T>."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val
        self.status = val["_status"]
        self.opt_value = val["_t"]

    def to_string(self) -> gdb.Value:
        status = StatusPrinter(self.status)
        if status.error != 0:
            return self.status

        return self.opt_value


def add_printers(pretty_printer: gdb.printing.RegexpCollectionPrettyPrinter, /) -> None:
    """Add the Status-related printers to the pretty printer collection given."""
    pretty_printer.add_printer("mongo::ErrorExtraInfo", "^mongo::ErrorExtraInfo$",
                               ErrorExtraInfoPrinter)
    pretty_printer.add_printer("mongo::Status::ErrorInfo", "^mongo::Status::ErrorInfo$",
                               ErrorInfoPrinter)
    pretty_printer.add_printer("mongo::Status", "^mongo::Status$", StatusPrinter)
    pretty_printer.add_printer("mongo::StatusWith", "^mongo::StatusWith<.*>$", StatusWithPrinter)
