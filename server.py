#  coding: utf-8 
import socketserver
import os, socket
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


WEB_ROOT = 'www/'


class Request:
    """ Data class representing a request. """
    def __init__(self, method, path, http_version, headers):
        self.method = method
        self.path = path
        self.http_version = http_version
        self.headers = headers


    def __str__(self):
        return (f'{self.method} '
                f'{self.path} '
                f'HTTP/{self.http_version[0]}.{self.http_version[1]}\n'
                + '\n'.join(f'{k}: {v}' for k, v in self.headers.items())
                + '\n\n')


class Response:
    OK = 200
    MOVED_PERMANENTLY = 301
    BAD_REQUEST = 400
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    INTERNAL_SERVER_ERROR = 500
    VERSION_NOT_SUPPORTED = 505

    STATUS_MESSAGES = {
            OK: 'OK',
            MOVED_PERMANENTLY: 'Moved Permanently',
            BAD_REQUEST: 'Bad Request',
            NOT_FOUND: 'Not Found',
            METHOD_NOT_ALLOWED: 'Method Not Allowed',
            INTERNAL_SERVER_ERROR: 'Internal Server Error',
            VERSION_NOT_SUPPORTED: 'HTTP Version Not Supported'
    }

    def __init__(self, code, *, headers=None, body=''):
        self.code = code
        self.body = body
        self.headers = headers or dict()


    def add_header(self, key, value):
        self.headers[key] = value


    def __str__(self):
        return (f'HTTP/1.1 {self.code} {self.STATUS_MESSAGES[self.code]}\n'
                + '\n'.join(f'{k}: {v}' for k, v in self.headers.items())
                + '\n\n' + self.body)



class MyWebServer(socketserver.BaseRequestHandler):
    """ Web server. """

    class WebServerException(Exception):
        """ Exception causing the server to stop processing and
            respond with the specified status code.
        """
        def __init__(self, code):
            super().__init__(
                    f'HTTP {code} {Response.STATUS_MESSAGES[message]}')
            self.resp = Response(code)


    @staticmethod
    def parse_http_ver(http_ver):
        """ Parse the HTTP version into major and minor parts.

        eg. HTTP/1.1 --> (1, 1)
        Returns tuple of ints (ver_maj, ver_min)
        Raises WebServerException if the format is invalid
        (including the part before the slash)
        """
        slash_split = http_ver.split('/')
        if len(slash_split) != 2: MyWebServer._bad_request()
        if slash_split[0] != 'HTTP': MyWebServer._bad_request()

        dot_split = slash_split[1].split('.')
        if len(dot_split) != 2: MyWebServer._bad_request()
        try:
            return int(dot_split[0]), int(dot_split[1])
        except ValueError:
            MyWebServer._bad_request()


    @staticmethod
    def guess_content_type(filename):
        if filename.endswith('.html'):
            return 'text/html'
        elif filename.endswith('.css'):
            return 'text/css'
        else:
            return 'text/plain'


    @staticmethod
    def _bad_request():
        raise MyWebServer.WebServerException(Response.BAD_REQUEST)


    @staticmethod
    def _not_found():
        raise MyWebServer.WebServerException(Response.NOT_FOUND)


    def handle(self):
        self.sio = SocketBuffer(self.request)

        try:
            req = self._read_request()
            resp = self._handle_request(req)

            self._send(str(resp))
        except self.WebServerException as e:
            self._send(str(e.resp))
        except:
            # Try to send a valid response even if something went wrong
            self._send_line('HTTP/1.1 500 Internal Server Error')
            raise
        finally:
            self._finish()

        #self.data = self.request.recv(1024).strip()
        #print ("Got a request of: %s\n" % self.data)
        #self.request.sendall(bytearray("OK",'utf-8'))


    def _handle_request(self, req):
        if req.method not in ['GET', 'HEAD']:
            return Response(Response.METHOD_NOT_ALLOWED)

        # Include the body if method is 'GET', but not if it is 'HEAD'
        includeBody = (req.method == 'GET')


        # Check the path...
        if not req.path.startswith('/'):
            # only local, absolute URLs are valid
            return Response(Response.NOT_FOUND)

        # Determine the file path indicated by the URL
        local_path = os.path.normpath(req.path[1:])
        if local_path.startswith('/') or local_path.startswith('..'):
            # don't allow rising above the path root
            return Response(Response.NOT_FOUND)

        file_path = os.path.join(WEB_ROOT, local_path)


        # Serve the content...
        if os.path.isdir(file_path):
            # this is a directory
            if not req.path.endswith('/'):
                return Response(Response.MOVED_PERMANENTLY,
                        headers={'Location': req.path + '/'})
            else:
                file_path = os.path.join(file_path, 'index.html')

        if not os.path.exists(file_path):
            # straightforwardly not found
            return Response(Response.NOT_FOUND)

        # this is a file: return it
        f = open(file_path)
        body = f.read()
        f.close()

        file_name = os.path.basename(file_path)
        content_type = self.guess_content_type(file_name)

        resp = Response(Response.OK,
                headers={'Content-Type': f'{content_type}; charset=utf-8'},
                body=body if includeBody else '')
        return resp


    def _finish(self):
        self._send_line()


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
            raise self.WebServerException(Response.VERSION_NOT_SUPPORTED)

        # Read and parse the headers
        headers = self._read_headers()

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
        if len(parts) != 3: self._bad_request()
        method, path, http_ver = parts

        # Parse the http version
        ver_maj, ver_min = self.parse_http_ver(http_ver)

        return method, path, (ver_maj, ver_min)


    def _read_headers(self):
        """ Reads and parses a block of header from the socket.

        Returns dict mapping header names (str) to values (str).
        Raises an appropriate WebServerException on parsing error.
        """

        headers = dict()
        last_header = None
        while True:
            # Get the next line
            headerLine = self._recv_line()
            if len(headerLine.strip()) == 0:
                # end of headers
                return headers
            if headerLine.startswith(' ') or headerLine.startswith('\t'):
                # this is a continuation line
                if last_header is None: self._bad_request()
                headers[last_header] += ' ' + headerLine.strip()
            else:
                parts = headerLine.split(':', 1)
                if len(parts) != 2: self._bad_request()
                last_header, value = parts
                if last_header in headers:
                    # duplicate header: merge the values
                    headers[last_header] += ',' + value.strip()
                else:
                    # entirely new header
                    headers[last_header] = value.strip()



if __name__ == "__main__":
    HOST, PORT = "localhost", 8080

    socketserver.TCPServer.allow_reuse_address = True
    # Create the server, binding to localhost on port 8080
    server = socketserver.TCPServer((HOST, PORT), MyWebServer)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
