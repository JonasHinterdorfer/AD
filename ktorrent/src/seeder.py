import asyncio
import hashlib
import logging
import math
import os
import random
import struct
import threading
import time
import urllib.parse
import urllib.request

from torrent_utils import bencode

logger = logging.getLogger('seeder')

# Peer ID prefix for KTorrent
PEER_ID_PREFIX = b'-FT0001-'

# Message IDs
MSG_CHOKE = 0
MSG_UNCHOKE = 1
MSG_INTERESTED = 2
MSG_NOT_INTERESTED = 3
MSG_HAVE = 4
MSG_BITFIELD = 5
MSG_REQUEST = 6
MSG_PIECE = 7
MSG_CANCEL = 8

MAX_BLOCK_SIZE = 32 * 1024  # 32KB


def generate_peer_id():
    random_bytes = bytes(random.randint(0, 255) for _ in range(12))
    return PEER_ID_PREFIX + random_bytes


class SeederProtocol:
    """Handles a single peer connection for seeding."""

    def __init__(self, reader, writer, torrents_info, upload_folder, announce_timeout):
        self.reader = reader
        self.writer = writer
        self.torrents_info = torrents_info  # {info_hash_bytes: {filepath, piece_length, file_size, num_pieces}}
        self.upload_folder = upload_folder
        self.announce_timeout = announce_timeout
        self.peer_id = generate_peer_id()
        self.info_hash = None
        self.torrent_info = None
        self.addr = writer.get_extra_info('peername')

    async def handle(self):
        try:
            await self._do_handshake()
            if self.info_hash is None:
                return
            await self._send_bitfield()
            await self._send_unchoke()
            await self._message_loop()
        except (asyncio.IncompleteReadError, ConnectionError, OSError) as e:
            logger.debug(f'Peer {self.addr} disconnected: {e}')
        except Exception as e:
            logger.error(f'Error handling peer {self.addr}: {e}')
        finally:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass

    async def _do_handshake(self):
        """Receive and validate handshake, send response."""
        try:
            data = await asyncio.wait_for(self.reader.readexactly(68), timeout=30)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError):
            logger.debug(f'Handshake timeout/incomplete from {self.addr}')
            return

        if data[0:1] != b'\x13' or data[1:20] != b'BitTorrent protocol':
            logger.debug(f'Invalid handshake protocol from {self.addr}')
            return

        info_hash = data[28:48]
        client_peer_id = data[48:68]

        if info_hash not in self.torrents_info:
            logger.debug(f'Unknown info_hash from {self.addr}: {info_hash.hex()}')
            return

        # Require recent tracker announce for this torrent/peer_id
        try:
            from models import peers as tracker_peers
            torrent_peers = tracker_peers.get(info_hash.hex(), {})
            now = time.time()
            authorized = any(
                p.get('peer_id') == client_peer_id and
                (now - p.get('last_announce', 0)) <= self.announce_timeout
                for p in torrent_peers.values()
            )
            if not authorized:
                logger.debug(f'Unauthorized handshake from {self.addr} for {info_hash.hex()}')
                return
        except Exception as e:
            logger.debug(f'Auth check failed for {self.addr}: {e}')
            return

        self.info_hash = info_hash
        self.torrent_info = self.torrents_info[info_hash]

        # Send handshake response
        response = b'\x13' + b'BitTorrent protocol' + b'\x00' * 8 + info_hash + self.peer_id
        self.writer.write(response)
        await self.writer.drain()
        logger.debug(f'Handshake complete with {self.addr} for {info_hash.hex()}')

    async def _send_bitfield(self):
        """Send bitfield with all pieces available."""
        num_pieces = self.torrent_info['num_pieces']
        num_bytes = math.ceil(num_pieces / 8)
        bitfield = bytearray(num_bytes)

        for i in range(num_pieces):
            byte_index = i // 8
            bit_index = 7 - (i % 8)
            bitfield[byte_index] |= (1 << bit_index)

        msg = struct.pack('!IB', 1 + len(bitfield), MSG_BITFIELD) + bytes(bitfield)
        self.writer.write(msg)
        await self.writer.drain()

    async def _send_unchoke(self):
        """Send unchoke message."""
        msg = struct.pack('!IB', 1, MSG_UNCHOKE)
        self.writer.write(msg)
        await self.writer.drain()

    async def _message_loop(self):
        """Main message processing loop."""
        while True:
            try:
                length_data = await asyncio.wait_for(self.reader.readexactly(4), timeout=120)
            except (asyncio.TimeoutError, asyncio.IncompleteReadError):
                return

            length = struct.unpack('!I', length_data)[0]

            if length == 0:
                # Keep-alive
                continue

            if length > MAX_BLOCK_SIZE + 13 + 100:
                logger.debug(f'Message too large from {self.addr}: {length}')
                return

            try:
                payload = await asyncio.wait_for(self.reader.readexactly(length), timeout=30)
            except (asyncio.TimeoutError, asyncio.IncompleteReadError):
                return

            msg_id = payload[0]

            if msg_id == MSG_REQUEST:
                await self._handle_request(payload[1:])
            elif msg_id == MSG_INTERESTED:
                pass  # Already unchoked
            elif msg_id == MSG_CANCEL:
                pass  # Ignore cancel for simplicity
            # Ignore all other messages

    async def _handle_request(self, payload):
        """Handle a piece request: index(4) + begin(4) + length(4)."""
        if len(payload) != 12:
            return

        index, begin, length = struct.unpack('!III', payload)

        if length > MAX_BLOCK_SIZE:
            logger.debug(f'Rejecting oversized block request: {length}')
            return

        piece_length = self.torrent_info['piece_length']
        file_size = self.torrent_info['file_size']
        filepath = self.torrent_info['filepath']

        file_offset = index * piece_length + begin

        if file_offset >= file_size:
            return

        # Clamp read to file_size
        read_length = min(length, file_size - file_offset)

        try:
            with open(filepath, 'rb') as f:
                f.seek(file_offset)
                block = f.read(read_length)
        except (IOError, OSError) as e:
            logger.error(f'Error reading file for piece {index}: {e}')
            return

        # Send MSG_PIECE: id(1) + index(4) + begin(4) + block
        header = struct.pack('!IB', 9 + len(block), MSG_PIECE)
        piece_header = struct.pack('!II', index, begin)
        self.writer.write(header + piece_header + block)
        await self.writer.drain()


async def _handle_client(reader, writer, torrents_info, upload_folder, announce_timeout):
    protocol = SeederProtocol(reader, writer, torrents_info, upload_folder, announce_timeout)
    await protocol.handle()


async def run_seeder(app):
    """Main async function running the seeder server, announcer, and DB poller."""
    seeder_port = app.config['SEEDER_PORT']
    upload_folder = app.config['UPLOAD_FOLDER']
    announce_timeout = app.config.get('TRACKER_PEER_TIMEOUT', 120)

    # Shared state: {info_hash_bytes: {filepath, piece_length, file_size, num_pieces, passkey}}
    torrents_info = {}

    async def client_handler(reader, writer):
        await _handle_client(reader, writer, torrents_info, upload_folder, announce_timeout)

    server = await asyncio.start_server(client_handler, '0.0.0.0', seeder_port)
    logger.info(f'Seeder listening on port {seeder_port}')

    async def db_poller():
        """Poll DB every 30s to pick up new torrents."""
        while True:
            try:
                with app.app_context():
                    from models import Torrent, User
                    all_torrents = Torrent.query.all()
                    for t in all_torrents:
                        ih_bytes = bytes.fromhex(t.info_hash)
                        if ih_bytes not in torrents_info:
                            filepath = os.path.join(upload_folder, t.filename)
                            if os.path.exists(filepath):
                                uploader = db.session.get(User, t.uploader_id)
                                torrents_info[ih_bytes] = {
                                    'filepath': filepath,
                                    'piece_length': t.piece_length,
                                    'file_size': t.file_size,
                                    'num_pieces': t.num_pieces,
                                    'passkey': uploader.passkey if uploader else '',
                                    'info_hash_hex': t.info_hash,
                                }
                                logger.info(f'Registered torrent for seeding: {t.name} ({t.info_hash})')
            except Exception as e:
                logger.error(f'DB poller error: {e}')
            await asyncio.sleep(30)

    async def announcer():
        """Announce to own tracker periodically for each torrent."""
        peer_id = generate_peer_id()
        while True:
            await asyncio.sleep(55)
            try:
                tracker_port = app.config['TRACKER_PORT']
                seeder_port_val = app.config['SEEDER_PORT']
                seeder_external = app.config.get('SEEDER_EXTERNAL_HOST', '')

                for ih_bytes, info in list(torrents_info.items()):
                    passkey = info.get('passkey', '')
                    if not passkey:
                        continue

                    # URL-encode the raw info_hash bytes
                    info_hash_encoded = urllib.parse.quote(ih_bytes, safe='')
                    peer_id_encoded = urllib.parse.quote(peer_id, safe='')

                    ip_param = f'&ip={seeder_external}' if seeder_external else ''
                    announce_url = (
                        f'http://127.0.0.1:{tracker_port}/announce'
                        f'?passkey={passkey}'
                        f'&info_hash={info_hash_encoded}'
                        f'&peer_id={peer_id_encoded}'
                        f'&port={seeder_port_val}'
                        f'&uploaded=0&downloaded=0&left=0'
                        f'&event=started&compact=1'
                        f'{ip_param}'
                    )

                    try:
                        req = urllib.request.Request(announce_url)
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            resp.read()
                        logger.debug(f'Announced as seeder for {info["info_hash_hex"]}')
                    except Exception as e:
                        logger.debug(f'Announce failed for {info["info_hash_hex"]}: {e}')
            except Exception as e:
                logger.error(f'Announcer error: {e}')

    from extensions import db

    async with server:
        await asyncio.gather(
            server.serve_forever(),
            db_poller(),
            announcer(),
        )


def start_seeder_thread(app):
    """Start the seeder in a background daemon thread."""
    logging.basicConfig(level=logging.INFO)
    logger.setLevel(logging.INFO)

    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_seeder(app))
        except Exception as e:
            logger.error(f'Seeder thread error: {e}')

    thread = threading.Thread(target=run, daemon=True, name='seeder-thread')
    thread.start()
    logger.info('Seeder thread started')
