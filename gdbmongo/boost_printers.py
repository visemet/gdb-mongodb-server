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
"""Pretty-printers for boost:: types."""

import abc
import typing

import gdb

from gdbmongo.gdbutil import gdb_resolve_type
from gdbmongo.printer_protocol import PrettyPrinterProtocol, SupportsChildren, SupportsDisplayHint


class SingletonPrinterBase(SupportsChildren, SupportsDisplayHint):
    # pylint: disable=missing-function-docstring
    """Class to define conventions for displaying a container of a single value."""

    @staticmethod
    def display_hint() -> typing.Literal["array"]:
        return "array"

    def children(self) -> typing.Iterator[typing.Tuple[str, gdb.Value]]:
        # Ideally we would have returned `contained_value` in the to_string() method and skipped
        # defining a children() method at all. But that approach causes GDB to not display the
        # addresses for Xmethods like get() on std::unique_ptr and std::shared_ptr types for any
        # members within `contained_value`. We display the contained value as if it was an array of
        # size 1 to keep the GDB output more compact as a compromise.
        contained_value = self.value()
        yield ("", contained_value)

    @abc.abstractmethod
    def value(self) -> gdb.Value:
        """Return the contained value."""
        raise NotImplementedError


class BoostOptionalPrinter(PrettyPrinterProtocol, SingletonPrinterBase):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for boost::optional<T>."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.element_type = val.type.template_argument(0)
        self.is_initialized = bool(val["m_initialized"])
        self.val = val

        gdb_resolve_type(self.element_type)

    def to_string(self) -> str:
        if self.is_initialized:
            return f"boost::optional<{self.element_type}>"

        return "boost::none"

    def children(self) -> typing.Iterator[typing.Tuple[str, gdb.Value]]:
        if self.is_initialized:
            yield from SingletonPrinterBase.children(self)

    def value(self) -> gdb.Value:
        if not self.is_initialized:
            raise ValueError("Cannot extract value from boost::none")

        storage = self.val["m_storage"]
        # boost::optional<T> is either stored using boost::optional_detail::aligned_storage<T> or
        # using direct storage of `T`. Scalar types are able to take advantage of direct storage.
        #
        # https://www.boost.org/doc/libs/1_79_0/libs/optional/doc/html/boost_optional/tutorial/performance_considerations.html
        if storage.type.strip_typedefs().code == gdb.TYPE_CODE_STRUCT:
            storage = storage["dummy_"]["data"]
            contained_value = storage.cast(self.element_type.pointer()).dereference()
        else:
            contained_value = storage

        return contained_value


def add_printers(pretty_printer: gdb.printing.RegexpCollectionPrettyPrinter, /) -> None:
    """Add the Boost printers to the pretty printer collection given."""
    pretty_printer.add_printer("boost::optional", "^boost::optional<.*>$", BoostOptionalPrinter)
