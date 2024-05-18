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

import abc
import struct
import typing

import gdb

from gdbmongo import stdlib_printers, stdlib_xmethods
from gdbmongo.abseil_printers import (AbslFlatHashMapPrinter, AbslNodeHashMapPrinter,
                                      AbslFlatHashSetPrinter, AbslNodeHashSetPrinter)
from gdbmongo.decorable_printer import DecorationIterator
from gdbmongo.gdbutil import gdb_is_libthread_db_loaded, gdb_lookup_value
from gdbmongo.printer_protocol import (PrettyPrinterProtocol, SupportsChildren, SupportsDisplayHint,
                                       SupportsToString)
from gdbmongo.static_immortal_printer import StaticImmortalPrinter
from gdbmongo.string_data_printer import StdStringPrinter


class ServiceContextDecorationMixin(typing.Protocol):
    """Class to add support for constructing from the global ServiceContext if the subclass already
    supports constructing from a ServiceContext explicitly.
    """

    Decoration = typing.TypeVar("Decoration", bound="ServiceContextDecorationMixin")

    @classmethod
    @abc.abstractmethod
    def from_service_context(cls: typing.Type[Decoration], service_context: gdb.Value,
                             /) -> Decoration:
        """Return a Decoration from its decoration on ServiceContext."""
        raise NotImplementedError

    @classmethod
    def from_global_service_context(cls: typing.Type[Decoration]) -> Decoration:
        """Return a Decoration printer from its decoration on the global ServiceContext."""
        service_context = gdb_lookup_value("mongo::(anonymous namespace)::globalServiceContext")
        assert service_context is not None
        return cls.from_service_context(service_context)


# pylint: disable-next=missing-class-docstring
# pylint: disable-next=too-few-public-methods
class ResourceCatalogGetter(typing.Protocol):

    @abc.abstractmethod
    def lookup_resource_name(self, res_id: gdb.Value, /) -> typing.Optional[str]:
        """Return the database or collection namespace string of the resource."""
        raise NotImplementedError


# pylint: disable-next=missing-class-docstring
# pylint: disable-next=too-few-public-methods
class CollectionCatalogGetter(typing.Protocol):

    short_name: typing.ClassVar[str]
    catalog_type: gdb.Type

    @abc.abstractmethod
    def __call__(self, decoration: gdb.Value, /) -> gdb.Value:
        raise NotImplementedError


# We don't have to_string() or children() defined on _CollectionCatalogPrinter right now. Until we
# have a sense of how else we might want to use the CollectionCatalog in GDB pretty printers, it is
# probably best to mark the type as being internal to this module.
class _CollectionCatalogPrinter(ServiceContextDecorationMixin, ResourceCatalogGetter):
    """Pretty-printer for mongo::CollectionCatalog."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.resources = val["_resourceInformation"]
        self.val = val

    def lookup_resource_name(self, res_id: gdb.Value, /) -> typing.Optional[str]:
        """Return the database or collection namespace string of the resource."""
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

        return StdStringPrinter(namespaces[0]).string() if len(namespaces) == 1 else None

    # pylint: disable-next=too-few-public-methods
    class _LatestCollectionCatalogDecoration(CollectionCatalogGetter):

        short_name = "LatestCollectionCatalog"

        def __init__(self) -> None:
            self.catalog_type = gdb.lookup_type(
                "mongo::(anonymous namespace)::LatestCollectionCatalog")

        def __call__(self, decoration: gdb.Value, /) -> gdb.Value:
            return stdlib_printers.SharedPointerPrinter(
                "std::shared_ptr", decoration["catalog"]).pointer.dereference()

    # pylint: disable-next=too-few-public-methods
    class _CollectionCatalogDecoration(CollectionCatalogGetter):

        short_name = "CollectionCatalog"

        def __init__(self) -> None:
            self.catalog_type = gdb.lookup_type("mongo::CollectionCatalog")

        def __call__(self, decoration: gdb.Value, /) -> gdb.Value:
            return decoration

    @classmethod
    def from_service_context(cls, service_context: gdb.Value, /) -> "_CollectionCatalogPrinter":
        """Return a _CollectionCatalogPrinter from its decoration on ServiceContext."""
        catalog_getter: CollectionCatalogGetter

        try:
            catalog_getter = cls._LatestCollectionCatalogDecoration()
        except gdb.error as err:
            if not err.args[0].startswith("No type named "):
                raise

            # The sole CollectionCatalog instance was previously a direct decoration on the global
            # ServiceContext before becoming a versioned object in SERVER-52556.
            # https://github.com/mongodb/mongo/blob/r4.4.13/src/mongo/db/catalog/collection_catalog.cpp#L47-L48
            catalog_getter = cls._CollectionCatalogDecoration()

        for decoration in DecorationIterator(service_context):
            if decoration.type == catalog_getter.catalog_type:
                catalog = catalog_getter(decoration)
                break
        else:
            raise ValueError(
                f"Failed to locate {catalog_getter.short_name} decoration in ServiceContext")

        return cls(catalog)


# pylint: disable-next=too-few-public-methods
class ResourceIdFactoryGetter(typing.Protocol):

    @abc.abstractmethod
    def lookup_resource_mutex_label(self, res_id: gdb.Value, /) -> str:
        """Return the name of the mutex."""
        raise NotImplementedError

    @classmethod
    def _lookup_resource_mutex_label_from(cls, res_id: gdb.Value, /, *,
                                          all_labels: gdb.Value) -> str:
        """Return the name of the mutex from the specified vector of resource labels."""
        xmethod_worker = stdlib_xmethods.VectorMethodsMatcher().match(all_labels.type, "at")
        label = StdStringPrinter(xmethod_worker(all_labels, res_id)).string()
        return label


# We don't have to_string() or children() defined on _ResourceCatalogPrinter right now. Until we
# have a sense of how else we might want to use the ResourceCatalog in GDB pretty printers, it is
# probably best to mark the type as being internal to this module.
class _ResourceCatalogPrinter(ServiceContextDecorationMixin, ResourceCatalogGetter,
                              ResourceIdFactoryGetter):
    """Pretty-printer for mongo::ResourceCatalog."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.resources = val["_resources"]
        self.val = val

    def lookup_resource_name(self, res_id: gdb.Value, /) -> typing.Optional[str]:
        """Return the database or collection namespace string of the resource."""
        for (iter_res_id, iter_nss_set) in AbslNodeHashMapPrinter(self.resources).items():
            if iter_res_id == res_id:
                nss_set = iter_nss_set
                break
        else:
            return None

        namespaces = [nss for (_, nss) in AbslFlatHashSetPrinter(nss_set).children()]
        return StdStringPrinter(namespaces[0]).string() if len(namespaces) == 1 else None

    @property
    def resource_mutex_labels(self) -> gdb.Value:
        """Get the vector of resource mutex labels."""
        # The ResourceCatalog::_mutexResourceIdLabels member was added as part of SERVER-77227.
        # https://github.com/mongodb/mongo/blob/r7.1.0/src/mongo/db/concurrency/resource_catalog.h#L81
        # We expose the instance attribute lazily here rather than defining it in __init__() because
        # the member won't always exist.
        return self.val["_mutexResourceIdLabels"]

    def lookup_resource_mutex_label(self, res_id: gdb.Value, /) -> str:
        return self._lookup_resource_mutex_label_from(res_id, all_labels=self.resource_mutex_labels)

    @classmethod
    def from_service_context(cls, service_context: gdb.Value, /) -> "_ResourceCatalogPrinter":
        """Return a _ResourceCatalogPrinter from its decoration on ServiceContext."""
        try:
            # The ResourceCatalog type was introduced and added as a decoration on the
            # ServiceContext type as part of SERVER-67383 in MongoDB 6.2. Previously in MongoDB 6.0,
            # the mapping of ResourceIds to collection and database names was managed through the
            # CollectionCatalog.
            resource_catalog_type = gdb.lookup_type("mongo::ResourceCatalog")
        except gdb.error as err:
            if not err.args[0].startswith("No type named "):
                raise

            raise ValueError(err.args[0]) from err

        for decoration in DecorationIterator(service_context):
            if decoration.type == resource_catalog_type:
                return cls(decoration)

        raise ValueError("Failed to locate ResourceCatalog decoration in ServiceContext")

    @classmethod
    def from_global(cls) -> "_ResourceCatalogPrinter":
        """Return a _ResourceCatalogPrinter from the function static ResourceCatalog."""
        # The global ResourceCatalog was previously a decoration on the global ServiceContext before
        # becoming a function static in SERVER-77227.
        # https://github.com/mongodb/mongo/blob/r7.1.0/src/mongo/db/concurrency/resource_catalog.cpp#L52
        if (resource_catalog :=
                gdb_lookup_value("mongo::ResourceCatalog::get()::resourceCatalog")) is not None:
            return cls(StaticImmortalPrinter(resource_catalog).value())

        return cls.from_global_service_context()


# We don't have to_string() or children() defined on _DatabaseShardingStateMapPrinter right now.
# Until we have a sense of how else we might want to use the DatabaseShardingStateMap in GDB pretty
# printers, it is probably best to mark the type as being internal to this module.
class _DatabaseShardingStateMapPrinter(ServiceContextDecorationMixin):
    """Pretty-printer for mongo::DatabaseShardingStateMap."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.databases = val["_databases"]
        self.val = val

    def lookup_database_name(self, res_id: gdb.Value, /) -> typing.Optional[str]:
        """Return the database name of the resource."""
        for (_, dss) in AbslFlatHashMapPrinter(self.databases).items():
            dss = stdlib_printers.SharedPointerPrinter("std::shared_ptr", dss).pointer.dereference()
            if dss["_stateChangeMutex"]["_rid"] == res_id:
                return StdStringPrinter(dss["_dbName"]).string()

        return None

    @classmethod
    def from_service_context(cls, service_context: gdb.Value,
                             /) -> "_DatabaseShardingStateMapPrinter":
        """Return a _DatabaseShardingStateMapPrinter from its decoration on ServiceContext."""
        try:
            # The DatabaseShardingStateMap type was introduced and added as a decoration on the
            # ServiceContext type as part of SERVER-34431 in MongoDB 4.4. Previously in MongoDB 4.2,
            # DatabaseShardingState was a decoration on each Database instance.
            databases_type = gdb.lookup_type(
                "mongo::(anonymous namespace)::DatabaseShardingStateMap")
        except gdb.error as err:
            if not err.args[0].startswith("No type named "):
                raise

            raise ValueError(err.args[0]) from err

        for decoration in DecorationIterator(service_context):
            if decoration.type == databases_type:
                return cls(decoration)

        raise ValueError("Failed to locate DatabaseShardingStateMap decoration in ServiceContext")


class LockManagerPrinter(PrettyPrinterProtocol, SupportsDisplayHint, ServiceContextDecorationMixin):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::LockManager."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.buckets = val["_lockBuckets"]
        self.val = val

        # Static member variables are not always accessible within GDB from the instance value
        # itself. We look up the fully qualified symbol rather than writing `val["_numLockBuckets"]`
        # here to work around this limitation.
        num_buckets = gdb_lookup_value("mongo::LockManager::_numLockBuckets")
        assert num_buckets is not None
        self.num_buckets = int(num_buckets)

    @staticmethod
    def display_hint() -> typing.Literal["map"]:
        return "map"

    def to_string(self) -> str:
        # The LockManagerPrinter.children() method skips over resources which have no locks granted
        # on them to match the behavior of mongo::LockManager::dump(). However, no output when
        # calling `python print(lock_mgr.val)` would be confusing to users so we implement
        # LockManagerPrinter.to_string() to make this situation more obvious. Unfortunately, the
        # LockManager has no higher-level notion of whether a MODE_S or MODE_X lock request is
        # present in the system so we may do the work of walking the lock buckets twice.
        for _ in self.children():
            return "mongo::LockManager dump"

        return "mongo::LockManager dump (no strong locks held or pending)"

    def children(self) -> typing.Iterator[typing.Tuple[str, gdb.Value]]:
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
    def from_service_context(cls, service_context: gdb.Value, /) -> "LockManagerPrinter":
        """Return a LockManagerPrinter from its decoration on ServiceContext."""
        lock_manager_type = gdb.lookup_type("mongo::LockManager")

        for decoration in DecorationIterator(service_context):
            if decoration.type == lock_manager_type:
                lock_manager = decoration
                break
        else:
            raise ValueError("Failed to locate LockManager decoration in ServiceContext")

        return cls(lock_manager)

    @classmethod
    def from_global(cls) -> "LockManagerPrinter":
        """Return a LockManagerPrinter from the global LockManager."""
        # The global LockManager was previously its own global before becoming a decoration on the
        # global ServiceContext in SERVER-52516.
        # https://github.com/mongodb/mongo/blob/r5.0.6/src/mongo/db/concurrency/lock_state.cpp#L122
        if (lock_manager :=
                gdb_lookup_value("mongo::(anonymous namespace)::globalLockManager")) is not None:
            return cls(lock_manager)

        return cls.from_global_service_context()


class LockRequestListPrinter(PrettyPrinterProtocol, SupportsDisplayHint):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::LockRequestList (doubly-linked list)."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val

    @staticmethod
    def display_hint() -> typing.Literal["array"]:
        return "array"

    def to_string(self) -> str:
        return "mongo::LockRequestList" if self else "Empty mongo::LockRequestList"

    def children(self) -> typing.Iterator[typing.Tuple[str, gdb.Value]]:
        lock_request = self.val["_front"]
        while lock_request != 0:
            yield ("", lock_request.dereference())
            lock_request = lock_request["next"]

    def __bool__(self) -> bool:
        """Return True if the linked list isn't empty, and return False otherwise."""
        return self.val["_front"] != 0


# pylint: disable-next=invalid-name
def ServiceContextClientsListIterator(service_context: gdb.Value, /) -> typing.Iterator[gdb.Value]:
    """Return a generator of every mongo::Client* in the given mongo::ServiceContext."""
    try:
        gdb.lookup_type("mongo::ServiceContext::ClientMap")
    except gdb.error as err:
        if not err.args[0].startswith("No type named "):
            raise

        for (_, client) in AbslNodeHashSetPrinter(service_context["_clients"]).children():
            yield client
    else:
        for (client, _) in AbslNodeHashMapPrinter(service_context["_clients"]).items():
            yield client


# pylint: disable-next=too-few-public-methods
class LockRequestPrinter(SupportsChildren):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::LockRequest."""

    _cached_threads: typing.ClassVar[typing.Optional[typing.Dict[int, gdb.InferiorThread]]] = None
    """Mapping from the pthread_t address (std::thread::id) to the associated gdb.InferiorThread."""

    _cached_operation_contexts: typing.ClassVar[typing.Optional[typing.Dict[int, gdb.Value]]] = None
    """Mapping from the mongo::Locker* address to the associated mongo::OperationContext*."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val

    def children(self) -> typing.Iterator[typing.Tuple[str, typing.Union[str, gdb.Value]]]:
        for field in self.val.type.fields():
            assert field.name is not None, (
                "Unexpected anonymous field in mongo::LockRequest struct")
            assert not field.is_base_class, (
                f"Unexpected base type '{field.name}' for mongo::LockRequest struct")
            assert not field.artificial, (
                f"Unexpected vtable '{field.name}' for mongo::LockRequest struct")

            if field.bitpos is None:
                # The mongo::LockRequest struct doesn't have any static members nor would it likely
                # ever have any. But we defensively skip listing any static members here.
                continue

            data_member = self.val[field.name]

            if field.name != "locker":
                yield (field.name, data_member)
                continue

            locker = data_member.dereference()
            locker_debug_info = locker["_debugInfo"]

            # We augment the field name displayed for the mongo::LockRequest::locker member to
            # include its type. GDB would otherwise only display the mongo::Locker* address.
            yield (f"locker = ({locker.dynamic_type.pointer()}) {hex(int(locker.address))}",
                   data_member)

            try:
                # The mongo::LockerImpl type was consolidated with its mongo::Locker base class as
                # part of SERVER-84753 in MongoDB 7.3.
                locker_impl_type = gdb.lookup_type("mongo::LockerImpl")
            except gdb.error as err:
                if not err.args[0].startswith("No type named "):
                    raise

                locker_impl_type = locker.type

            if locker_impl_type == locker.dynamic_type:
                thread_id = int(locker.cast(locker_impl_type)["_threadId"]["_M_thread"])

                self._populate_cached_threads()
                assert self._cached_threads is not None

                if (thread := self._cached_threads.get(thread_id)) is not None:
                    thread_name = f', "{thread.name}"' if thread.name else ""
                    thread_id_str = f"{hex(thread_id)} (GDB Id: thread {thread.num}{thread_name})"
                elif thread_id == 0:
                    thread_id_str = self._make_inactive_thread_hint(
                        StdStringPrinter(locker_debug_info).string())
                else:
                    # Only if the libthread_db library is not available would we expect to not find
                    # the thread's ID.
                    assert not self._cached_threads, f"Failed to identify thread {hex(thread_id)}"
                    thread_id_str = hex(thread_id)

                # gdb.Value.__str__() returns a Python string according to how the value would be
                # **printed** by GDB. We therefore yield `thread_id_str` directly rather than
                # gdb.Value(thread_id_str) to have the string text displayed verbatim.
                yield ("locker._threadId", thread_id_str)

            yield ("locker._debugInfo", locker_debug_info)

            self._populate_cached_operation_contexts()
            assert self._cached_operation_contexts is not None

            if (operation_context :=
                    self._cached_operation_contexts.get(int(locker.address))) is not None:
                # We augment the field name displayed for the mongo::LockRequest::$_opCtx
                # pseudo-member to include its type. GDB would otherwise only display the
                # mongo::OperationContext* address. The '$' character included in the field name was
                # intentionally chosen as invalid C++ and GDB syntax to avoid any naming collisions.
                yield (f"locker.$_opCtx = ({operation_context.type}) {hex(int(operation_context))}",
                       operation_context)

    def _make_inactive_thread_hint(self, locker_debug_info_str: str) -> str:
        if locker_debug_info_str.startswith("lsid: "):
            # https://github.com/mongodb/mongo/blob/r8.0.0-rc4/src/mongo/db/transaction/transaction_participant.cpp#L1360-L1364
            return "No active thread (likely an idle transaction)"

        if " operationType: " in locker_debug_info_str:
            # https://github.com/mongodb/mongo/blob/r8.0.0-rc4/src/mongo/db/s/sharding_ddl_coordinator.cpp#L336
            return "No active thread (likely a ShardingDDLCoordinator)"

        return "No active thread (Locker::unsetThreadId() was called)"

    @classmethod
    def _populate_cached_threads(cls) -> None:
        if cls._cached_threads is not None:
            # The cache has already been populated.
            return

        if not gdb_is_libthread_db_loaded():
            # gdb.InferiorThread.handle() raises a RuntimeError when the libthread_db library is not
            # available. In this situation, the pthread_t address (std::thread::id) cannot be known
            # for the gdb.InferiorThread. We return early and leave `_cached_threads` as an empty
            # dictionary to skip attempting to populate the cache later.
            cls._cached_threads = {}
            return

        # Using native byte ordering is only correct here because the libthread_db library won't be
        # available when cross-platform debugging.
        fmt = "=Q"
        cached_threads: typing.Dict[int, gdb.InferiorThread] = {}

        for thread in gdb.selected_inferior().threads():
            (thread_id, ) = struct.unpack_from(fmt, memoryview(thread.handle()))
            assert isinstance(thread_id, int)
            cached_threads[thread_id] = thread

        cls._cached_threads = cached_threads

    @classmethod
    def _populate_cached_operation_contexts(cls) -> None:
        if cls._cached_operation_contexts is not None:
            # The cache has already been populated.
            return

        service_context = gdb_lookup_value("mongo::(anonymous namespace)::globalServiceContext")
        assert service_context is not None

        cached_operation_contexts: typing.Dict[int, gdb.Value] = {}

        for client in ServiceContextClientsListIterator(service_context):
            if (operation_context := client["_opCtx"]) != 0:
                locker = operation_context["_locker"]

                # UniquePtrGetWorker.__call__(self, obj) is implemented by first calling
                # obj.dereference() on the supplied argument. This behavior for UniquePtrGetWorker
                # was introduced by https://gcc.gnu.org/bugzilla/show_bug.cgi?id=77990 and is
                # therefore present in all versions of the libstdc++ pretty printers for the MongoDB
                # toolchain. We pass in `obj.address` to UniquePtrGetWorker to cancel out the
                # obj.dereference() call.
                xmethod_worker = stdlib_xmethods.UniquePtrMethodsMatcher().match(locker.type, "get")
                if (locker_address := xmethod_worker(locker.address)) != 0:
                    cached_operation_contexts[int(locker_address)] = operation_context

        cls._cached_operation_contexts = cached_operation_contexts


# We don't have to_string() or children() defined on _ResourceIdFactoryPrinter right now. Until we
# have a sense of how else we might want to use the ResourceIdFactory in GDB pretty printers, it is
# probably best to mark the type as being internal to this module.
class _ResourceIdFactoryPrinter(ResourceIdFactoryGetter):
    """Pretty-printer for mongo::Lock::ResourceMutex::ResourceIdFactory."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.resource_labels = val["labels"]
        self.val = val

    def lookup_resource_mutex_label(self, res_id: gdb.Value, /) -> str:
        return self._lookup_resource_mutex_label_from(res_id, all_labels=self.resource_labels)

    @classmethod
    def from_global(cls) -> "_ResourceIdFactoryPrinter":
        """Return a _ResourceIdFactoryPrinter from its global definition."""
        # The ResourceIdFactory type was moved to be a nested type within mongo::Lock::ResourceMutex
        # as part of SERVER-70467 in MongoDB 6.3. Previously in MongoDB 6.0, the ResourceIdFactory
        # type was defined as its own top-level type.
        # https://github.com/mongodb/mongo/blob/r7.0.0/src/mongo/db/concurrency/d_concurrency.cpp#L77
        # https://github.com/mongodb/mongo/blob/r6.0.9/src/mongo/db/concurrency/d_concurrency.cpp#L91
        if (res_id_factory := gdb_lookup_value(
                # pylint: disable-next=line-too-long
                "mongo::Lock::ResourceMutex::ResourceIdFactory::_resourceIdFactory()::resourceIdFactory"
        )) is not None:
            return cls(StaticImmortalPrinter(res_id_factory).value())

        if (res_id_factory := gdb_lookup_value(
                "mongo::(anonymous namespace)::ResourceIdFactory::resourceIdFactory")) is not None:
            return cls(res_id_factory)

        raise ValueError("Failed to locate ResourceIdFactory")


# pylint: disable-next=too-few-public-methods
class ResourceIdPrinter(SupportsToString):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::ResourceId."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val
        self.full_hash = int(val["_fullHash"])

        resource_type_bits = gdb_lookup_value("mongo::ResourceId::resourceTypeBits")
        assert resource_type_bits is not None
        self.resource_type = gdb.Value(self.full_hash >> (64 - int(resource_type_bits))).cast(
            gdb.lookup_type("mongo::ResourceType"))
        self.hash_id = self.full_hash & ((2**64 - 1) >> int(resource_type_bits))

    def to_string(self) -> str:
        ret = f"{{{self.full_hash}: {self.resource_type}, {self.hash_id}}}"

        if self.resource_type == gdb_lookup_value("mongo::RESOURCE_MUTEX"):
            res_id_factory: ResourceIdFactoryGetter

            try:
                res_id_factory = _ResourceIdFactoryPrinter.from_global()
            except ValueError:
                res_id_factory = _ResourceCatalogPrinter.from_global()

            label = res_id_factory.lookup_resource_mutex_label(gdb.Value(self.hash_id))
            ret += f", {label}"

            if "DatabaseShardingState" == label:
                # The label for the DatabaseShardingState's ResourceMutex was changed as part of
                # SERVER-70610 in MongoDB 6.2 where it now embeds the database name in the label.
                # Previously in MongoDB 6.0, the labels for all DatabaseShardingStates'
                # ResourceMutexes were the same generic "DatabaseShardingState" string and meant
                # consulting the DatabaseShardingStateMap was the only way to know which
                # ResourceMutex corresponded to which DatabaseShardingState.
                try:
                    dss_map = _DatabaseShardingStateMapPrinter.from_global_service_context()
                except ValueError:
                    pass
                else:
                    if (db_name := dss_map.lookup_database_name(self.val)) is not None:
                        ret += f", {db_name}"

        if self.resource_type in (gdb_lookup_value("mongo::RESOURCE_DDL_DATABASE"),
                                  gdb_lookup_value("mongo::RESOURCE_DDL_COLLECTION")):
            # Names for the ScopedDatabaseDDLLock and ScopedCollectionDDLLock resources were added
            # to the ResourceCatalog as part of SERVER-77512.
            # https://github.com/mongodb/mongo/blob/r7.1.0/src/mongo/db/concurrency/resource_catalog.cpp#L66-L69
            resource_catalog = _ResourceCatalogPrinter.from_global()

            if (resource_name := resource_catalog.lookup_resource_name(self.val)) is not None:
                ret += f", {resource_name}"

        if self.resource_type in (gdb_lookup_value("mongo::RESOURCE_DATABASE"),
                                  gdb_lookup_value("mongo::RESOURCE_COLLECTION")):
            catalog: ResourceCatalogGetter

            try:
                catalog = _ResourceCatalogPrinter.from_global()
            except ValueError:
                catalog = _CollectionCatalogPrinter.from_global_service_context()

            if (nss := catalog.lookup_resource_name(self.val)) is not None:
                ret += f", {nss}"

        if (self.resource_type == gdb_lookup_value("mongo::RESOURCE_GLOBAL")
                and ResourceGlobalIdPrinter.is_type_defined()):
            global_res_id = gdb.Value(self.hash_id).cast(gdb.lookup_type("mongo::ResourceGlobalId"))
            ret += f", {global_res_id}"

        return ret


# pylint: disable-next=too-few-public-methods
class ResourceTypePrinter(SupportsToString):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::ResourceType."""

    @property
    def resource_type_names(self) -> typing.Tuple[str, ...]:
        # We duplicate the contents of mongo::ResourceTypeNames[] here for a couple reasons:
        #
        #   1. gdb.lookup_symbol("mongo::ResourceTypeNames") would OOM the GDB process when
        #      searching for the symbol in a dynamically-linked mongod executable.
        #
        #   2. While gdb.lookup_static_symbol("mongo::ResourceTypeNames").value() would avoid the
        #      memory pressure, that function is only available starting in the v4 toolchain.
        #      Moreover, the `const char*` values are almost surely to have been optimized out
        #      anyway.
        global_resource_names = ("Global", ) if ResourceGlobalIdPrinter.is_type_defined() else (
            "ParallelBatchWriterMode", "ReplicationStateTransition", "Global")

        tenant_resource_name = (("Tenant", )
                                if gdb_lookup_value("mongo::RESOURCE_TENANT") is not None else ())

        ddl_resource_names = (("DDLDatabase", "DDLCollection") if
                              gdb_lookup_value("mongo::RESOURCE_DDL_DATABASE") is not None else ())

        return (("Invalid", ) + global_resource_names + tenant_resource_name +
                ("Database", "Collection", "Metadata") + ddl_resource_names + ("Mutex", ))

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val

    def to_string(self) -> str:
        return self.resource_type_names[int(self.val)]


class ResourceGlobalIdPrinter(SupportsToString):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::ResourceGlobalId."""

    @property
    def resource_global_id_names(self) -> typing.Tuple[str, ...]:
        # We duplicate the contents of mongo::ResourceGlobalIdNames[] for the same reasons described
        # above in ResourceTypePrinter.

        # The parallel batch writer mutex was removed in MongoDB 7.1 as part of SERVER-38341.
        pbwm_resource_name = ("ParallelBatchWriterMode", ) if gdb_lookup_value(
            "mongo::resourceIdParallelBatchWriterMode") is not None else ()

        # The feature compatibility version full transition lock was replaced with an equivalent
        # barrier applied to only transaction operations in MongoDB 7.3 as part of SERVER-66340.
        txn_barrier_resource_name = ("MultiDocumentTransactionsBarrier", ) if gdb_lookup_value(
            "mongo::resourceIdMultiDocumentTransactionsBarrier") is not None else (
                "FeatureCompatibilityVersion", )

        return (pbwm_resource_name + txn_barrier_resource_name +
                ("ReplicationStateTransition", "Global"))

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val

    def to_string(self) -> str:
        return self.resource_global_id_names[int(self.val)]

    @staticmethod
    def is_type_defined() -> bool:
        """Return True if the ResourceGlobalId type is defined, and return False otherwise."""
        try:
            # The ResourceGlobalId type was introduced as part of SERVER-65821 in MongoDB 6.0 and
            # then subsequently backported to 4.4.15 and 5.0.10. resourceIdParallelBatchWriterMode
            # and resourceIdReplicationStateTransitionLock, along with a new
            # resourceIdFeatureCompatibilityVersion, all became distinct resources under the
            # RESOURCE_GLOBAL ResourceType. The top-level RESOURCE_PBWM and RESOURCE_RSTL
            # ResourceTypes were removed.
            gdb.lookup_type("mongo::ResourceGlobalId")
            return True
        except gdb.error as err:
            if not err.args[0].startswith("No type named "):
                raise

            return False


def add_printers(pretty_printer: gdb.printing.RegexpCollectionPrettyPrinter, /) -> None:
    """Add the LockManager related printers to the pretty printer collection given."""
    pretty_printer.add_printer("mongo::LockManager", "^mongo::LockManager$", LockManagerPrinter)
    pretty_printer.add_printer("mongo::LockRequestList", "^mongo::LockRequestList$",
                               LockRequestListPrinter)
    pretty_printer.add_printer("mongo::LockRequest", "^mongo::LockRequest$", LockRequestPrinter)
    pretty_printer.add_printer("mongo::ResourceId", "^mongo::ResourceId$", ResourceIdPrinter)
    pretty_printer.add_printer("mongo::ResourceType", "^mongo::ResourceType$", ResourceTypePrinter)
    pretty_printer.add_printer("mongo::ResourceGlobalId", "^mongo::ResourceGlobalId$",
                               ResourceGlobalIdPrinter)
