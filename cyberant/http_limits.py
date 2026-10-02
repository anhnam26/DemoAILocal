"""ASGI request body limit, including chunked requests without Content-Length."""
from starlette.responses import PlainTextResponse


class BodyTooLarge(Exception):
    pass


class BodyLimitMiddleware:
    def __init__(self, app, limit=2_100_000):
        self.app=app
        self.limit=limit

    async def __call__(self, scope, receive, send):
        if scope['type']!='http':
            return await self.app(scope,receive,send)
        total=0
        started=False

        async def limited_receive():
            nonlocal total
            message=await receive()
            if message['type']=='http.request':
                total+=len(message.get('body',b''))
                if total>self.limit:raise BodyTooLarge()
            return message

        async def tracked_send(message):
            nonlocal started
            if message['type']=='http.response.start':started=True
            await send(message)

        try:
            await self.app(scope,limited_receive,tracked_send)
        except BodyTooLarge:
            if started:raise
            response=PlainTextResponse('Request too large',413)
            await response(scope,receive,send)