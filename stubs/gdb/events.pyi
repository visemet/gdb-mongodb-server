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
"""https://sourceware.org/gdb/onlinedocs/gdb/Events-In-Python.html"""

import typing

NotifyFunc = typing.TypeVar("NotifyFunc", bound=typing.Callable[..., None])


class EventRegistry(typing.Generic[NotifyFunc]):

    def connect(self, func: NotifyFunc, /) -> None:
        ...

    def disconnect(self, func: NotifyFunc, /) -> None:
        ...


before_prompt: EventRegistry[typing.Callable[[], None]]


class StopEvent:
    pass


stop: EventRegistry[typing.Callable[[StopEvent], None]]
