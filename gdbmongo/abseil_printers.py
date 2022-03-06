###
# Copyright 2018-present MongoDB, Inc.
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
"""Pretty printers for absl:: container types."""

import typing

import gdb

from gdbmongo import stdlib_printers


def gdb_resolve_type(typ: gdb.Type) -> gdb.Type:
    """Look up the name of a C++ type with any typedefs, pointers, and references stripped.

    This function is useful in contexts where template arguments can be pointers because GDB may not
    load the fields of the templated entity otherwise."""

    typ = typ.strip_typedefs()

    while typ.code in (gdb.TYPE_CODE_PTR, gdb.TYPE_CODE_REF):
        typ = typ.target().strip_typedefs()

    typename = typ.tag if typ.tag is not None else typ.name
    return gdb.lookup_type(typename)


# pylint: disable-next=invalid-name
def AbslHashContainerIterator(container):
    """Return a generator of every node in the given absl::container_internal::raw_hash_set or
    derived class.
    """

    capacity = int(container["capacity_"])
    ctrl = container["ctrl_"]
    slots = container["slots_"]

    # We search for any in-use `slots_` among the `ctrl_` bytes and return them.
    # https://github.com/mongodb/mongo/blob/r5.3.0-rc1/src/third_party/abseil-cpp-master/abseil-cpp/absl/container/internal/raw_hash_set.h#L1817-L1820
    # https://github.com/mongodb/mongo/blob/r5.3.0-rc1/src/third_party/abseil-cpp-master/abseil-cpp/absl/container/internal/raw_hash_set.h#L315
    for i in range(capacity):
        is_full = int(ctrl[i]) >= 0
        if is_full:
            yield slots[i]


class AbslHashSetPrinterBase:
    # pylint: disable=missing-function-docstring
    """Pretty-printer base class for absl::node_hash_set<T> and absl::flat_hash_set<T>."""

    template_name: str
    type_aliases: typing.Iterable[str]

    def __init__(self, val):
        self.element_type = val.type.template_argument(0)
        self.size = int(val["size_"])
        self.val = val

        gdb_resolve_type(self.element_type)

    @staticmethod
    def display_hint():
        return "array"

    def to_string(self):
        return (f"{self.template_name}<{self.element_type}> with"
                f" {stdlib_printers.num_elements(self.size)}")

    def children(self):
        count = 0
        for elem in AbslHashContainerIterator(self.val):
            # The first element in the tuple here is technically ignored when the value is printed
            # because we've configured an "array" display hint. Regardless, we use the same
            # convention for it as StdSetPrinter and Tr1UnorderedSetPrinter both do.
            yield (f"[{count}]", self._extract_element(elem))
            count += 1

    def _extract_element(self, elem_val):
        raise NotImplementedError("AbslHashSetPrinterBase._extract_element")


class AbslNodeHashSetPrinter(AbslHashSetPrinterBase):
    """Pretty-printer for absl::node_hash_set<T>."""

    template_name = "absl::node_hash_set"
    type_aliases = ("absl::lts_20210324::node_hash_set", )

    def _extract_element(self, elem_val):
        # https://github.com/mongodb/mongo/blob/r5.3.0-rc1/src/third_party/abseil-cpp-master/abseil-cpp/absl/container/internal/node_hash_policy.h#L75
        return elem_val.dereference()


class AbslFlatHashSetPrinter(AbslHashSetPrinterBase):
    """Pretty-printer for absl::flat_hash_set<T>."""

    template_name = "absl::flat_hash_set"
    type_aliases = ("absl::lts_20210324::flat_hash_set", )

    def _extract_element(self, elem_val):
        # https://github.com/mongodb/mongo/blob/r5.3.0-rc1/src/third_party/abseil-cpp-master/abseil-cpp/absl/container/flat_hash_set.h#L478
        return elem_val


class AbslHashMapPrinterBase:
    # pylint: disable=missing-function-docstring
    """Pretty-printer base class for absl::node_hash_map<K, V> and absl::flat_hash_map<K, V>."""

    template_name: str
    type_aliases: typing.Iterable[str]

    def __init__(self, val):
        self.key_type = val.type.template_argument(0)
        self.value_type = val.type.template_argument(1)
        self.size = int(val["size_"])
        self.val = val

        gdb_resolve_type(self.key_type)
        gdb_resolve_type(self.value_type)

    @staticmethod
    def display_hint():
        return "map"

    def to_string(self):
        return (f"{self.template_name}<{self.key_type}, {self.value_type}> with"
                f" {stdlib_printers.num_elements(self.size)}")

    def children(self):
        for (i, (key, value)) in enumerate(self.items()):
            # The first elements in the tuples here are technically ignored when the value is
            # printed because we've configured a "map" display hint. Regardless, we use the same
            # convention for them as StdMapPrinter and Tr1UnorderedMapPrinter both do.
            yield (f"[{i}]", key)
            yield (f"[{i}]", value)

    def items(self):
        """Return a generator of key-value pairs."""
        for kvp in AbslHashContainerIterator(self.val):
            (key, value) = self._extract_key_value_pair(kvp)
            yield (key, value)

    def _extract_key_value_pair(self, kvp_value):
        raise NotImplementedError("AbslHashMapPrinterBase._extract_key_value_pair")


class AbslNodeHashMapPrinter(AbslHashMapPrinterBase):
    """Pretty-printer for absl::node_hash_map<K, V>."""

    template_name = "absl::node_hash_map"
    type_aliases = ("absl::lts_20210324::node_hash_map", )

    def _extract_key_value_pair(self, kvp_value):
        # https://github.com/mongodb/mongo/blob/r5.3.0-rc1/src/third_party/abseil-cpp-master/abseil-cpp/absl/container/node_hash_map.h#L580
        return (kvp_value["first"], kvp_value["second"])


class AbslFlatHashMapPrinter(AbslHashMapPrinterBase):
    """Pretty-printer for absl::flat_hash_map<K, V>."""

    template_name = "absl::flat_hash_map"
    type_aliases = ("absl::lts_20210324::flat_hash_map", )

    def _extract_key_value_pair(self, kvp_value):
        # https://github.com/mongodb/mongo/blob/r5.3.0-rc1/src/third_party/abseil-cpp-master/abseil-cpp/absl/container/flat_hash_map.h#L586-L588
        return (kvp_value["key"], kvp_value["value"]["second"])


def add_printers(pretty_printer):
    """Add the Abseil printers to the pretty printer collection given."""
    for printer in (AbslNodeHashSetPrinter, AbslFlatHashSetPrinter, AbslNodeHashMapPrinter,
                    AbslFlatHashMapPrinter):
        pretty_printer.add_printer(printer.template_name, f"^{printer.template_name}<.*>$", printer)

        for printer_alias in printer.type_aliases:
            pretty_printer.add_printer(printer_alias, f"^{printer_alias}<.*>$", printer)
