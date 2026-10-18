import asyncio
from cryptography.hazmat.primitives.asymmetric import x25519
from gossipmesh.crypto.noise import NoiseHandshakeState


class SecureTransport:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, priv_key: x25519.X25519PrivateKey, is_initiator: bool):
        self.reader = reader
        self.writer = writer
        self.state = NoiseHandshakeState(is_initiator, priv_key)
        self.transport_key = None

    async def handshake(self):
        if self.state.is_initiator:
            msg1 = self.state.write_message_1()
            self.writer.write(len(msg1).to_bytes(2, "big") + msg1)
            await self.writer.drain()
            
            len_bytes = await self.reader.readexactly(2)
            msg2 = await self.reader.readexactly(int.from_bytes(len_bytes, "big"))
            self.state.read_message_2(msg2)
            
            msg3 = self.state.write_message_3()
            self.writer.write(len(msg3).to_bytes(2, "big") + msg3)
            await self.writer.drain()
        else:
            len_bytes = await self.reader.readexactly(2)
            msg1 = await self.reader.readexactly(int.from_bytes(len_bytes, "big"))
            self.state.read_message_1(msg1)
            
            msg2 = self.state.write_message_2()
            self.writer.write(len(msg2).to_bytes(2, "big") + msg2)
            await self.writer.drain()
            
            len_bytes = await self.reader.readexactly(2)
            msg3 = await self.reader.readexactly(int.from_bytes(len_bytes, "big"))
            self.state.read_message_3(msg3)
        
        self.transport_key = self.state.key

    async def send(self, data: bytes):
        ciphertext = self.state.encrypt_and_hash(data)
        self.writer.write(len(ciphertext).to_bytes(4, "big") + ciphertext)
        await self.writer.drain()

    async def recv(self) -> bytes:
        len_bytes = await self.reader.readexactly(4)
        ciphertext = await self.reader.readexactly(int.from_bytes(len_bytes, "big"))
        return self.state.decrypt_and_hash(ciphertext)
