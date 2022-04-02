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
"""Pretty-printer for the mongo::Date_t type."""

import ctypes
import datetime
import dataclasses
import struct
import typing

import gdb

from gdbmongo.printer_protocol import PrettyPrinterProtocol


# pylint: disable-next=invalid-name
# pylint: disable-next=too-few-public-methods
class c_int64(ctypes.c_int64):
    """Wrapper class for ctypes.c_int64 to avoid implicit conversion to int."""


@dataclasses.dataclass
class MongoDateT(ctypes.Structure):
    """Structure with a memory layout compatible with that of mongo::Date_t.

    This class is useful for constructing gdb.Value objects of type mongo::Date_t out of selected
    portions of a buffer read with gdb.Inferior.read_memory(). These synthetic gdb.Values can then
    be formatted by DatePrinter like normal.

    .. code-block:: python

        objdata = gdb.selected_inferior().read_memory(self.val["_objdata"], objsize)
        date_t = MongoDateT.unpack_from(objdata)
        yield (f"{i}", date_t.to_value())
    """

    millis: c_int64

    @classmethod
    def unpack_from(cls, buffer: memoryview, /) -> "MongoDateT":
        """Read an 8-byte date starting from the beginning of the given buffer."""
        fmt = "<q"
        (millis, ) = struct.unpack_from(fmt, buffer)
        return cls(millis=c_int64(millis))

    def to_value(self) -> gdb.Value:
        """Convert the structure to a gdb.Value of type mongo::Date_t."""
        typ = gdb.lookup_type("mongo::Date_t")
        return gdb.Value(memoryview(self), typ)


setattr(MongoDateT, "_fields_",
        [(field.name, field.type) for field in dataclasses.fields(MongoDateT)])


class DatePrinter(PrettyPrinterProtocol):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::Date_t."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val
        self.millis = int(val["millis"])
        self.formattable = (0 <= self.millis < 32535215999000)  # "3000-12-31T23:59:59Z"

    def to_string(self) -> typing.Optional[str]:
        if not self.formattable:
            return None

        (seconds, millis) = divmod(self.millis, 1000)
        date_t = datetime.datetime.fromtimestamp(
            seconds, tz=datetime.timezone.utc).replace(microsecond=millis * 1000)

        return date_t.isoformat(timespec="milliseconds")

    def children(self) -> typing.Iterator[typing.Tuple[str, gdb.Value]]:
        if self.formattable:
            return

        yield ("millis", gdb.Value(self.millis))


def add_printers(pretty_printer: gdb.printing.RegexpCollectionPrettyPrinter, /) -> None:
    """Add the DatePrinter to the pretty printer collection given."""
    pretty_printer.add_printer("mongo::Date_t", "^mongo::Date_t$", DatePrinter)
