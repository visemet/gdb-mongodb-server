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
from gdbmongo.gdbutil import gdb_lookup_value
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
            # LazyString.value() can only be called for non-nullptr strings.
            return ret.value().string(length=ret.length) if ret.address != 0 else ""
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
class MongoStringDataLayoutStdStringView(ctypes.Structure):
    """Structure with a memory layout compatible with that of mongo::StringData.

    It corresponds to the memory layout after mongo::StringData became a thin wrapper over
    std::string_view as part of SERVER-82604 in MongoDB 7.3. It is equivalent to the following
    C struct:

    .. code-block:: c

        struct {
            size_t size;
            char* data;
        };
    """

    size: c_size_t
    data: c_char_p


setattr(MongoStringDataLayoutStdStringView, "_fields_",
        [(field.name, field.type)
         for field in dataclasses.fields(MongoStringDataLayoutStdStringView)])


@dataclasses.dataclass
class MongoStringDataLayoutPre73(ctypes.Structure):
    """Structure with a memory layout compatible with that of mongo::StringData.

    It corresponds to the memory layout prior to mongo::StringData being made a thin wrapper over
    std::string_view as part of SERVER-82604 in MongoDB 7.3. It is equivalent to the following
    C struct:

    .. code-block:: c

        struct {
            char* data;
            size_t size;
        };
    """

    data: c_char_p
    size: c_size_t


setattr(MongoStringDataLayoutPre73, "_fields_",
        [(field.name, field.type) for field in dataclasses.fields(MongoStringDataLayoutPre73)])


class MongoStringData(ctypes.Union):
    """Object with a memory layout compatible with that of mongo::StringData.

    It is implemented as a ctypes.Union to accommodate the memory layout of mongo::StringData
    changing between MongoDB Server versions. It is equivalent to the following C union:

    .. code-block:: c

        union {
            struct {
                size_t size;
                char* data;
            } layout_string_view;

            struct {
                char* data;
                size_t size;
            } layout_pre73;
        };

    This class is useful for constructing gdb.Value objects of type mongo::StringData out of
    selected portions of a buffer read with gdb.Inferior.read_memory(). These synthetic gdb.Values
    can then be formatted by StringDataPrinter like normal.

    .. code-block:: python

        objdata = gdb.selected_inferior().read_memory(self.val["_objdata"], objsize)
        string_data = MongoStringData.from_pascalstring(self.val["_objdata"], view=objdata)
        yield (f"{i}", string_data.to_value())
    """

    layout_string_view: MongoStringDataLayoutStdStringView
    layout_pre73: MongoStringDataLayoutPre73

    # dataclasses.dataclass doesn't appear to be compatible with ctypes.Union. We enumerate
    # `MongoStringData._fields_` explicitly instead of relying on the type annotations.
    _fields_ = [("layout_string_view", MongoStringDataLayoutStdStringView),
                ("layout_pre73", MongoStringDataLayoutPre73)]

    def __init__(self, *, data: int, size: int) -> None:
        if size < 0:
            raise ValueError("size argument must be a non-negative integer")

        if StringDataPrinter.is_wrapping_std_string_view():
            super().__init__(layout_string_view=MongoStringDataLayoutStdStringView(
                data=c_char_p(data), size=c_size_t(size)))
        else:
            super().__init__(
                layout_pre73=MongoStringDataLayoutPre73(data=c_char_p(data), size=c_size_t(size)))

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

    @property
    def data(self) -> c_char_p:
        """Return the pointer to the first character in the string."""
        return (self.layout_string_view.data
                if StringDataPrinter.is_wrapping_std_string_view() else self.layout_pre73.data)

    @property
    def size(self) -> c_size_t:
        """Return the number of characters in the string."""
        return (self.layout_string_view.size
                if StringDataPrinter.is_wrapping_std_string_view() else self.layout_pre73.size)

    def to_value(self) -> gdb.Value:
        """Convert the structure to a gdb.Value of type mongo::StringData."""
        typ = gdb.lookup_type("mongo::StringData")
        return gdb.Value(memoryview(self), typ)


class StringDataPrinter(SupportsDisplayHint, ValueAsPythonStringMixin):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::StringData."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val

    @staticmethod
    def display_hint() -> typing.Literal["string"]:
        return "string"

    def to_string(self) -> typing.Union[gdb.Value, LazyString]:
        if StringDataPrinter.is_wrapping_std_string_view():
            return self.val["_sv"]

        return self.val["_data"].lazy_string(length=int(self.val["_size"]))

    @staticmethod
    def is_wrapping_std_string_view() -> bool:
        # The StringData class was changed to be a thin wrapper over std::string_view as part of
        # SERVER-82604 in MongoDB 7.3.
        return gdb_lookup_value("mongo::StringData::npos") is not None


def add_printers(pretty_printer: gdb.printing.RegexpCollectionPrettyPrinter, /) -> None:
    """Add the StringDataPrinter to the pretty printer collection given."""
    pretty_printer.add_printer("mongo::StringData", "^mongo::StringData$", StringDataPrinter)
