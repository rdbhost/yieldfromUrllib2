import unittest
from test import support
from test.test_urllib2 import sanepathname2url

import os
import socket
import sys
import asyncio
import functools
try:
    import ssl
except ImportError:
    ssl = None

sys.path.insert(0, '../yieldfrom/urllib')
import error
import request

sys.path.append('.')
import testtcpserver as server
from testtcpserver import RECEIVE, TestingSocket

from test import support
support.use_resources = ['network']


CONNECT = ('127.0.0.1', 2222)
testLoop = asyncio.get_event_loop()

def open_socket_conn(host='127.0.0.1', port=2222):
    """  """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    sock.connect((host, port))
    return sock

def _prep_server(body, prime=False, reader=None):
    commands = []
    if type(body) == type([]):
        commands.extend(body)
    else:
        commands.extend([RECEIVE, body])
    srvr = server.AsyncioCommandServer(commands, testLoop if reader else None, reader, *CONNECT, verbose=False)
    if prime:
        sock = open_socket_conn(*CONNECT)
        sock.sendall(b' ')
        return srvr, sock
    else:
        return srvr, None

def _run_with_server_pre(f, body='', srvr=None, sock=None):
    try:
        if srvr is None:
            srvr, sock = _prep_server(body, prime=True)
        testLoop.run_until_complete(f(sock))
    except:
        raise
    finally:
        srvr.stop()

def _run_with_server(f, body='', srvr=None):
    if srvr is None:
        srvr, _j = _prep_server(body)
    testLoop.run_until_complete(f(*CONNECT))
    srvr.stop()

def async_test(f):

    testLoop = asyncio.get_event_loop()

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        testLoop.run_until_complete(future)
    return wrapper

async_test.__test__ = False # not a test


support.requires("network")

TIMEOUT = 60  # seconds


def _retry_thrice(func, exc, *args, **kwargs):
    for i in range(3):
        try:
            return func(*args, **kwargs)
        except exc as e:
            last_exc = e
            continue
        except:
            raise
    raise last_exc

def _wrap_with_retry_thrice(func, exc):
    @asyncio.coroutine
    def wrapped(*args, **kwargs):
        r = yield from _retry_thrice(func, exc, *args, **kwargs)
        return r
    return wrapped

# Connecting to remote hosts is flaky.  Make it more robust by retrying
# the connection several times.
_urlopen_with_retry = _wrap_with_retry_thrice(request.urlopen,
                                              error.URLError)


class AuthTests(unittest.TestCase):
    """Tests urllib2 authentication features."""

## Disabled at the moment since there is no page under python.org which
## could be used to HTTP authentication.
#
#    def test_basic_auth(self):
#        import http.client
#
#        test_url = "http://www.python.org/test/test_urllib2/basic_auth"
#        test_hostport = "www.python.org"
#        test_realm = 'Test Realm'
#        test_user = 'test.test_urllib2net'
#        test_password = 'blah'
#
#        # failure
#        try:
#            _urlopen_with_retry(test_url)
#        except urllib2.HTTPError, exc:
#            self.assertEqual(exc.code, 401)
#        else:
#            self.fail("urlopen() should have failed with 401")
#
#        # success
#        auth_handler = urllib2.HTTPBasicAuthHandler()
#        auth_handler.add_password(test_realm, test_hostport,
#                                  test_user, test_password)
#        opener = urllib2.build_opener(auth_handler)
#        f = opener.open('http://localhost/')
#        response = _urlopen_with_retry("http://www.python.org/")
#
#        # The 'userinfo' URL component is deprecated by RFC 3986 for security
#        # reasons, let's not implement it!  (it's already implemented for proxy
#        # specification strings (that is, URLs or authorities specifying a
#        # proxy), so we must keep that)
#        self.assertRaises(http.client.InvalidURL,
#                          urllib2.urlopen, "http://evil:thing@example.com")


class CloseSocketTest(unittest.TestCase):

    @async_test
    def tst_close(self):
        # calling .close() on urllib2's response objects should close the
        # underlying socket
        url = "http://www.example.com/"
        with support.transient_internet(url):
            response = yield from _urlopen_with_retry(url)
            sock = response.fp
            self.assertFalse(sock.at_eof())
            response.close()
            self.assertTrue(sock.at_eof())

class OtherNetworkTests(unittest.TestCase):

    @asyncio.coroutine
    def aioAssertRaises(self, exc, f, *args, **kwargs):
        """tests a coroutine for whether it raises given error."""
        try:
            yield from f(*args, **kwargs)
        except exc as e:
            pass
        else:
            raise Exception('expected %s not raised' % exc.__name__)


    def setUp(self):
        if 0:  # for debugging
            import logging
            logger = logging.getLogger("test_urllib2net")
            logger.addHandler(logging.StreamHandler())

    # XXX The rest of these tests aren't very good -- they don't check much.
    # They do sometimes catch some major disasters, though.

    def test_ftp(self):
        urls = [
            'ftp://ftp.debian.org/debian/README',
            ('ftp://ftp.debian.org/debian/non-existent-file',
             None, error.URLError),
            'ftp://gatekeeper.research.compaq.com/pub/DEC/SRC'
                '/research-reports/00README-Legal-Rules-Regs',
            ]
        self._test_urls(urls, self._extra_handlers())

    def test_file(self):
        TESTFN = support.TESTFN
        f = open(TESTFN, 'w')
        try:
            f.write('hi there\n')
            f.close()
            urls = [
                'file:' + sanepathname2url(os.path.abspath(TESTFN)),
                ('file:///nonsensename/etc/passwd', None,
                 error.URLError),
                ]
            self._test_urls(urls, self._extra_handlers(), retry=True)
        finally:
            os.remove(TESTFN)

        self.aioAssertRaises(ValueError, request.urlopen,'./relative_path/to/file')

    # XXX Following test depends on machine configurations that are internal
    # to CNRI.  Need to set up a public server with the right authentication
    # configuration for test purposes.

##     def test_cnri(self):
##         if socket.gethostname() == 'bitdiddle':
##             localhost = 'bitdiddle.cnri.reston.va.us'
##         elif socket.gethostname() == 'bitdiddle.concentric.net':
##             localhost = 'localhost'
##         else:
##             localhost = None
##         if localhost is not None:
##             urls = [
##                 'file://%s/etc/passwd' % localhost,
##                 'http://%s/simple/' % localhost,
##                 'http://%s/digest/' % localhost,
##                 'http://%s/not/found.h' % localhost,
##                 ]

##             bauth = HTTPBasicAuthHandler()
##             bauth.add_password('basic_test_realm', localhost, 'jhylton',
##                                'password')
##             dauth = HTTPDigestAuthHandler()
##             dauth.add_password('digest_test_realm', localhost, 'jhylton',
##                                'password')

##             self._test_urls(urls, self._extra_handlers()+[bauth, dauth])

    @async_test
    def test_urlwithfrag(self):
        urlwith_frag = "https://docs.python.org/2/glossary.html#glossary"
        with support.transient_internet(urlwith_frag):
            req = request.Request(urlwith_frag)
            res = yield from request.urlopen(req)
            self.assertEqual(res.geturl(),
                    "https://docs.python.org/2/glossary.html#glossary")

    @async_test
    def test_redirect_url_withfrag(self):
        redirect_url_with_frag = "http://bit.ly/1iSHToT"
        with support.transient_internet(redirect_url_with_frag):
            req = request.Request(redirect_url_with_frag)
            res = yield from request.urlopen(req)
            self.assertEqual(res.geturl(),
                    "https://docs.python.org/3.4/glossary.html#term-global-interpreter-lock")

    @async_test
    def test_custom_headers(self):
        url = "http://www.example.com"
        with support.transient_internet(url):
            opener = request.build_opener()
            req = request.Request(url)
            self.assertFalse(req.header_items())
            yield from opener.open(req)
            self.assertTrue(req.header_items())
            self.assertTrue(req.has_header('User-agent'))
            req.add_header('User-Agent','Test-Agent')
            yield from opener.open(req)
            self.assertEqual(req.get_header('User-agent'),'Test-Agent')

    @async_test
    def test_sites_no_connection_close(self):
        # Some sites do not send Connection: close header.
        # Verify that those work properly. (#issue12576)

        URL = 'http://www.imdb.com' # mangles Connection:close

        with support.transient_internet(URL):
            try:
                res = yield from request.urlopen(URL)
                pass
            except ValueError as e:
                self.fail("urlopen failed for site not sending \
                           Connection:close")
            else:
                self.assertTrue(res)

            req = yield from request.urlopen(URL)
            res = yield from req.read()
            self.assertTrue(res)

    def _test_urls(self, urls, handlers, retry=True):
        import time
        import logging
        debug = logging.getLogger("test_urllib2").debug

        urlopen = request.build_opener(*handlers).open
        if retry:
            urlopen = yield from _wrap_with_retry_thrice(urlopen, error.URLError)

        for url in urls:
            with self.subTest(url=url):
                if isinstance(url, tuple):
                    url, req, expected_err = url
                else:
                    req = expected_err = None

                with support.transient_internet(url):
                    try:
                        f = yield from urlopen(url, req, TIMEOUT)
                    except OSError as err:
                        if expected_err:
                            msg = ("Didn't get expected error(s) %s for %s %s, got %s: %s" %
                                   (expected_err, url, req, type(err), err))
                            self.assertIsInstance(err, expected_err, msg)
                        else:
                            raise
                    except error.URLError as err:
                        if isinstance(err[0], socket.timeout):
                            print("<timeout: %s>" % url, file=sys.stderr)
                            continue
                        else:
                            raise
                    else:
                        try:
                            with support.time_out, \
                                 support.socket_peer_reset, \
                                 support.ioerror_peer_reset:
                                buf = yield from f.read()
                                debug("read %d bytes" % len(buf))
                        except socket.timeout:
                            print("<timeout: %s>" % url, file=sys.stderr)
                        f.close()
                time.sleep(0.1)

    def _extra_handlers(self):
        handlers = []

        cfh = request.CacheFTPHandler()
        self.addCleanup(cfh.clear_cache)
        cfh.setTimeout(1)
        handlers.append(cfh)

        return handlers


class TimeoutTest(unittest.TestCase):

    @async_test
    def test_http_basic(self):
        self.assertIsNone(socket.getdefaulttimeout())
        url = "http://www.example.com"
        with support.transient_internet(url, timeout=None):
            u = yield from _urlopen_with_retry(url)
            self.addCleanup(u.close)
            #self.assertIsNone(u.fp.raw._sock.gettimeout())

    @async_test
    def tst_http_default_timeout(self):
        self.assertIsNone(socket.getdefaulttimeout())
        url = "http://www.example.com"
        with support.transient_internet(url):
            socket.setdefaulttimeout(60)
            try:
                u = yield from _urlopen_with_retry(url)
                self.addCleanup(u.close)
            finally:
                socket.setdefaulttimeout(None)
            self.assertEqual(u.fp.raw._sock.gettimeout(), 60)

    @async_test
    def tst_http_no_timeout(self):
        self.assertIsNone(socket.getdefaulttimeout())
        url = "http://www.example.com"
        with support.transient_internet(url):
            socket.setdefaulttimeout(60)
            try:
                u = yield from _urlopen_with_retry(url, timeout=None)
                self.addCleanup(u.close)
            finally:
                socket.setdefaulttimeout(None)
            self.assertIsNone(u.fp.raw._sock.gettimeout())

    @async_test
    def tst_http_timeout(self):
        url = "http://www.example.com"
        with support.transient_internet(url):
            u = yield from _urlopen_with_retry(url, timeout=120)
            self.addCleanup(u.close)
            self.assertEqual(u.fp.raw._sock.gettimeout(), 120)

    FTP_HOST = "ftp://ftp.mirror.nl/pub/gnu/"

    @async_test
    def test_ftp_basic(self):
        self.assertIsNone(socket.getdefaulttimeout())
        with support.transient_internet(self.FTP_HOST, timeout=None):
            u = yield from _urlopen_with_retry(self.FTP_HOST)
            self.addCleanup(u.close)
            self.assertIsNone(u.fp.fp.raw._sock.gettimeout())

    @async_test
    def tst_ftp_default_timeout(self):
        self.assertIsNone(socket.getdefaulttimeout())
        with support.transient_internet(self.FTP_HOST):
            socket.setdefaulttimeout(60)
            try:
                u = yield from _urlopen_with_retry(self.FTP_HOST)
                self.addCleanup(u.close)
            finally:
                socket.setdefaulttimeout(None)
            self.assertEqual(u.fp.fp.raw._sock.gettimeout(), 60)

    @async_test
    def tst_ftp_no_timeout(self):
        self.assertIsNone(socket.getdefaulttimeout())
        with support.transient_internet(self.FTP_HOST):
            socket.setdefaulttimeout(60)
            try:
                u = yield from _urlopen_with_retry(self.FTP_HOST, timeout=None)
                self.addCleanup(u.close)
            finally:
                socket.setdefaulttimeout(None)
            self.assertIsNone(u.fp.fp.raw._sock.gettimeout())

    @async_test
    def tst_ftp_timeout(self):
        with support.transient_internet(self.FTP_HOST):
            u = yield from _urlopen_with_retry(self.FTP_HOST, timeout=60)
            self.addCleanup(u.close)
            self.assertEqual(u.fp.fp.raw._sock.gettimeout(), 60)


if __name__ == "__main__":
    unittest.main()
