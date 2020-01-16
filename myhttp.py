
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
        return f'HTTP/{self.major}.{self.minor}'


    def __repr__(self):
        return f'HTTPVersion({self.major}, {self.minor})'


class Message:
    """ Abstract class for functionality shared
        between Request and Response.
    """

    def __init__(self, ver=None, headers=None, body=None):
        """ Initialize data shared between request and response.

        ver: HTTPVersion -- HTTPVersion specified by response;
                            defaults to HTTP/1.1
        headers: dict -- headers of the response; defaults to empty dict
        body: str -- body content of the response; defaults to empty str
        """

        assert ver is None or isinstance(ver, HTTPVersion)
        assert headers is None or isinstance(headers, dict)
        assert body is None or isinstance(body, str)

        self.ver = ver or HTTPVersion(1, 1)
        self.headers = headers or dict()
        self.body = body or ''


    def _message_line(self):
        """ Generates the "message line": the first line of the message.

        Must be implemented by concrete subclasses.
        """
        raise NotImplementedError()


    def __str__(self):
        return (self._message_line() + '\n'
                + '\n'.join(f'{k}: {v}' for k, v in self.headers.items())
                + '\n\n'
                + self.body)


class Request(Message):
    """ An HTTP request. """

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
        return f'{self.method} {self.path} {self.ver}'


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
        return f'{self.ver} {self.code} {self.status_message()}'


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
