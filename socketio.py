import io

# Copyright 2020 John Dorn
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


class SocketIO(io.RawIOBase):
    """ Raw IO wrapper around a socket.

    Supports both reading and writing.
    """

    def __init__(self, socket):
        super().__init__()
        self.socket = socket


    def readinto(self, b):
        return self.socket.recv_into(b)


    def write(self, b):
        return self.socket.send(b)


    def readable(self):
        return True


    def writable(self):
        return True


class SocketBuffer(io.TextIOWrapper):
    """ Self-configuring TextIOWrapper around a socket. """

    def __init__(self, socket):
        super().__init__(io.BufferedRWPair(
            SocketIO(socket),
            SocketIO(socket)),
            newline='\r\n', line_buffering=True)