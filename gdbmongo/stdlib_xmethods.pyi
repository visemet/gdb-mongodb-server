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
"""https://github.com/gcc-mirror/gcc/blob/master/libstdc++-v3/python/libstdcxx/v6/xmethods.py"""

import typing

import gdb


# Intentionally diverging from the true class hierarchy by not inheriting from
# gdb.xmethod.XMethodWorker. However, this enables us to keep the signature for __call__ more
# constrained.
class ArrayWorkerBase:

    def __init__(self, val_type: gdb.Type, size: gdb.Value, /) -> None:
        ...


class ArraySizeWorker(ArrayWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> gdb.Value:
        ...


class ArrayEmptyWorker(ArrayWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> bool:
        ...


class ArrayFrontWorker(ArrayWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> gdb.Value:
        ...


class ArrayBackWorker(ArrayWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> gdb.Value:
        ...


class ArrayAtWorker(ArrayWorkerBase):

    def __call__(self, obj: gdb.Value, index: gdb.Value, /) -> gdb.Value:
        ...


class ArraySubscriptWorker(ArrayWorkerBase):

    def __call__(self, obj: gdb.Value, index: gdb.Value, /) -> gdb.Value:
        ...


class ArrayMethodsMatcher:

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["size"],
              /) -> ArraySizeWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["empty"],
              /) -> ArrayEmptyWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["front"],
              /) -> ArrayFrontWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["back"],
              /) -> ArrayBackWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["at"], /) -> ArrayAtWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["operator[]"],
              /) -> ArraySubscriptWorker:
        ...


# Intentionally diverging from the true class hierarchy by not inheriting from
# gdb.xmethod.XMethodWorker. However, this enables us to keep the signature for __call__ more
# constrained.
class DequeWorkerBase:

    def __init__(self, val_type: gdb.Type, /) -> None:
        ...


class DequeEmptyWorker(DequeWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> bool:
        ...


class DequeSizeWorker(DequeWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> gdb.Value:
        ...


class DequeFrontWorker(DequeWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> gdb.Value:
        ...


class DequeBackWorker(DequeWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> gdb.Value:
        ...


class DequeSubscriptWorker(DequeWorkerBase):

    def __call__(self, obj: gdb.Value, subscript: gdb.Value, /) -> gdb.Value:
        ...


class DequeAtWorker(DequeWorkerBase):

    def __call__(self, obj: gdb.Value, index: gdb.Value, /) -> gdb.Value:
        ...


class DequeMethodsMatcher:

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["empty"],
              /) -> DequeEmptyWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["size"],
              /) -> DequeSizeWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["front"],
              /) -> DequeFrontWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["back"],
              /) -> DequeBackWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["operator[]"],
              /) -> DequeSubscriptWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["at"], /) -> DequeAtWorker:
        ...


# Intentionally diverging from the true class hierarchy by not inheriting from
# gdb.xmethod.XMethodWorker. However, this enables us to keep the signature for __call__ more
# constrained.
class ForwardListWorkerBase:

    def __init__(self, val_type: gdb.Type, node_type: gdb.Type, /) -> None:
        ...


class ForwardListEmptyWorker(ForwardListWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> bool:
        ...


class ForwardListFrontWorker(ForwardListWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> gdb.Value:
        ...


class ForwardListMethodsMatcher:

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["empty"],
              /) -> ForwardListEmptyWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["front"],
              /) -> ForwardListFrontWorker:
        ...


# Intentionally diverging from the true class hierarchy by not inheriting from
# gdb.xmethod.XMethodWorker. However, this enables us to keep the signature for __call__ more
# constrained.
class ListWorkerBase:

    def __init__(self, val_type: gdb.Type, node_type: gdb.Type, /):
        ...


class ListEmptyWorker(ListWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> bool:
        ...


class ListSizeWorker(ListWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> int:
        ...


class ListFrontWorker(ListWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> gdb.Value:
        ...


class ListBackWorker(ListWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> gdb.Value:
        ...


class ListMethodsMatcher:

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["empty"],
              /) -> ListEmptyWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["size"], /) -> ListSizeWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["front"],
              /) -> ListFrontWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["back"], /) -> ListBackWorker:
        ...


# Intentionally diverging from the true class hierarchy by not inheriting from
# gdb.xmethod.XMethodWorker. However, this enables us to keep the signature for __call__ more
# constrained.
class VectorWorkerBase:

    def __init__(self, val_type: gdb.Type, /) -> None:
        ...


class VectorEmptyWorker(VectorWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> bool:
        ...


class VectorSizeWorker(VectorWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> gdb.Value:
        ...


class VectorFrontWorker(VectorWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> gdb.Value:
        ...


class VectorBackWorker(VectorWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> gdb.Value:
        ...


class VectorAtWorker(VectorWorkerBase):

    def __call__(self, obj: gdb.Value, index: gdb.Value, /) -> gdb.Value:
        ...


class VectorSubscriptWorker(VectorWorkerBase):

    def __call__(self, obj: gdb.Value, subscript: gdb.Value, /) -> gdb.Value:
        ...


class VectorMethodsMatcher:

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["empty"],
              /) -> VectorEmptyWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["size"],
              /) -> VectorSizeWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["front"],
              /) -> VectorFrontWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["back"],
              /) -> VectorBackWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["at"], /) -> VectorAtWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["operator[]"],
              /) -> VectorSubscriptWorker:
        ...


# Intentionally diverging from the true class hierarchy by not inheriting from
# gdb.xmethod.XMethodWorker. However, this enables us to keep the signature for __call__ more
# constrained.
class AssociativeContainerWorkerBase:

    def __init__(self, unordered: bool, /):
        ...


class AssociativeContainerEmptyWorker(AssociativeContainerWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> bool:
        ...


class AssociativeContainerSizeWorker(AssociativeContainerWorkerBase):

    def __call__(self, obj: gdb.Value, /) -> gdb.Value:
        ...


class AssociativeContainerMethodsMatcher:

    def __init__(self, name: typing.Literal["set", "map", "multiset", "multimap", "unordered_set",
                                            "unordered_map", "unordered_multiset",
                                            "unordered_multimap"], /):
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["empty"],
              /) -> AssociativeContainerEmptyWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["size"],
              /) -> AssociativeContainerSizeWorker:
        ...


class UniquePtrGetWorker:

    def __init__(self, elem_type: gdb.Type, /):
        ...

    def __call__(self, obj: gdb.Value, /) -> gdb.Value:
        ...


class UniquePtrDerefWorker(UniquePtrGetWorker):
    ...


# Intentionally diverging from the true class hierarchy by not inheriting from UniquePtrGetWorker.
# However, this enables us to keep the signature for __call__ more constrained.
class UniquePtrSubscriptWorker:

    def __init__(self, elem_type: gdb.Type, /):
        ...

    def __call__(self, obj: gdb.Value, index: gdb.Value, /) -> gdb.Value:
        ...


class UniquePtrMethodsMatcher:

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["get"],
              /) -> UniquePtrGetWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["operator->"],
              /) -> UniquePtrGetWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["operator*"],
              /) -> UniquePtrDerefWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["operator[]"],
              /) -> UniquePtrSubscriptWorker:
        ...


# Intentionally diverging from the true class hierarchy by not inheriting from
# gdb.xmethod.XMethodWorker. However, this enables us to keep the signature for __call__ more
# constrained.
class SharedPtrGetWorker:

    def __init__(self, elem_type: gdb.Type, /):
        ...

    def __call__(self, obj: gdb.Value, /) -> gdb.Value:
        ...


class SharedPtrDerefWorker(SharedPtrGetWorker):

    def __call__(self, obj: gdb.Value, /) -> gdb.Value:
        ...


# Intentionally diverging from the true class hierarchy by not inheriting from SharedPtrGetWorker.
# However, this enables us to keep the signature for __call__ more constrained.
class SharedPtrSubscriptWorker:

    def __init__(self, elem_type: gdb.Type, /):
        ...

    def __call__(self, obj: gdb.Value, index: gdb.Value, /) -> gdb.Value:
        ...


# Intentionally diverging from the true class hierarchy by not inheriting from
# gdb.xmethod.XMethodWorker. However, this enables us to keep the signature for __call__ more
# constrained.
class SharedPtrUseCountWorker:

    def __init__(self, elem_type: gdb.Type, /):
        ...

    def __call__(self, obj: gdb.Value, /) -> int | gdb.Value:
        ...


# Intentionally diverging from the true class hierarchy by not inheriting from
# SharedPtrUseCountWorker. However, this enables us to keep the signature for __call__ more
# constrained.
class SharedPtrUniqueWorker:

    def __init__(self, elem_type: gdb.Type, /):
        ...

    def __call__(self, obj: gdb.Value, /) -> bool:
        ...


class SharedPtrMethodsMatcher:

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["get"],
              /) -> SharedPtrGetWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["operator->"],
              /) -> SharedPtrGetWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["operator*"],
              /) -> SharedPtrDerefWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["operator[]"],
              /) -> SharedPtrSubscriptWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["use_count"],
              /) -> SharedPtrUseCountWorker:
        ...

    @typing.overload
    def match(self, class_type: gdb.Type, method_name: typing.Literal["unique"],
              /) -> SharedPtrUniqueWorker:
        ...
