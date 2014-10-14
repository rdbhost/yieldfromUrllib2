
import sys
import ssl
import asyncio
import socket

sys.path.insert(1, '..')
import request

#socket.setblocking(False)
sslContext = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)



@asyncio.coroutine
def get_py():
    print('start')
    resp = yield from request.urlopen('http://httpbin.org') #, context=sslContext, timeout=1)
    print('have resp %s' % len(resp.fp._buffer))
    pg = yield from resp.read()
    print(pg.decode('utf-8'))
    return pg


loop = asyncio.get_event_loop()
loop.set_debug(True)

loop.run_until_complete(get_py())
