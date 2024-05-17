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
"""Pretty-printers for absl:: container types."""

import typing

import gdb

from gdbmongo import stdlib_printers
from gdbmongo.gdbutil import gdb_resolve_type
from gdbmongo.printer_protocol import PrettyPrinterProtocol, SupportsDisplayHint


# absl::container_internals::CommonFields isn't a type which is likely to be printed so we don't
# bother registering it with GDB.
#
# pylint: disable-next=too-few-public-methods
class _AbslRawHashSetCommonFieldsPrinter:
    """Pretty-printer for absl::container_internals::CommonFields."""

    def __init__(self, container: gdb.Value, /) -> None:
        try:
            # The code structure for absl::lts_20230802::container_internal::raw_hash_set<T> was
            # changed to have an explicit type for its non-templated members.
            gdb.lookup_type("absl::lts_20230802::container_internal::CommonFields")
        except gdb.error as err:
            if not err.args[0].startswith("No type named "):
                raise

            settings = container
            control = container["ctrl_"]
            size = container["size_"]
            slots = container["slots_"]
        else:
            try:
                common_fields_storage_type = gdb.lookup_type(
                    "absl::lts_20230802::container_internal::internal_compressed_tuple::Storage"
                    "<absl::lts_20230802::container_internal::CommonFields, 0, false>")
            except gdb.error as err:
                if not err.args[0].startswith("No type named "):
                    raise

                # Abseil uses `inline namespace lts_20230802 { ... }` for its container types. This
                # can inhibit GDB from resolving type names when the inline namespace appears within
                # a template argument.
                common_fields_storage_type = gdb.lookup_type(
                    "absl::lts_20230802::container_internal::internal_compressed_tuple::Storage"
                    "<absl::container_internal::CommonFields, 0, false>")

            # The Hash, Eq, or Alloc functors may not be zero-sized objects.
            # mongo::LogicalSessionIdHash is one such example. An explicit cast is needed to
            # disambiguate which `value` member variable of the CompressedTuple is to be accessed.
            settings = container["settings_"].cast(common_fields_storage_type)["value"]
            control = settings["control_"]

            # Sampling is disabled and so HashtablezInfoHandle{} is a zero-sized object. We can
            # therefore treat the entire compressed tuple as the storage for the container's size.
            # https://github.com/mongodb/mongo/blob/r8.0.0-rc3/src/third_party/abseil-cpp/dist/absl/container/internal/raw_hash_set.h#L1049-L1052
            size = settings["compressed_tuple_"]["value"]

            container_type = container.type.strip_typedefs()
            container_typename = (container_type.tag
                                  if container_type.tag is not None else container_type.name)
            assert container_typename is not None
            slot_type = gdb.lookup_type(container_typename + "::slot_type")
            slots = settings["slots_"].cast(slot_type.pointer())

        self.capacity = int(settings["capacity_"])
        self.control = control
        self.size = int(size)
        self.slots = slots


# pylint: disable-next=invalid-name
def AbslHashContainerIterator(settings: _AbslRawHashSetCommonFieldsPrinter,
                              /) -> typing.Iterator[gdb.Value]:
    """Return a generator of every node in the given absl::container_internal::raw_hash_set or
    derived class.
    """
    # We search for any in-use `slots_` among the `ctrl_` bytes and return them.
    # https://github.com/mongodb/mongo/blob/r7.0.0/src/third_party/abseil-cpp/dist/absl/container/internal/raw_hash_set.h#L1948-L1951
    # https://github.com/mongodb/mongo/blob/r7.0.0/src/third_party/abseil-cpp/dist/absl/container/internal/raw_hash_set.h#L330
    for i in range(settings.capacity):
        is_full = int(settings.control[i]) >= 0
        if is_full:
            yield settings.slots[i]


# pylint: disable-next=missing-class-docstring
# pylint: disable-next=too-few-public-methods
class AbslPrinterProtocol(PrettyPrinterProtocol, SupportsDisplayHint, typing.Protocol):

    template_name: typing.ClassVar[str]
    type_aliases: typing.ClassVar[typing.Iterable[str]]


class AbslHashSetPrinterBase(AbslPrinterProtocol):
    # pylint: disable=missing-function-docstring
    """Pretty-printer base class for absl::node_hash_set<T> and absl::flat_hash_set<T>."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.element_type = val.type.template_argument(0)
        self.settings = _AbslRawHashSetCommonFieldsPrinter(val)
        self.val = val

        gdb_resolve_type(self.element_type)

    @staticmethod
    def display_hint() -> typing.Literal["array"]:
        return "array"

    def to_string(self) -> str:
        return (f"{self.template_name}<{self.element_type}> with"
                f" {stdlib_printers.num_elements(self.settings.size)}")

    def children(self) -> typing.Iterator[typing.Tuple[str, gdb.Value]]:
        count = 0
        for elem in AbslHashContainerIterator(self.settings):
            # The first element in the tuple here is technically ignored when the value is printed
            # because we've configured an "array" display hint. Regardless, we use the same
            # convention for it as StdSetPrinter and Tr1UnorderedSetPrinter both do.
            yield (f"[{count}]", self._extract_element(elem))
            count += 1

    def _extract_element(self, elem_val: gdb.Value, /) -> gdb.Value:
        raise NotImplementedError("AbslHashSetPrinterBase._extract_element")


class AbslNodeHashSetPrinter(AbslHashSetPrinterBase):
    """Pretty-printer for absl::node_hash_set<T>."""

    template_name = "absl::node_hash_set"
    type_aliases = ("absl::lts_20210324::node_hash_set", "absl::lts_20211102::node_hash_set",
                    "absl::lts_20230802::node_hash_set")

    def _extract_element(self, elem_val: gdb.Value, /) -> gdb.Value:
        # https://github.com/mongodb/mongo/blob/r7.0.0/src/third_party/abseil-cpp/dist/absl/container/internal/node_hash_policy.h#L75
        return elem_val.dereference()


class AbslFlatHashSetPrinter(AbslHashSetPrinterBase):
    """Pretty-printer for absl::flat_hash_set<T>."""

    template_name = "absl::flat_hash_set"
    type_aliases = ("absl::lts_20210324::flat_hash_set", "absl::lts_20211102::flat_hash_set",
                    "absl::lts_20230802::flat_hash_set")

    def _extract_element(self, elem_val: gdb.Value, /) -> gdb.Value:
        # https://github.com/mongodb/mongo/blob/r7.0.0/src/third_party/abseil-cpp/dist/absl/container/flat_hash_set.h#L478
        return elem_val


class AbslHashMapPrinterBase(AbslPrinterProtocol):
    # pylint: disable=missing-function-docstring
    """Pretty-printer base class for absl::node_hash_map<K, V> and absl::flat_hash_map<K, V>."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.key_type = val.type.template_argument(0)
        self.value_type = val.type.template_argument(1)
        self.settings = _AbslRawHashSetCommonFieldsPrinter(val)
        self.val = val

        gdb_resolve_type(self.key_type)
        gdb_resolve_type(self.value_type)

    @staticmethod
    def display_hint() -> typing.Literal["map"]:
        return "map"

    def to_string(self) -> str:
        return (f"{self.template_name}<{self.key_type}, {self.value_type}> with"
                f" {stdlib_printers.num_elements(self.settings.size)}")

    def children(self) -> typing.Iterator[typing.Tuple[str, gdb.Value]]:
        for (i, (key, value)) in enumerate(self.items()):
            # The first elements in the tuples here are technically ignored when the value is
            # printed because we've configured a "map" display hint. Regardless, we use the same
            # convention for them as StdMapPrinter and Tr1UnorderedMapPrinter both do.
            yield (f"[{i}]", key)
            yield (f"[{i}]", value)

    def items(self) -> typing.Iterator[typing.Tuple[gdb.Value, gdb.Value]]:
        """Return a generator of key-value pairs."""
        for kvp in AbslHashContainerIterator(self.settings):
            (key, value) = self._extract_key_value_pair(kvp)
            yield (key, value)

    def _extract_key_value_pair(self, kvp_value: gdb.Value,
                                /) -> typing.Tuple[gdb.Value, gdb.Value]:
        raise NotImplementedError("AbslHashMapPrinterBase._extract_key_value_pair")


class AbslNodeHashMapPrinter(AbslHashMapPrinterBase):
    """Pretty-printer for absl::node_hash_map<K, V>."""

    template_name = "absl::node_hash_map"
    type_aliases = ("absl::lts_20210324::node_hash_map", "absl::lts_20211102::node_hash_map",
                    "absl::lts_20230802::node_hash_map")

    def _extract_key_value_pair(self, kvp_value: gdb.Value,
                                /) -> typing.Tuple[gdb.Value, gdb.Value]:
        # https://github.com/mongodb/mongo/blob/r7.0.0/src/third_party/abseil-cpp/dist/absl/container/node_hash_map.h#L580
        return (kvp_value["first"], kvp_value["second"])


class AbslFlatHashMapPrinter(AbslHashMapPrinterBase):
    """Pretty-printer for absl::flat_hash_map<K, V>."""

    template_name = "absl::flat_hash_map"
    type_aliases = ("absl::lts_20210324::flat_hash_map", "absl::lts_20211102::flat_hash_map",
                    "absl::lts_20230802::flat_hash_map")

    def _extract_key_value_pair(self, kvp_value: gdb.Value,
                                /) -> typing.Tuple[gdb.Value, gdb.Value]:
        # https://github.com/mongodb/mongo/blob/r7.0.0/src/third_party/abseil-cpp/dist/absl/container/flat_hash_map.h#L586-L588
        return (kvp_value["key"], kvp_value["value"]["second"])


def add_printers(pretty_printer: gdb.printing.RegexpCollectionPrettyPrinter, /) -> None:
    """Add the Abseil printers to the pretty printer collection given."""
    for printer in (AbslNodeHashSetPrinter, AbslFlatHashSetPrinter, AbslNodeHashMapPrinter,
                    AbslFlatHashMapPrinter):
        pretty_printer.add_printer(printer.template_name, f"^{printer.template_name}<.*>$", printer)

        for printer_alias in printer.type_aliases:
            pretty_printer.add_printer(printer_alias, f"^{printer_alias}<.*>$", printer)
