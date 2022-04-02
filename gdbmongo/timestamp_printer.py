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
"""Pretty-printer for the mongo::Timestamp type."""

import ctypes
import dataclasses
import struct

import gdb

from gdbmongo.printer_protocol import SupportsToString


# pylint: disable-next=invalid-name
# pylint: disable-next=too-few-public-methods
class c_uint32(ctypes.c_uint32):
    """Wrapper class for ctypes.c_uint32 to avoid implicit conversion to int."""


@dataclasses.dataclass
class MongoTimestamp(ctypes.Structure):
    """Structure with a memory layout compatible with that of mongo::Timestamp.

    This class is useful for constructing gdb.Value objects of type mongo::Timestamp out of selected
    portions of a buffer read with gdb.Inferior.read_memory(). These synthetic gdb.Values can then
    be formatted by TimestampPrinter like normal.

    .. code-block:: python

        objdata = gdb.selected_inferior().read_memory(self.val["_objdata"], objsize)
        timestamp = MongoTimestamp.unpack_from(objdata)
        yield (f"{i}", timestamp.to_value())
    """

    i: c_uint32
    secs: c_uint32

    @classmethod
    def unpack_from(cls, buffer: memoryview, /) -> "MongoTimestamp":
        """Read an 8-byte Timestamp starting from the beginning of the given buffer."""
        fmt = "<II"
        (inc, seconds) = struct.unpack_from(fmt, buffer)
        return cls(secs=c_uint32(seconds), i=c_uint32(inc))

    def to_value(self) -> gdb.Value:
        """Convert the structure to a gdb.Value of type mongo::Timestamp."""
        typ = gdb.lookup_type("mongo::Timestamp")
        return gdb.Value(memoryview(self), typ)


setattr(MongoTimestamp, "_fields_",
        [(field.name, field.type) for field in dataclasses.fields(MongoTimestamp)])


# pylint: disable-next=too-few-public-methods
class TimestampPrinter(SupportsToString):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::Timestamp."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val
        self.time = val["secs"]
        self.inc = val["i"]

    def to_string(self) -> str:
        return f"Timestamp({self.time}, {self.inc})"


def add_printers(pretty_printer: gdb.printing.RegexpCollectionPrettyPrinter, /) -> None:
    """Add the TimestampPrinter to the pretty printer collection given."""
    pretty_printer.add_printer("mongo::Timestamp", "^mongo::Timestamp$", TimestampPrinter)
