import asyncio
from queue import Queue
from threading import Thread

from EdgeGPT.EdgeGPT import Chatbot, ConversationStyle


class DelegateChat(object):

    def __init__(self):
        self.chat_bot = None

    def clear(self):
        self.chat_bot = None


class ChatThread(Thread):

    def __init__(self, chat_send_message: str):
        super().__init__()
        self.current_message = None
        self.chat_send_message = chat_send_message
        self.chat_bot = None
        if DELEGATE_CHAT.chat_bot is not None:
            self.chat_bot = DELEGATE_CHAT.chat_bot

    def run(self) -> None:
        chat_response = ""

        async def send_chat_async():
            nonlocal chat_response
            if self.chat_bot is None:
                bot = await Chatbot.create()
                response = await bot.ask(prompt=self.chat_send_message, conversation_style=ConversationStyle.creative)
                chat_response = response
            else:
                response = await self.chat_bot.ask(prompt=self.chat_send_message,
                                                   conversation_style=ConversationStyle.creative)
                chat_response = response

        asyncio.run(send_chat_async())
        self.current_message = chat_response
        MESSAGE_QUEUE.put(self.current_message)
        print(self.current_message)
        DELEGATE_CHAT.chat_bot = self.chat_bot


MESSAGE_QUEUE = Queue()
DELEGATE_CHAT = DelegateChat()
