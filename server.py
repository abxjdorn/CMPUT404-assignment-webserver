#  coding: utf-8 
import socketserver
import sys, os, time

import myhttp
from myhttp import Request, Response, HTTPVersion
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


class MyHTTPHandler:
    """ HTTP request handler. """

    def __init__(self, web_root):
        """ Creates a handler which will serve files from the
            specified directory.

        web_root: str -- local path to web root directory
                         (files will be served from here)
        """
        self.web_root = web_root


    def handle_request(self, req):
        """ Handle an HTTP request.

        req: Request --- Request object specifying the HTTP request
        Returns a Response object specifying the HTTP response.
        """

        assert isinstance(req, Request)

        # Respond with 505 to unsupported methods
        if req.method not in ['GET', 'HEAD']:
            return Response(Response.METHOD_NOT_ALLOWED,
                    headers={'Allow', 'GET, HEAD'})

        # Fail if the URL is not a local, absolute path
        if not req.path.startswith('/'):
            return Response(Response.NOT_FOUND)

        # Normalize the request path to determine the relative file path
        rel_path = os.path.normpath(req.path[1:])

        # Reject requests that aren't inside the relative root
        if rel_path.startswith('/') or rel_path.startswith('..'):
            return Response(Response.NOT_FOUND)

        # Generate the local filesystem path corresponding to the request
        local_path = os.path.join(self.web_root, rel_path)

        # Redirect 'open' directory paths to their 'closed' equivalents
        if os.path.isdir(local_path) and not req.path.endswith('/'):
            return Response(Response.MOVED_PERMANENTLY,
                    headers={'Location': req.path + '/'})

        # Serve the content
        include_body = (req.method == 'GET')
        return self._serve_path(local_path, include_body)


    def _serve_path(self, path, include_body):
        """ Generate a response appropriate for a specified local path.

        path: str -- local path relative to the web root
        include_body: bool -- whether to include the body

        Returns a Response object appropriate for the path,
        which might be a not-found response if no content exists.

        If include_body is False, the body will be excluded from the Response
        (ie. a HEAD request rather than a GET)
        """

        assert isinstance(path, str)

        # Serve index.html from directories
        if os.path.isdir(path):
            path = os.path.join(path, 'index.html')

        # Respond with 404 if the content doesn't exist
        if not os.path.exists(path):
            return Response(Response.NOT_FOUND)

        # Read the content
        if include_body:
            f = open(path)
            body = f.read()
            f.close()
        else:
            body = ''

        content_length = len(body)

        # Guess the content-type
        file_name = os.path.basename(path)
        content_type = myhttp.guess_content_type(file_name)

        # Generate a response
        return Response(Response.OK,
                headers={
                    'Content-Type': content_type,
                    'Content-Length': content_length
                },
                body=body)


class MyWebServer(socketserver.BaseRequestHandler):
    """ Web server. """

    class ClientDisconnected(Exception):
        """ Raised when a client disconnects while the server
            is waiting for it to transmit.
        """
        pass


    class BadRequest(Exception):
        """ Raised when parsing the client's request fails. """
        pass


    def handle(self):
        self.handler = MyHTTPHandler(WEB_ROOT)
        self.sio = SocketBuffer(self.request)

        try:
            req = self._read_request()
            print(f'{self.client_address[0]}:{self.client_address[1]} '
                f'{req.method} {req.path}', file=sys.stderr)
            resp = self.handler.handle_request(req)
        except self.BadRequest:
            resp = Response(Response.BAD_REQUEST)
        except self.ClientDisconnected:
            # nothing to do, really
            return
        except:
            # Try to send a valid response even if something went wrong
            print('500 Internal Server Error', file=sys.stderr)
            self.sio.write('HTTP/1.1 500 Internal Server Error\n\n')
            raise

        # Attach required header
        resp.attach_header('Connection', 'close')

        # send
        self._send_response(resp)


    def _send_response(self, resp):
        """ Write an HTTP response as represented by a Response object
            to the socket.

        resp: Response
        """

        assert isinstance(resp, Response)

        # Attach the current date
        gmt_now = time.gmtime()
        ftime = time.strftime('%a, %d %b %Y %H:%M:%S GMT', gmt_now)
        resp.attach_header('Date', ftime)

        # write
        print(f'    {resp.code} {resp.status_message()}', file=sys.stderr)
        self.sio.write(str(resp))


    def _recv_line(self):
        """ Read a line from the socket.

        Returns a line of text (str), with the trailing newline removed.

        Raises ClientDisconnected if the socket has been disconnected
        from the other side.
        """

        text = self.sio.readline()
        if not text: raise self.ClientDisconnected()
        stripped = text.rstrip('\r\n')
        return stripped


    def _read_request(self):
        """ Reads and parses a request message from the socket.

        Returns a Request object.
        Raises BadRequest if the request cannot be parsed.
        If the version is not HTTP/1.1, the headers will not be
        parsed, since their format is not known.

        Request bodies will be ignored.
        """

        # Read and parse the request line
        method, path, version = self._read_reqline()

        # Stop early if the version is unsupported
        if version != HTTPVersion(1, 1): return

        # Read and parse the headers
        headers = self._read_headers()

        # Build a Request object
        return Request(method, path, version, headers=headers)


    def _read_reqline(self):
        """ Reads and parses a request line (the first line of a request)
            from the socket.

        Empty lines before the request line will be consumed.

        Returns (method: str, path: str, ver: HTTPVersion)
        Raises BadRequest if the request line cannot be parsed.
        """

        # Get the first non-blank line
        requestLine = ''
        while not requestLine:
            requestLine = self._recv_line()

        # Split into url, path, http version
        parts = requestLine.split(' ')
        if len(parts) != 3: raise self.BadRequest()
        method, path, ver_string = parts

        # Parse the http version
        ver = HTTPVersion.parse(ver_string)

        return method, path, ver


    def _read_headers(self):
        """ Reads and parses a block of headers from the socket.

        Returns dict mapping header names (str) to values (str).
        Raises BadRequest on parsing error.
        """

        headers = dict()
        last_header = None

        while True:
            # Get the next line
            headerLine = self._recv_line()

            # Stop at end of headers
            if len(headerLine.strip()) == 0: return headers

            if headerLine.startswith(' ') or headerLine.startswith('\t'):
                # Merge continuation lines with the current header's value
                if last_header is None: raise self.BadRequest()
                headers[last_header] += ' ' + headerLine.strip()
            else:
                # Separate header into name and value
                parts = headerLine.split(':', 1)
                if len(parts) != 2: raise self.BadRequest()
                last_header, value = parts

                if last_header in headers:
                    # Merge values of duplicate headers
                    headers[last_header] += ',' + value.strip()
                else:
                    # Create an entirely new header
                    headers[last_header] = value.strip()



if __name__ == "__main__":
    HOST, PORT = "localhost", 8080

    socketserver.TCPServer.allow_reuse_address = True
    # Create the server, binding to localhost on port 8080
    server = socketserver.TCPServer((HOST, PORT), MyWebServer)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
