###
# Copyright 2016-present MongoDB, Inc.
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
"""Pretty-printer for "decorated" types in the MongoDB Server.

This includes MongoDB types like ServiceContext, Client, and OperationContext. Decorated types have
a memory compartment and a registration scheme where other .cpp files can be allocated an offset
into the memory compartment.

For example, after the DecorationContainerPrinter and DecorationBufferPrinter pretty printers have
been registered in GDB, the decorated values on the global ServiceContext can be displayed with the
following command:

.. code-block:: gdb

    print 'mongo::(anonymous namespace)::globalServiceContext'._decorations
"""

import collections.abc
import re
import typing

import gdb

from gdbmongo import stdlib_printers, stdlib_xmethods
from gdbmongo.printer_protocol import PrettyPrinterProtocol


class DecorationMemoryPrinterBase(PrettyPrinterProtocol, collections.abc.Sized):
    # pylint: disable=missing-function-docstring
    """Pretty-printer base class for decorations storage."""

    type_name_regexp = re.compile(r"^(.*[\w>])([\s\*]*)$")

    _cached_decorations_type: typing.ClassVar[typing.Dict[
        str, typing.List[typing.Optional[gdb.Type]]]] = {}
    """Mapping from the decorated type name to the list of types of its decorations."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val

        decorated_type_name = val.type.template_argument(0).tag
        assert decorated_type_name is not None
        # The number of decorations for a particular decorated type is static in a MongoDB program.
        # We preallocate the slots for the gdb.Types at DecorationContainerPrinter construction time
        # to simplying the indexing logic later on.
        self._decorations_type = self._cached_decorations_type.setdefault(
            decorated_type_name, [None] * len(self))

    def to_string(self) -> str:
        return f"{self.val.type.name} with {stdlib_printers.num_elements(len(self))}"

    def children(self) -> typing.Iterator[typing.Tuple[str, gdb.Value]]:
        for (index, (decoration_type, decoration_value)) in enumerate(self._iterate_raw_entries()):
            decoration_type_p = decoration_type.pointer()
            decoration_address = decoration_value.address

            # decoration_value.cast(decoration_type) may not be an addressable object so we get its
            # address and perform the cast through the unsigned char* representation of the value.
            # This ensures decorations which are themselves pointer types are correctly casted.
            yield (f"[{index}] = ({decoration_type_p}) {hex(int(decoration_address))}",
                   decoration_address.cast(decoration_type_p).dereference())

    def _iterate_raw_entries(self) -> typing.Iterator[typing.Tuple[gdb.Type, gdb.Value]]:
        """Return a generator of every decoration in the given mongo::Decorable<T> as pairs of
        (decoration type, decoration value).
        """
        raise NotImplementedError

    @classmethod
    def _cast_decoration_value(cls, type_name: str, decoration_address: int, /) -> gdb.Value:
        """Return the type of the decoration value."""
        # We cannot use gdb.lookup_type() when the decoration type is a pointer type, e.g.
        # ServiceContext::declareDecoration<VectorClock*>(). gdb.parse_and_eval() is one of the few
        # ways to convert a type expression into a gdb.Type value. Some care is taken to quote the
        # non-pointer portion of the type so resolution for a type defined within an anonymous
        # namespace works correctly.
        escaped = cls.type_name_regexp.sub(r"'\1'\2*", type_name)
        try:
            return gdb.parse_and_eval(f"({escaped}) {decoration_address}").dereference()
        except gdb.error as err:
            if not err.args[0].startswith("No symbol "):
                raise

        # The MongoDB C++ driver prior to version 3.10.0 uses `inline namespace v_noabi { ... }` for
        # mongocxx::instance and other types. This can inhibit GDB from resolving type names when
        # the inline namespace appears within a template argument.
        escaped = escaped.replace("bsoncxx::v_noabi::", "bsoncxx::")
        escaped = escaped.replace("mongocxx::v_noabi::", "mongocxx::")

        # libstdc++ uses `inline namespace __cxx11 { ... }` for its std::string definition and other
        # types. This can inhibit GDB from resolving type names when the inline namespace appears
        # within a template argument.
        escaped = escaped.replace("std::__cxx11::", "std::")

        # Functions with C linkage that appear in template parameters may result in mangled names
        # which refer to the address of that function. This can be observed from 'XadL' appearing in
        # the mangled name prior to the function's '_Z' name. The "address of" operator appearing in
        # the type name can inhibit GDB from resolving it. This has been known to impact decoration
        # types like
        #
        #   ServiceContext::declareDecoration<
        #       libmongocrypt_unique_ptr<mongocrypt_t, mongocrypt_destroy>>()
        #
        # needing to be resolved as
        #
        #   std::unique_ptr<
        #       _mongocrypt_t,
        #       mongo::libmongocrypt_support_detail::
        #           LibMongoCryptDeleter<_mongocrypt_t, mongocrypt_destroy>>
        # and not
        #
        #   std::unique_ptr<
        #       _mongocrypt_t,
        #       mongo::libmongocrypt_support_detail::
        #           LibMongoCryptDeleter<_mongocrypt_t, &mongocrypt_destroy>>
        escaped = escaped.replace("&mongocrypt_destroy", "mongocrypt_destroy")

        return gdb.parse_and_eval(f"({escaped}) {decoration_address}").dereference()


class DecorationContainerPrinter(DecorationMemoryPrinterBase):
    """Pretty-printer for mongo::DecorationContainer<DecoratedType>.

    This includes MongoDB types like ServiceContext, Client, and OperationContext.
    """

    symbol_name_regexp = re.compile(r"^(.*) in ")

    def __init__(self, val: gdb.Value, /) -> None:
        decoration_registry = val["_registry"]
        self.decorations_info = decoration_registry["_decorationInfo"]
        self.decorations_storage = val["_decorationData"]

        # len() called by DecorationMemoryPrinterBase.__init__() depends on self.decorations_info
        # being defined first.
        super().__init__(val)

        registry_type = decoration_registry.dereference().type
        self.constructor_regexp = re.compile(
            fr"^void {registry_type.name}::constructAt<\s*(.*)\s*>\(void\*\)$")

    def __len__(self) -> int:
        iterator = stdlib_printers.StdVectorPrinter("std::vector", self.decorations_info).children()
        length = int(iterator.finish - iterator.item)
        return length

    def _iterate_raw_entries(self) -> typing.Iterator[typing.Tuple[gdb.Type, gdb.Value]]:
        xmethod_worker = stdlib_xmethods.UniquePtrMethodsMatcher().match(
            self.decorations_storage.type, "get")

        # UniquePtrGetWorker.__call__(self, obj) is implemented by first calling obj.dereference()
        # on the supplied argument. This behavior for UniquePtrGetWorker was introduced by
        # https://gcc.gnu.org/bugzilla/show_bug.cgi?id=77990 and is therefore present in all
        # versions of the libstdc++ pretty printers for the MongoDB toolchain. We pass in
        # `obj.address` to UniquePtrGetWorker to cancel out the obj.dereference() call.
        decorations_storage = xmethod_worker(self.decorations_storage.address)
        iterator = stdlib_printers.StdVectorPrinter("std::vector", self.decorations_info).children()
        for (index, (_, decoration_info)) in enumerate(iterator):
            storage_offset = int(decoration_info["descriptor"]["_index"])
            decoration_value = decorations_storage[storage_offset]

            assert index < len(self._decorations_type)
            if (decoration_type := self._decorations_type[index]) is None:
                type_name = self._get_decoration_type_name(decoration_info)
                decoration_address = int(decoration_value.address)
                decoration_type = self._cast_decoration_value(type_name, decoration_address).type
                self._decorations_type[index] = decoration_type

            yield (decoration_type, decoration_value)

    def _get_decoration_type_name(self, decoration_info: gdb.Value, /) -> str:
        """Return the name of the decoration type."""
        function = decoration_info["constructor"]
        address = int(function.dereference().address)

        if address == 0:
            # The changes from SERVER-76788 made it possible for the constructor function to be
            # nullptr when the decoration type is trivially constructible. This situation prevents
            # the determination of the actual decoration type. We return `unsigned char` here to
            # reflect the decoration having the existing opaque type of the underlying storage.
            return "unsigned char"

        # We use the `info symbol <address>` command to retrieve the type name for a couple reasons:
        #
        #   1. Unlike gdb.libstdcxx.v6.printers.function_pointer_to_name(), the `info symbol`
        #      command consults the minimal symbol table (aka msymtabs). This enables the command to
        #      prefer certain symbol names over what `gdb.block_for_pc(address).function.name`
        #      naively would have returned in its place. The difference in behavior has been
        #      observed to affect the std::unique_ptr and std::shared_ptr types, both of which are
        #      commonly used as decoration values. Using the `info symbol` command appears to keep
        #      the decoration types more consistent with their source code definitions.
        #
        #   2. While gdb.Type.__str__() also consults the minimal symbol table, its formatting for
        #      the type name may prohibit resolving the underlying decoration type and seemingly
        #      cannot be configured. The result from `str(function)` would omit any default template
        #      arguments. Types such as std::unique_ptr<mongo::AuthorizationManager> must explicitly
        #      include std::default_delete<mongo::AuthorizationManager> as a second template
        #      argument to always be recognized by GDB.
        symbol_info = gdb.execute(f"info symbol {address}", to_string=True).rstrip()
        if (match := self.symbol_name_regexp.match(symbol_info)) is None:
            raise ValueError(
                f"Unable to extract symbol name: {symbol_info}; str() would have returned"
                f" '{str(function)}' and function_pointer_to_name() would have returned"
                f" '{stdlib_printers.function_pointer_to_name(function)}'; perhaps we should"
                " consider adding a fallback mechanism?")

        type_name = match.group(1)
        if (match := self.constructor_regexp.match(type_name)) is None:
            raise ValueError(f"Unable to extract type name from constructor: {type_name}")

        return match.group(1)


class DecorationBufferPrinter(DecorationMemoryPrinterBase):
    """Pretty-printer for mongo::decorable_detail::DecorationBuffer<DecoratedType>.

    This includes MongoDB types like ServiceContext, Client, and OperationContext.
    """

    symbol_name_regexp = re.compile(r"^typeinfo for (.*) in ")

    def __init__(self, val: gdb.Value, /) -> None:
        # The 'mongo::decorable_detail::getRegistry<D>()::reg' function static can have its typeinfo
        # elided.
        #
        #   template <typename D>
        #   Registry& getRegistry() {
        #       static auto reg = [] {
        #           auto r = new Registry{};
        #           return r;
        #       }();
        #       return *reg;
        #   }
        #
        #   (gdb) print 'mongo::decorable_detail::getRegistry<mongo::ServiceContext>()::reg'
        #   'mongo::decorable_detail::getRegistry<mongo::ServiceContext>()::reg' has unknown type;
        #   cast it to its declared type
        #
        # We therefore cast its address to be a mongo::decorable_detail::Registry** to resolve its
        # type manually.
        decorated_type_name = val.type.template_argument(0).tag
        registry_pp = gdb.parse_and_eval(
            f"&'mongo::decorable_detail::getRegistry<{decorated_type_name}>()::reg'")

        registry_type = gdb.lookup_type("mongo::decorable_detail::Registry")
        registry = registry_pp.cast(registry_type.pointer().pointer()).dereference().dereference()
        self.registry = registry
        self.registry_entries = registry["_entries"]

        # len() called by DecorationMemoryPrinterBase.__init__() depends on self.registry_entries
        # being defined first.
        super().__init__(val)

        self.decorations_data = val["_data"]

        try:
            # The mongo::decorable_detail::RegistryEntry class with its private, underscore-prefixed
            # members replaced the mongo::decorable_detail::Registry::Entry struct as part of
            # SERVER-77825 in MongoDB 7.1. The mongo::decorable_detail::Registry::Entry struct had
            # public, non-prefixed members.
            # https://github.com/mongodb/mongo/blob/r7.1.0/src/mongo/util/decorable.h#L445-L446
            #
            # The changes from SERVER-77825 were then reverted under SERVER-81848 in MongoDB 8.0.
            # https://github.com/mongodb/mongo/blob/r8.0.0-rc3/src/mongo/util/decorable.h#L150-L151
            gdb.lookup_type("mongo::decorable_detail::RegistryEntry")
        except gdb.error as err:
            if not err.args[0].startswith("No type named "):
                raise

            self._type_info_field_name = "typeInfo"
            self._offset_field_name = "offset"
        else:
            self._type_info_field_name = "_typeInfo"
            self._offset_field_name = "_offset"

    def __len__(self) -> int:
        iterator = stdlib_printers.StdVectorPrinter("std::vector", self.registry_entries).children()
        length = int(iterator.finish - iterator.item)
        return length

    def _iterate_raw_entries(self) -> typing.Iterator[typing.Tuple[gdb.Type, gdb.Value]]:
        iterator = stdlib_printers.StdVectorPrinter("std::vector", self.registry_entries).children()
        for (index, (_, entry)) in enumerate(iterator):
            data_offset = int(entry[self._offset_field_name])
            decoration_value = self.decorations_data[data_offset]

            assert index < len(self._decorations_type)
            if (decoration_type := self._decorations_type[index]) is None:
                type_name = self._get_decoration_type_name(entry)
                decoration_address = int(decoration_value.address)
                decoration_type = self._cast_decoration_value(type_name, decoration_address).type
                self._decorations_type[index] = decoration_type

            yield (decoration_type, decoration_value)

    def _get_decoration_type_name(self, registry_entry: gdb.Value, /) -> str:
        """Return the name of the decoration type."""
        type_info = registry_entry[self._type_info_field_name]

        # Unlike with DecorationContainerPrinter._get_decoration_type_name(), it isn't strictly
        # necessary to use the `info symbol <address>` command to retrieve the type name. This is
        # because the built in handling for std::type_info* objects in gdb.Type.__str__() won't
        # cause GDB to omit any default template arguments. However, we use the `info symbol`
        # command here for consistency.
        symbol_info = gdb.execute(f"info symbol {int(type_info)}", to_string=True).rstrip()
        if (match := self.symbol_name_regexp.match(symbol_info)) is None:
            raise ValueError(
                f"Unable to extract symbol name: {symbol_info}; str() would have returned"
                f" '{str(type_info)}'; perhaps we should consider adding a fallback mechanism?")

        return match.group(1)


# pylint: disable-next=invalid-name
def DecorationIterator(val: gdb.Value) -> typing.Iterator[gdb.Value]:
    """Return a generator of every decoration in the given mongo::Decorable<T>."""
    try:
        # The memory layout for the Decorable<T> type was changed as part of SERVER-78390.
        # https://github.com/mongodb/mongo/blob/r7.1.0/src/mongo/util/decorable.h#L770
        # https://github.com/mongodb/mongo/blob/r7.0.0/src/mongo/util/decorable.h#L154
        gdb.lookup_type("mongo::decorable_detail::Registry")
    except gdb.error as err:
        if not err.args[0].startswith("No type named "):
            raise

        iterator = DecorationContainerPrinter(val["_decorations"]).children()
    else:
        iterator = DecorationBufferPrinter(val["_decorations"]).children()

    for (_, decoration) in iterator:
        yield decoration


def add_printers(pretty_printer: gdb.printing.RegexpCollectionPrettyPrinter, /) -> None:
    """Add the DecorationContainerPrinter and DecorationBufferPrinter to the pretty printer
    collection given.
    """
    pretty_printer.add_printer("mongo::DecorationContainer", "^mongo::DecorationContainer<.*>$",
                               DecorationContainerPrinter)

    pretty_printer.add_printer("mongo::decorable_detail::DecorationBuffer",
                               "^mongo::decorable_detail::DecorationBuffer<.*>$",
                               DecorationBufferPrinter)
