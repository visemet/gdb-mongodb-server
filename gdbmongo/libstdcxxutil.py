###
# Copyright 2025-present MongoDB, Inc.
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
"""Utility functions for libstdc++ types."""

import gdb

from gdbmongo import stdlib_xmethods


def shared_ptr_get(obj: gdb.Value, /) -> gdb.Value:
    """Return the stored T* pointer underlying a std::shared_ptr<T>."""
    xmethod_worker = stdlib_xmethods.SharedPtrMethodsMatcher().match(obj.type, "get")
    return xmethod_worker(obj)


def unique_ptr_get(obj: gdb.Value, /) -> gdb.Value:
    """Return the stored T* pointer underlying a std::unique_ptr<T>."""
    xmethod_worker = stdlib_xmethods.UniquePtrMethodsMatcher().match(obj.type, "get")

    # UniquePtrGetWorker.__call__(self, obj) is implemented by first calling obj.dereference() on
    # the supplied argument. This behavior for UniquePtrGetWorker was introduced by
    # https://gcc.gnu.org/bugzilla/show_bug.cgi?id=77990 and is therefore present in all versions of
    # the libstdc++ pretty printers for the MongoDB toolchain. We pass in `obj.address` to
    # UniquePtrGetWorker to cancel out the obj.dereference() call.
    return xmethod_worker(obj.address)


def vector_size(obj: gdb.Value, /) -> gdb.Value:
    """Return the number of elements in a std::vector<T>."""
    xmethod_worker = stdlib_xmethods.VectorMethodsMatcher().match(obj.type, "size")
    return xmethod_worker(obj)
