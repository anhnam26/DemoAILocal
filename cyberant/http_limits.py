"""ASGI request body limit, including chunked requests without Content-Length."""
import re
from starlette.responses import PlainTextResponse


class BodyLimitMiddleware:
    def __init__(self, app, limit=2_100_000):
        self.app=app
        self.limit=limit

    async def __call__(self, scope, receive, send):
        if scope['type']!='http':
            return await self.app(scope,receive,send)
        limit=10_100_000 if re.fullmatch(r'/api/conversations/[a-f0-9]{24}/attachments',scope.get('path','')) else self.limit
        # Validate BEFORE framework body parsing/side effects. Raising from receive
        # inside FastAPI can otherwise be converted to 400 by its JSON parser.
        body=bytearray()
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            body.extend(message.get('body',b''))
            if len(body)>limit:
                await PlainTextResponse('Request too large',413)(scope,receive,send)
                return
            if not message.get('more_body',False):break
        delivered=False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered=True
                return {'type':'http.request','body':bytes(body),'more_body':False}
            return await receive()

        await self.app(scope,replay,send)