#  coding: utf-8 
import socketserver
from socketio import SocketBuffer


# Copyright 2020 Abram Hindle, Eddie Antonio Santos, John Dorn
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
#
#
# Furthermore it is derived from the Python documentation examples thus
# some of the code is Copyright © 2001-2013 Python Software
# Foundation; All Rights Reserved
#
# http://docs.python.org/2/library/socketserver.html
#
# run: python freetests.py

# try: curl -v -X GET http://127.0.0.1:8080/


class MyWebServer(socketserver.BaseRequestHandler):
    """ Web server. """

    def handle(self):
        self.sio = SocketBuffer(self.request)
        req = self._parse_request()

        self._send_line('HTTP/1.1 404 Not Found')
        self._send_line()
        #self.data = self.request.recv(1024).strip()
        #print ("Got a request of: %s\n" % self.data)
        #self.request.sendall(bytearray("OK",'utf-8'))


    def _send(self, text):
        print('> ' + text.strip('\n'))
        self.sio.write(text)


    def _recv_line(self):
        text = self.sio.readline()
        print ('< ' + text.strip('\n'))
        return text


    def _send_line(self, text=''):
        self._send(text + '\n')


    def _parse_request(self):
        self._recv_line()


if __name__ == "__main__":
    HOST, PORT = "localhost", 8080

    socketserver.TCPServer.allow_reuse_address = True
    # Create the server, binding to localhost on port 8080
    server = socketserver.TCPServer((HOST, PORT), MyWebServer)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
