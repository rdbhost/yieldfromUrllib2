
import sys
import ssl
import asyncio
import socket

sys.path.insert(1, '..')

from yieldfrom.urllib import request

sslContext = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)



@asyncio.coroutine
def get_py():
    print('start')
    resp = yield from request.urlopen('http://httpbin.org', context=sslContext, timeout=5)
    #resp = yield from request.urlopen('https://www.rdbhost.com', context=sslContext, timeout=5)
    #print('eof ', resp.fp.at_eof(), file=sys.stderr)

    try:
        pg = yield from resp.read()
    except Exception as e:
        print('eof1 ', resp.fp, file=sys.stderr)
        raise
    print(pg.decode('utf-8'))
    return pg


loop = asyncio.get_event_loop()
loop.set_debug(True)

loop.run_until_complete(get_py())
