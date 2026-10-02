import asyncio
import unittest
from cyberant.http_limits import BodyLimitMiddleware


class BodyLimitTests(unittest.TestCase):
    def test_chunked_body_without_content_length(self):
        async def run():
            async def app(scope,receive,send):
                while True:
                    message=await receive()
                    if not message.get('more_body'):break
                await send({'type':'http.response.start','status':200,'headers':[]})
                await send({'type':'http.response.body','body':b'ok'})
            messages=iter([{'type':'http.request','body':b'123','more_body':True},
                           {'type':'http.request','body':b'456','more_body':False}])
            async def receive():return next(messages)
            result=[]
            async def send(message):result.append(message)
            await BodyLimitMiddleware(app,limit=5)({'type':'http'},receive,send)
            self.assertEqual(result[0]['status'],413)
        asyncio.run(run())