#  coding: utf-8 
import socketserver
import sys, os, io, time

import myhttp
from myhttp import Request, Response, HTTPVersion
from socketio import SocketIO


LOG_REQUESTS = False # set to True to log requests/responses to stderr
WEB_ROOT = 'www/' # local directory corresponding to URL path root


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
                    headers={'Allow': 'GET, HEAD'})

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
            f = open(path, mode='rb')
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


    class SocketIterator:
        """ Decoding iterator over a SocketBuffer yielding lines. """
        def __init__(self, sio):
            self.sio = io.TextIOWrapper(
                    io.BufferedReader(sio), newline='\r\n')


        def __next__(self):
            """ Read a line from the socket.

            Returns a line of text (str), with the trailing newline removed.

            Raises ClientDisconnected if the socket has been disconnected
            from the other side.
            """

            text = self.sio.readline()
            if not text: raise self.ClientDisconnected()
            stripped = text.rstrip('\r\n')
            return stripped


    def handle(self):
        self.handler = MyHTTPHandler(WEB_ROOT)
        self.sio = SocketIO(self.request)

        try:
            req = Request.read_from(self.SocketIterator(self.sio))
            if LOG_REQUESTS:
                print(('{}:{} {} {}').format(
                    self.client_address[0],
                    self.client_address[1],
                    req.method, req.path), file=sys.stderr)
            resp = self.handler.handle_request(req)
        except myhttp.ParseError:
            resp = Response(Response.BAD_REQUEST)
        except self.ClientDisconnected:
            # nothing to do, really
            return
        except:
            # Try to send a valid response even if something went wrong
            if LOG_REQUESTS:
                print('500 Internal Server Error', file=sys.stderr)
            self.sio.write(b'HTTP/1.1 500 Internal Server Error\r\n')
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
        if LOG_REQUESTS:
            print('    {} {}'.format(
                resp.code, resp.status_message()), file=sys.stderr)
        self.sio.write(bytes(resp))


if __name__ == "__main__":
    HOST, PORT = "localhost", 8080

    socketserver.TCPServer.allow_reuse_address = True
    # Create the server, binding to localhost on port 8080
    server = socketserver.TCPServer((HOST, PORT), MyWebServer)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
