import asyncio
from queue import Queue
from threading import Thread
from re_edge_gpt import ImageGenAsync


class ImageGenThread(Thread):

    def __init__(self, image_keyword: str):
        super().__init__()
        auth_cooker = open("bing_cookies.txt", "r+").read()
        self.async_gen = ImageGenAsync(auth_cookie=auth_cooker)
        self.image_keyword = image_keyword

    def run(self) -> None:
        try:
            image_list = list()

            async def send_chat_async():
                nonlocal image_list
                image_list = await self.async_gen.get_images(self.image_keyword)

            asyncio.run(send_chat_async())
            for image in image_list:
                IMAGE_QUEUE.put_nowait(image)
        except Exception as error:
            EXCEPTION_QUEUE.put_nowait(repr(error))
            raise error


IMAGE_QUEUE = Queue()
EXCEPTION_QUEUE = Queue()
