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
import typing

SharedPointerPrinter: typing.Any
UniquePointerPrinter: typing.Any
StdListPrinter: typing.Any
StdListIteratorPrinter: typing.Any
StdFwdListIteratorPrinter: typing.Any
StdVectorPrinter: typing.Any
StdVectorIteratorPrinter: typing.Any
StdTuplePrinter: typing.Any
StdStackOrQueuePrinter: typing.Any
StdRbtreeIteratorPrinter: typing.Any
StdDebugIteratorPrinter: typing.Any
StdMapPrinter: typing.Any
StdSetPrinter: typing.Any
StdBitsetPrinter: typing.Any
StdDequePrinter: typing.Any
StdDequeIteratorPrinter: typing.Any
StdStringPrinter: typing.Any
Tr1UnorderedSetPrinter: typing.Any
Tr1UnorderedMapPrinter: typing.Any
StdForwardListPrinter: typing.Any
StdExpAnyPrinter: typing.Any
StdExpOptionalPrinter: typing.Any
StdVariantPrinter: typing.Any
StdNodeHandlePrinter: typing.Any
StdExpStringViewPrinter: typing.Any
StdExpPathPrinter: typing.Any
StdPairPrinter: typing.Any

# Only present in /opt/mongodbtoolchain/v4/share/gcc-11.2.0/python/libstdcxx/v6/printers.py.
StdBitIteratorPrinter: typing.Optional[typing.Any]
StdBitReferencePrinter: typing.Optional[typing.Any]
# StdDebugIteratorPrinter is additionally only present in --dbg=on builds.
StdDebugIteratorPrinter: typing.Optional[typing.Any]
StdPathPrinter: typing.Optional[typing.Any]
StdCmpCatPrinter: typing.Optional[typing.Any]
