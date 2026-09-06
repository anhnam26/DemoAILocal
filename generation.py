"""Bounded concurrent inference with an exclusive maintenance gate."""
import asyncio
from fastapi import HTTPException

class GenerationGate:
    def __init__(self):
        self.active=0;self.waiting=0;self.maintenance=False
    def locked(self):return self.active>0 or self.waiting>0 or self.maintenance
    async def acquire(self):
        # Maintenance never interrupts accepted requests.
        if self.locked():raise HTTPException(409,'Có câu hỏi đang xử lý hoặc chờ; hãy đợi trước khi điều khiển model.')
        self.maintenance=True
    def release(self):self.maintenance=False
    async def enter(self,capacity):
        if self.maintenance:raise HTTPException(503,'Model đang được quản trị khởi động lại. Vui lòng thử lại sau.')
        if self.waiting>=16:raise HTTPException(429,'Hàng chờ đã đầy (16 yêu cầu). Vui lòng thử lại sau.')
        self.waiting+=1
        try:
            async with asyncio.timeout(180):
                while self.active>=capacity:await asyncio.sleep(.05)
                self.active+=1
        except TimeoutError:raise HTTPException(429,'Đã chờ 180 giây. Vui lòng gửi lại câu hỏi.')
        finally:self.waiting-=1
    def leave(self):self.active-=1
    def status(self):return dict(active=self.active,waiting=self.waiting,maintenance=self.maintenance,queue_limit=16)
