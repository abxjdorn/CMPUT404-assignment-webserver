
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

# This file implements concepts from the HTTP/1.1 specification
# (RFC 2161, https://www.ietf.org/rfc/rfc2616.txt)


class ParseError(Exception):
    """ Raised on parsing failure. """
    pass


class HTTPVersion:
    """ Representation of an HTTP protocol version, eg. HTTP/1.1 """

    @staticmethod
    def parse(string):
        """ Parse an HTTP version string into major and minor parts.

        string: str -- string representation of HTTP version
        eg. 'HTTP/1.1' --> HTTPVersion(1, 1)
        Returns new HTTPVersion(major, minor)
        Raises ValueError if the format is invalid.
        """

        # Separate out the major and minor versions
        if not string.startswith('HTTP/'): raise ValueError()
        parts = string[len('HTTP/'):].split('.')
        if len(parts) != 2: raise ValueError()

        # Convert them to integers
        return HTTPVersion(*map(int, parts))


    def __init__(self, major, minor):
        """ Create representation of HTTP version {major}.{minor}.

        major: int -- major component of version
        minor: int -- minor component of version
        Raises ValueError if either component is negative.
        """

        if major < 0 or minor < 0: raise ValueError()
        self.major = major
        self.minor = minor


    def __eq__(self, other):
        return (isinstance(other, HTTPVersion)
                and self.major == other.major
                and self.minor == other.minor)


    def __str__(self):
        return 'HTTP/' + str(self.major) + '.' + str(self.minor)


    def __bytes__(self):
        return bytes(str(self), encoding='ascii')


    def __repr__(self):
        return 'HTTPVersion(' + str(self.major) + ', ' + str(self.minor) + ')'


class Message:
    """ Abstract class for functionality shared
        between Request and Response.
    """

    @staticmethod
    def read_headers_from(lines):
        """ Reads and parses a block of headers from an iterable of lines.

        Returns dict mapping header names (str) to values (str).
        Raises ParseError on parsing error.
        """

        headers = dict()
        last_header = None

        while True:
            # Get the next line
            headerLine = next(lines)

            # Stop at end of headers
            if len(headerLine.strip()) == 0: return headers

            if headerLine.startswith(' ') or headerLine.startswith('\t'):
                # Merge continuation lines with the current header's value
                if last_header is None: raise self.ParseError()
                headers[last_header] += ' ' + headerLine.strip()
            else:
                # Separate header into name and value
                parts = headerLine.split(':', 1)
                if len(parts) != 2: raise self.ParseError()
                last_header, value = parts

                if last_header in headers:
                    # Merge values of duplicate headers
                    headers[last_header] += ',' + value.strip()
                else:
                    # Create an entirely new header
                    headers[last_header] = value.strip()


    def __init__(self, ver=None, headers=None, body=None):
        """ Initialize data shared between request and response.

        ver: HTTPVersion -- HTTPVersion specified by response;
                            defaults to HTTP/1.1
        headers: dict -- headers of the response; defaults to empty dict
        body: bytes -- body content of the response; defaults to empty
        """

        assert ver is None or isinstance(ver, HTTPVersion)
        assert headers is None or isinstance(headers, dict)
        assert body is None or isinstance(body, bytes)

        self.ver = ver or HTTPVersion(1, 1)
        self.headers = headers or dict()
        self.body = body or b''


    def attach_header(self, header, value):
        """ Attach a header to an existing request.

        header: str -- header name
        value: str -- header value

        If the header already exists, it will be merged with the new value.
        """

        if header in self.headers.keys():
            self.headers[header] += ', ' + value
        else:
            self.headers[header] = value


    def _message_line(self):
        """ Generates the "message line": the first line of the message.

        Must be implemented by concrete subclasses.
        """
        raise NotImplementedError()


    def __bytes__(self):
        return (bytes(self._message_line() + '\r\n'
                + '\r\n'.join('{}: {}'.format(k, v)
                    for k, v in self.headers.items())
                + '\r\n\r\n', encoding='ascii')
                + self.body)


    def __str__(self):
        return (self._message_line() + '\n'
                + '\n'.join('{}: {}'.format(k, v)
                    for k, v in self.headers.items())
                + '\n\n'
                + str(self.body))


class Request(Message):
    """ An HTTP request. """

    @staticmethod
    def read_from(lines):
        """ Reads and parses a request message from an iterable of lines.

        Returns a Request object.
        Raises ParseError if the request cannot be parsed.
        If the version is not HTTP/1.1, the headers will not be
        parsed, since their format is not known.

        Request bodies will be ignored.
        """

        # Read and parse the request line
        method, path, version = Request._read_reqline(lines)

        # Stop early if the version is unsupported
        if version != HTTPVersion(1, 1): return

        # Read and parse the headers
        headers = Message.read_headers_from(lines)

        # Build a Request object
        return Request(method, path, version, headers=headers)


    @staticmethod
    def _read_reqline(lines):
        """ Reads and parses a request line (the first line of a request)
            from an iterable of lines.

        Empty lines before the request line will be consumed.

        Returns (method: str, path: str, ver: HTTPVersion)
        Raises ParseError if the request line cannot be parsed.
        """

        # Get the first non-blank line
        requestLine = ''
        while not requestLine:
            requestLine = next(lines)

        # Split into url, path, http version
        parts = requestLine.split(' ')
        if len(parts) != 3: raise self.ParseError()
        method, path, ver_string = parts

        # Parse the http version
        ver = HTTPVersion.parse(ver_string)

        return method, path, ver


    def __init__(self, method, path, ver=None, headers=None, body=None):
        """ Create an HTTP request.

        method: str -- HTTP method
        path: str -- request path
        ver: HTTPVersion -- HTTP version specified by request;
                            defaults to HTTP/1.1
        headers: dict -- headers of the request; defaults to empty dict
        body: str -- body content of the response; defaults to empty str
        """

        assert isinstance(method, str)
        assert isinstance(path, str)

        super().__init__(ver, headers, body)
        self.method = method
        self.path = path


    def _message_line(self):
        return '{} {} {}'.format(self.method, self.path, self.ver)


class Response(Message):
    """ An HTTP response. """

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


    def __init__(self, code, ver=None, headers=None, body=None):
        """ Create an HTTP response.

        code: int -- status code
        ver: HTTPVersion -- HTTPVersion specified by response;
                            defaults to HTTP/1.1
        headers: dict -- headers of the response; defaults to empty dict
        body: str -- body content of the response; defaults to empty str
        """

        assert isinstance(code, int)

        super().__init__(ver, headers, body)
        self.code = code


    def status_message(self):
        return self.STATUS_MESSAGES[self.code]


    def _message_line(self):
        return '{} {} {}'.format(self.ver, self.code, self.status_message())


def guess_content_type(filename):
    """ Return a content-type for a filename based on its suffix.

    This implementation only supports '.html' and '.css' as suffixes.
    """

    if filename.endswith('.html'):
        return 'text/html'
    elif filename.endswith('.css'):
        return 'text/css'
    else:
        return 'text/plain'
