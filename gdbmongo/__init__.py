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
"""The gdbmongo package contains GDB pretty printers and commands for debugging the MongoDB Server.
Its primary target audience is MongoDB employees.
"""

try:
    from gdbmongo._version import version as __version__
except ImportError:
    # The package is not installed so we don't bother giving it a version number.
    __version__ = None
