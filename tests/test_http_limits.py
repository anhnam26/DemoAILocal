import asyncio
import unittest
from cyberant.http_limits import BodyLimitMiddleware


class BodyLimitTests(unittest.TestCase):
    def test_attachment_limit_is_endpoint_scoped(self):
        async def run(path):
            result=[];called=[]
            async def app(scope,receive,send):
                called.append(len((await receive())['body']))
                await send({'type':'http.response.start','status':200,'headers':[]})
                await send({'type':'http.response.body','body':b'ok'})
            async def receive():return {'type':'http.request','body':b'x'*2_200_000,'more_body':False}
            async def send(m):result.append(m)
            await BodyLimitMiddleware(app)({'type':'http','path':path},receive,send)
            return result[0]['status'],called
        self.assertEqual(asyncio.run(run('/api/chat'))[0],413)
        self.assertEqual(asyncio.run(run('/api/conversations/'+'a'*24+'/attachments'))[0],200)

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