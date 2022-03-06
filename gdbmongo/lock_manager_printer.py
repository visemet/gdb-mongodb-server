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
"""Pretty-printers for mongo::LockManager resource locks.

After the pretty printers have been registered in GDB, the LockManager locks in a mongod process or
core file can be displayed with the following commands:

.. code-block:: python

    (gdb) python lock_mgr = gdbmongo.LockManagerPrinter.from_global_service_context()
    (gdb) python print(lock_mgr.val)
"""

import typing

import gdb

from gdbmongo import stdlib_printers
from gdbmongo.abseil_printers import AbslNodeHashMapPrinter
from gdbmongo.decorable_printer import DecorationContainerPrinter


def gdb_lookup_value(symbol_name: str) -> typing.Optional[gdb.Value]:
    """Return the gdb.Value corresponding to the symbol name given."""
    if (symbol := gdb.lookup_symbol(symbol_name)[0]) is not None:
        return symbol.value()

    return None


# pylint: disable-next=too-few-public-methods
class ServiceContextDecorationMixin:
    """Class to add support for constructing from the global ServiceContext if the subclass already
    supports constructing from a ServiceContext explicitly."""

    Decoration = typing.TypeVar("Decoration", bound="ServiceContextDecorationMixin")

    from_service_context: typing.Callable[[typing.Type[Decoration], gdb.Value], Decoration]

    @classmethod
    def from_global_service_context(cls: typing.Type[Decoration]) -> Decoration:
        """Return a Decoration printer from its decoration on the global ServiceContext."""
        service_context = gdb_lookup_value("mongo::(anonymous namespace)::globalServiceContext")
        return cls.from_service_context(service_context)


# We don't have to_string() or children() defined on _CollectionCatalogPrinter right now. Until we
# have a sense of how else we might want to use the CollectionCatalog in GDB pretty printers, it is
# probably best to mark the type as being internal to this module.
class _CollectionCatalogPrinter(ServiceContextDecorationMixin):
    """Pretty-printer for mongo::CollectionCatalog."""

    def __init__(self, val):
        self.resources = val["_resourceInformation"]
        self.val = val

    def lookup_resource_name(self, res_id: gdb.Value) -> typing.Optional[gdb.Value]:
        """Return a gdb.Value containing the database or collection namespace string of the
        resource.
        """

        iterator = stdlib_printers.StdMapPrinter("std::map", self.resources).children()
        for ((_, iter_res_id), (_, iter_nss_set)) in zip(iterator, iterator):
            if iter_res_id == res_id:
                nss_set = iter_nss_set
                break
        else:
            return None

        namespaces = [
            nss for (_, nss) in stdlib_printers.StdSetPrinter("std::set", nss_set).children()
        ]

        return namespaces[0] if len(namespaces) == 1 else None

    # pylint: disable-next=too-few-public-methods
    class _LatestCollectionCatalogDecoration:

        short_name = "LatestCollectionCatalog"

        def __init__(self):
            self.catalog_type = gdb.lookup_type(
                "mongo::(anonymous namespace)::LatestCollectionCatalog")

        def __call__(self, decoration: gdb.Value) -> gdb.Value:
            return stdlib_printers.SharedPointerPrinter(
                "std::shared_ptr", decoration["catalog"]).pointer.dereference()

    # pylint: disable-next=too-few-public-methods
    class _CollectionCatalogDecoration:

        short_name = "CollectionCatalog"

        def __init__(self):
            self.catalog_type = gdb.lookup_type("mongo::CollectionCatalog")

        def __call__(self, decoration: gdb.Value) -> gdb.Value:
            return decoration

    @classmethod
    def from_service_context(cls, service_context):
        """Return a _CollectionCatalogPrinter from its decoration on ServiceContext."""
        try:
            catalog_getter = cls._LatestCollectionCatalogDecoration()
        except gdb.error as err:
            if not err.args[0].startswith("No type named "):
                raise

            # The sole CollectionCatalog instance was previously a direct decoration on the global
            # ServiceContext before becoming a versioned object in SERVER-52556.
            # https://github.com/mongodb/mongo/blob/r4.4.13/src/mongo/db/catalog/collection_catalog.cpp#L47-L48
            catalog_getter = cls._CollectionCatalogDecoration()

        iterator = DecorationContainerPrinter(service_context["_decorations"]).children()
        for (_, decoration) in iterator:
            if decoration.type == catalog_getter.catalog_type:
                catalog = catalog_getter(decoration)
                break
        else:
            raise ValueError(
                f"Failed to locate {catalog_getter.short_name} decoration in ServiceContext")

        return cls(catalog)


class LockManagerPrinter(ServiceContextDecorationMixin):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::LockManager."""

    def __init__(self, val):
        self.buckets = val["_lockBuckets"]
        self.num_buckets = int(val["_numLockBuckets"])
        self.val = val

    @staticmethod
    def display_hint():
        return "map"

    def to_string(self):
        # The LockManagerPrinter.children() method skips over resources which have no locks granted
        # on them to match the behavior of mongo::LockManager::dump(). However, no output when
        # calling `python print(lock_mgr.val)` would be confusing to users so we implement
        # LockManagerPrinter.to_string() to make this situation more obvious. Unfortunately, the
        # LockManager has no higher-level notion of whether a MODE_S or MODE_X lock request is
        # present in the system so we may do the work of walking the lock buckets twice.
        for _ in self.children():
            return "mongo::LockManager dump"

        return "mongo::LockManager dump (no strong locks held or pending)"

    def children(self):
        for i in range(self.num_buckets):
            bucket_data = AbslNodeHashMapPrinter(self.buckets[i]["data"])
            for (res_id, lock_head_ptr) in bucket_data.items():
                lock_head = lock_head_ptr.dereference()
                # We skip displaying anything for resources which have no locks granted on them to
                # match the behavior of mongo::LockManager::dump(). Resources which aren't held by
                # anything thread cannot be involved in a deadlock because there could be any
                # conflicts either.
                if LockRequestListPrinter(lock_head["grantedList"]):
                    yield ("", res_id)
                    yield ("", lock_head)

    @classmethod
    def from_service_context(cls, service_context):
        """Return a LockManagerPrinter from its decoration on ServiceContext."""
        lock_manager_type = gdb.lookup_type("mongo::LockManager")

        iterator = DecorationContainerPrinter(service_context["_decorations"]).children()
        for (_, decoration) in iterator:
            if decoration.type == lock_manager_type:
                lock_manager = decoration
                break
        else:
            raise ValueError("Failed to locate LockManager decoration in ServiceContext")

        return cls(lock_manager)

    @classmethod
    def from_global(cls):
        """Return a LockManagerPrinter from the global LockManager."""
        # The global LockManager was previously its own global before becoming a decoration on the
        # global ServiceContext in SERVER-52516.
        # https://github.com/mongodb/mongo/blob/r5.0.6/src/mongo/db/concurrency/lock_state.cpp#L122
        if (lock_manager :=
                gdb_lookup_value("mongo::(anonymous namespace)::globalLockManager")) is not None:
            return cls(lock_manager)

        return cls.from_global_service_context()


class LockRequestListPrinter:
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::LockRequestList (doubly-linked list)."""

    def __init__(self, val):
        self.val = val

    @staticmethod
    def display_hint():
        return "array"

    def to_string(self):
        return "mongo::LockRequestList" if self else "Empty mongo::LockRequestList"

    def children(self):
        lock_request = self.val["_front"]
        while lock_request != 0:
            yield ("", lock_request.dereference())
            lock_request = lock_request["next"]

    def __bool__(self) -> bool:
        """Return True if the linked list isn't empty, and return False otherwise."""
        return self.val["_front"] != 0


# pylint: disable-next=too-few-public-methods
class ResourceIdPrinter:
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::ResourceId."""

    def __init__(self, val):
        self.val = val
        self.full_hash = int(val["_fullHash"])

        resource_type_bits = int(gdb_lookup_value("mongo::ResourceId::resourceTypeBits"))
        self.resource_type = gdb.Value(self.full_hash >> (64 - resource_type_bits)).cast(
            gdb.lookup_type("mongo::ResourceType"))
        self.hash_id = self.full_hash & ((2**64 - 1) >> resource_type_bits)

    def to_string(self):
        ret = f"{{{self.full_hash}: {self.resource_type}, {self.hash_id}}}"

        if self.resource_type == gdb_lookup_value("mongo::RESOURCE_MUTEX"):
            res_id_factory = gdb_lookup_value(
                "mongo::(anonymous namespace)::ResourceIdFactory::resourceIdFactory")

            iterator = stdlib_printers.StdVectorPrinter("std::vector",
                                                        res_id_factory["labels"]).children()

            # `iterator.item` refers to the front of the array underlying the std::vector initially.
            # We could achieve a similar effect by calling into the VectorAtWorker Xmethod for
            # std::vector, but that would be a bit more effort.
            ret += f", {iterator.item[self.hash_id]}"

        if self.resource_type in (gdb_lookup_value("mongo::RESOURCE_DATABASE"),
                                  gdb_lookup_value("mongo::RESOURCE_COLLECTION")):
            collection_catalog = _CollectionCatalogPrinter.from_global_service_context()
            if (nss := collection_catalog.lookup_resource_name(self.val)) is not None:
                ret += f", {nss}"

        return ret


# pylint: disable-next=too-few-public-methods
class ResourceTypePrinter:
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::ResourceType"""

    # We duplicate the contents of mongo::ResourceTypeNames[] here for a couple reasons:
    #
    #   1. gdb.lookup_symbol("mongo::ResourceTypeNames") would OOM the GDB process when searching
    #      for the symbol in a dynamically-linked mongod executable.
    #
    #   2. While gdb.lookup_static_symbol("mongo::ResourceTypeNames").value() would avoid the memory
    #      pressure, that function is only available starting in the v4 toolchain. Moreover, the
    #      `const char*` values are almost surely to have been optimized out anyway.
    #
    # If we do end up adding a new resource type to the middle of the hierarchy in a later version
    # of the MongoDB Server (e.g. RSTL lock in MongoDB 4.2) then we'll need to come up with some
    # scheme for detecting which set of names to use.
    resource_type_names = (
        "Invalid",
        "ParallelBatchWriterMode",
        "ReplicationStateTransition",
        "Global",
        "Database",
        "Collection",
        "Metadata",
        "Mutex",
    )

    def __init__(self, val):
        self.val = val

    def to_string(self):
        return self.resource_type_names[int(self.val)]


def add_printers(pretty_printer):
    """Add the LockManager related printers to the pretty printer collection given."""
    pretty_printer.add_printer("mongo::LockManager", "^mongo::LockManager$", LockManagerPrinter)
    pretty_printer.add_printer("mongo::LockRequestList", "^mongo::LockRequestList$",
                               LockRequestListPrinter)
    pretty_printer.add_printer("mongo::ResourceType", "^mongo::ResourceType$", ResourceTypePrinter)
    pretty_printer.add_printer("mongo::ResourceId", "^mongo::ResourceId$", ResourceIdPrinter)
