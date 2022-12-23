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
"""https://github.com/gcc-mirror/gcc/blob/master/libstdc++-v3/python/libstdcxx/v6/printers.py"""

import abc
import typing

import gdb

from gdbmongo.printer_protocol import LazyString


def num_elements(num: int, /) -> str:
    ...


def function_pointer_to_name(func: gdb.Value, /) -> typing.Optional[str]:
    ...


class __PrettyPrinterProtocol(gdb.printing._PrettyPrinterProtocol, typing.Protocol):
    # The typename argument isn't part of GDB's pretty printing API. The pretty printers defined in
    # the gdb.libstdcxx.v6.printers package aren't registered individually and instead accept a
    # string corresponding to the C++ type for the subprinter.
    def __init__(self, typename: str, val: gdb.Value, /) -> None:
        ...

    def to_string(self) -> str | gdb.Value | LazyString | None:
        ...

    def children(self) -> typing.Iterator[typing.Tuple[str, gdb.Value]]:
        ...


class SharedPointerPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::shared_ptr"], val: gdb.Value, /):
        ...

    @property
    def pointer(self) -> gdb.Value:
        ...


class UniquePointerPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::unique_ptr"], val: gdb.Value, /):
        ...


class StdListPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::list"], val: gdb.Value, /):
        ...


class StdListIteratorPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::list::iterator"], val: gdb.Value, /):
        ...


class StdFwdListIteratorPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::forward_list::iterator"], val: gdb.Value, /):
        ...


class StdVectorPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::vector"], val: gdb.Value, /):
        ...

    class Iterator(typing.Iterator[typing.Tuple[str, gdb.Value]], metaclass=abc.ABCMeta):

        @property
        def item(self) -> gdb.Value:
            ...

        @property
        def finish(self) -> gdb.Value:
            ...

    def children(self) -> Iterator:
        ...


class StdVectorIteratorPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::vector::iterator"], val: gdb.Value, /):
        ...


class StdTuplePrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::tuple"], val: gdb.Value, /):
        ...


class StdStackOrQueuePrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::stack", "std::queue"], val: gdb.Value, /):
        ...


class StdRbtreeIteratorPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::map::iterator", "std::set::iterator"],
                 val: gdb.Value, /):
        ...


# StdDebugIteratorPrinter is only valid for --dbg=on builds.
class StdDebugIteratorPrinter(__PrettyPrinterProtocol):
    ...


class StdMapPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::map"], val: gdb.Value, /):
        ...


class StdSetPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::set"], val: gdb.Value, /):
        ...


class StdBitsetPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::bitset"], val: gdb.Value, /):
        ...


class StdDequePrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::deque"], val: gdb.Value, /):
        ...


class StdDequeIteratorPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::deque::iterator"], val: gdb.Value, /):
        ...


class StdStringPrinter(__PrettyPrinterProtocol):

    # Intentionally not constraining `typename` to be typing.Literal["std::basic_string"] because
    # the argument is used by StdStringPrinter to set its `new_string` attribute based on whether
    # the type contains "::__cxx11::basic_string".
    def __init__(self, typename: str, val: gdb.Value, /):
        ...


class Tr1UnorderedSetPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["tr1::unordered_set"], val: gdb.Value, /):
        ...


class Tr1UnorderedMapPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["tr1::unordered_map"], val: gdb.Value, /):
        ...


class StdForwardListPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::forward_list"], val: gdb.Value, /):
        ...


class StdExpAnyPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::any", "std::experimental::any"],
                 val: gdb.Value, /):
        ...


class StdExpOptionalPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::optional", "std::experimental::optional"],
                 val: gdb.Value, /):
        ...


class StdVariantPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::variant"], val: gdb.Value, /):
        ...


class StdNodeHandlePrinter(__PrettyPrinterProtocol):
    ...


class StdExpStringViewPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::basic_string_view",
                                                "std::experimental::basic_string_view"],
                 val: gdb.Value, /):
        ...


class StdExpPathPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::filesystem::path",
                                                "std::experimental::filesystem::path"],
                 val: gdb.Value, /):
        ...


class StdPairPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::pair"], val: gdb.Value, /):
        ...


# The following classes are only present in
# /opt/mongodbtoolchain/v4/share/gcc-11.2.0/python/libstdcxx/v6/printers.py.


class __StdBitIteratorPrinter(__PrettyPrinterProtocol):
    ...


class __StdBitReferencePrinter(__PrettyPrinterProtocol):
    ...


class __StdPathPrinter(__PrettyPrinterProtocol):

    def __init__(self, typename: typing.Literal["std::filesystem::path"], val: gdb.Value, /):
        ...


class __StdCmpCatPrinter(__PrettyPrinterProtocol):
    ...


StdBitIteratorPrinter: typing.Optional[typing.Type[__StdBitIteratorPrinter]]
StdBitReferencePrinter: typing.Optional[typing.Type[__StdBitReferencePrinter]]
StdPathPrinter: typing.Optional[typing.Type[__StdPathPrinter]]
StdCmpCatPrinter: typing.Optional[typing.Type[__StdCmpCatPrinter]]
