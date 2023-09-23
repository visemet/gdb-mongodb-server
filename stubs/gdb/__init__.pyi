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
"""https://sourceware.org/gdb/onlinedocs/gdb/Python-API.html"""

from gdb import events as events
from gdb import printing as printing
from gdb._architecture import Architecture as Architecture
from gdb._basic import parse_and_eval as parse_and_eval
from gdb._basic import execute as execute
from gdb._errors import error as error
from gdb._errors import MemoryError as MemoryError
from gdb._errors import GdbError as GdbError
from gdb.events import StopEvent as StopEvent
from gdb._frame import Frame as Frame
from gdb._frame import newest_frame as newest_frame
from gdb._frame import selected_frame as selected_frame
from gdb._inferior import Inferior as Inferior
from gdb._inferior import selected_inferior as selected_inferior
from gdb._inferiorthread import InferiorThread as InferiorThread
from gdb._inferiorthread import selected_thread as selected_thread
from gdb._objfile import Objfile as Objfile
from gdb._objfile import current_objfile as current_objfile
from gdb._progspace import Progspace as Progspace
from gdb._symbol import Symbol as Symbol
from gdb._symbol import lookup_symbol as lookup_symbol
from gdb._type import Field as Field
from gdb._type import Type as Type
from gdb._type import TypeCode
from gdb._type import lookup_type as lookup_type
from gdb._value import Value as Value

TYPE_CODE_BITSTRING = TypeCode.TYPE_CODE_BITSTRING
TYPE_CODE_PTR = TypeCode.TYPE_CODE_PTR
TYPE_CODE_ARRAY = TypeCode.TYPE_CODE_ARRAY
TYPE_CODE_STRUCT = TypeCode.TYPE_CODE_STRUCT
TYPE_CODE_UNION = TypeCode.TYPE_CODE_UNION
TYPE_CODE_ENUM = TypeCode.TYPE_CODE_ENUM
TYPE_CODE_FLAGS = TypeCode.TYPE_CODE_FLAGS
TYPE_CODE_FUNC = TypeCode.TYPE_CODE_FUNC
TYPE_CODE_INT = TypeCode.TYPE_CODE_INT
TYPE_CODE_FLT = TypeCode.TYPE_CODE_FLT
TYPE_CODE_VOID = TypeCode.TYPE_CODE_VOID
TYPE_CODE_SET = TypeCode.TYPE_CODE_SET
TYPE_CODE_RANGE = TypeCode.TYPE_CODE_RANGE
TYPE_CODE_STRING = TypeCode.TYPE_CODE_STRING
TYPE_CODE_ERROR = TypeCode.TYPE_CODE_ERROR
TYPE_CODE_METHOD = TypeCode.TYPE_CODE_METHOD
TYPE_CODE_METHODPTR = TypeCode.TYPE_CODE_METHODPTR
TYPE_CODE_MEMBERPTR = TypeCode.TYPE_CODE_MEMBERPTR
TYPE_CODE_REF = TypeCode.TYPE_CODE_REF
TYPE_CODE_RVALUE_REF = TypeCode.TYPE_CODE_RVALUE_REF
TYPE_CODE_CHAR = TypeCode.TYPE_CODE_CHAR
TYPE_CODE_BOOL = TypeCode.TYPE_CODE_BOOL
TYPE_CODE_COMPLEX = TypeCode.TYPE_CODE_COMPLEX
TYPE_CODE_TYPEDEF = TypeCode.TYPE_CODE_TYPEDEF
TYPE_CODE_NAMESPACE = TypeCode.TYPE_CODE_NAMESPACE
TYPE_CODE_DECFLOAT = TypeCode.TYPE_CODE_DECFLOAT
TYPE_CODE_INTERNAL_FUNCTION = TypeCode.TYPE_CODE_INTERNAL_FUNCTION
