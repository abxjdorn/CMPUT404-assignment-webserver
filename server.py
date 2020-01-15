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

    class WebServerException(Exception):
        """ Exception causing the server to stop processing and
            respond with the specified status code.
        """
        def __init__(self, code, message):
            super().__init__(f'HTTP {code} {message}')
            self.code = code
            self.message = message


    BAD_REQUEST = WebServerException(400, 'Bad Request')


    @staticmethod
    def parse_http_ver(http_ver):
        """ Parse the HTTP version into major and minor parts.

        eg. HTTP/1.1 --> (1, 1)
        Returns tuple of ints (ver_maj, ver_min)
        Raises WebServerException if the format is invalid
        (including the part before the slash)
        """
        slash_split = http_ver.split('/')
        if len(slash_split) != 2: raise self.BAD_REQUEST
        if slash_split[0] != 'HTTP': raise self.BAD_REQUEST

        dot_split = slash_split[1].split('.')
        if len(dot_split) != 2: raise self.BAD_REQUEST
        try:
            return int(dot_split[0]), int(dot_split[1])
        except ValueError:
            raise self.BAD_REQUEST


    def handle(self):
        self.sio = SocketBuffer(self.request)

        try:
            req = self._read_request()

            self._send_line('HTTP/1.1 503 Service Unavailable')
        except self.WebServerException as e:
            self._send_line(f'HTTP/1.1 {e.code} {e.message}')
        except:
            # Try to send a valid response even if something went wrong
            self._send_line('HTTP/1.1 500 Internal Server Error')
            raise
        finally:
            self._finish()

        #self.data = self.request.recv(1024).strip()
        #print ("Got a request of: %s\n" % self.data)
        #self.request.sendall(bytearray("OK",'utf-8'))


    def _finish(self):
        self._send_line()
        self.request.close()


    def _send(self, text):
        print('> ' + text.strip('\n'))
        self.sio.write(text)


    def _recv_line(self):
        text = self.sio.readline().rstrip('\r\n')
        print ('< ' + text)
        return text


    def _send_line(self, text=''):
        self._send(text + '\n')


    def _read_request(self):
        """ Reads and parses a request message from the socket.

        Returns a Request object.
        Raises an appropriate WebServerException if the request
        cannot be parsed, is not HTTP/1.1, or has a method other
        than GET or HEAD.
        """

        # Read and parse the request line
        method, path, version = self._read_reqline()
        if version != (1, 1):
            raise self.WebServerException(505, 'HTTP Version Not Supported')

        # Read and parse the headers
        headers = dict()
        while True:
            header, value = self._read_header()
            if header is None: break # end of headers
            headers[header] = value

        return Request(method, path, version, headers)


    def _read_reqline(self):
        """ Reads and parses a request line (the first line of a request)
            from the socket.

        Empty lines before the request line will be consumed.

        Returns (method: str, path: str,
            (version_major: int, version_minor: int))
        Raises an appropriate WebServerException if the request line
        cannot be parsed.
        """

        # Get the first non-blank line
        requestLine = ''
        while not requestLine:
            requestLine = self._recv_line()

        # Split into url, path, http version
        parts = requestLine.split(' ')
        if len(parts) != 3: raise self.BAD_REQUEST
        method, path, http_ver = parts

        # Parse the http version
        ver_maj, ver_min = self.parse_http_ver(http_ver)

        return method, path, (ver_maj, ver_min)


if __name__ == "__main__":
    HOST, PORT = "localhost", 8080

    socketserver.TCPServer.allow_reuse_address = True
    # Create the server, binding to localhost on port 8080
    server = socketserver.TCPServer((HOST, PORT), MyWebServer)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
