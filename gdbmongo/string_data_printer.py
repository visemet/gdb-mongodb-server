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
"""Pretty-printers for string-related data types."""

import abc
import ctypes
import dataclasses
import struct
import typing

import gdb

from gdbmongo import stdlib_printers
from gdbmongo.printer_protocol import LazyString, SupportsDisplayHint, SupportsToString


class ValueAsPythonStringMixin(SupportsToString):
    # pylint: disable=missing-function-docstring
    """Class to add support for converting a gdb.Value into a Python string from the to_string()
    method of the subclass.

    This class is really only appropriate to use on types which represent string data. One clue can
    be the display_hint() method of the subclass returns "string".
    """

    @abc.abstractmethod
    def to_string(self) -> typing.Union[str, gdb.Value, LazyString, None]:
        raise NotImplementedError

    def string(self) -> str:
        """Return the value as a Python string."""
        ret = self.to_string()
        assert ret is not None

        if isinstance(ret, gdb.Value):
            return ret.string()
        if isinstance(ret, LazyString):
            return ret.value().string(length=ret.length)
        return ret


class StdStringPrinter(SupportsDisplayHint, ValueAsPythonStringMixin):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for std::string.

    This class wraps a gdb.libstdcxx.v6.printers.StdStringPrinter instance to support extracting the
    gdb.Value as a Python string. gdb.Value.__str__() returns a Python string according to how the
    value would be **printed** by GDB. It causes the value to be awkwardly double-quoted and
    possibly truncated due to the user's `set print elements` setting. This class avoids both of
    these issues by instead calling gdb.Value.string().
    """

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val

        typ = val.type.strip_typedefs()
        typename = typ.tag if typ.tag is not None else typ.name
        assert typename is not None
        self.printer = stdlib_printers.StdStringPrinter(typename, val)

    @staticmethod
    def display_hint() -> typing.Literal["string"]:
        return "string"

    def to_string(self) -> typing.Union[str, gdb.Value, LazyString, None]:
        return self.printer.to_string()


# pylint: disable-next=invalid-name
# pylint: disable-next=too-few-public-methods
class c_char_p(ctypes.c_char_p):
    """Wrapper class for ctypes.c_char_p to avoid implicit conversion to bytes."""


# pylint: disable-next=invalid-name
# pylint: disable-next=too-few-public-methods
class c_size_t(ctypes.c_size_t):
    """Wrapper class for ctypes.c_size_t to avoid implicit conversion to int."""


@dataclasses.dataclass
class MongoStringData(ctypes.Structure):
    """Structure with a memory layout compatible with that of mongo::StringData.

    This class is useful for constructing gdb.Value objects of type mongo::StringData out of
    selected portions of a buffer read with gdb.Inferior.read_memory(). These synthetic gdb.Values
    can then be formatted by StringDataPrinter like normal.

    .. code-block:: python

        objdata = gdb.selected_inferior().read_memory(self.val["_objdata"], objsize)
        string_data = MongoStringData.from_pascalstring(self.val["_objdata"], view=objdata)
        yield (f"{i}", string_data.to_value())
    """

    data: c_char_p
    size: c_size_t

    def __init__(self, *, data: int, size: int) -> None:
        if size < 0:
            raise ValueError("size argument must be a non-negative integer")

        super().__init__(data=c_char_p(data), size=c_size_t(size))

    @classmethod
    def from_cstring(cls, val: gdb.Value, /, *, maxsize: int) -> "MongoStringData":
        """Read a null-terminated string starting from the beginning of the given buffer."""
        start = int(val)
        size = maxsize

        if (end := gdb.selected_inferior().search_memory(start, maxsize, b"\x00")) is not None:
            size = end - start

        return cls(data=start, size=size)

    @classmethod
    def from_pascalstring(cls, val: gdb.Value, /, *, view: memoryview) -> "MongoStringData":
        """Read a length-prefixed string starting from the beginning of the given buffer."""
        fmt = "<i"
        (size, ) = struct.unpack_from(fmt, view)
        return cls(data=int(val + struct.calcsize(fmt)), size=size)

    def to_value(self) -> gdb.Value:
        """Convert the structure to a gdb.Value of type mongo::StringData."""
        typ = gdb.lookup_type("mongo::StringData")
        return gdb.Value(memoryview(self), typ)


setattr(MongoStringData, "_fields_",
        [(field.name, field.type) for field in dataclasses.fields(MongoStringData)])


class StringDataPrinter(SupportsDisplayHint, ValueAsPythonStringMixin):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::StringData."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val
        self.size = val["_size"]
        self.data = val["_data"]

    @staticmethod
    def display_hint() -> typing.Literal["string"]:
        return "string"

    def to_string(self) -> LazyString:
        return self.data.lazy_string(length=int(self.size))


def add_printers(pretty_printer: gdb.printing.RegexpCollectionPrettyPrinter, /) -> None:
    """Add the StringDataPrinter to the pretty printer collection given."""
    pretty_printer.add_printer("mongo::StringData", "^mongo::StringData$", StringDataPrinter)
