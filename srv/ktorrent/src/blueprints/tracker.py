import struct
import time
import urllib.parse

from flask import Blueprint, request, current_app

from models import User, Torrent, peers
from torrent_utils import bencode

tracker_bp = Blueprint('tracker', __name__)


def _extract_raw_param(raw_query, param_name):
    """
    Extract a raw binary parameter from the query string.
    Flask's request.args corrupts binary data via UTF-8 decoding.
    """
    prefix = (param_name + '=').encode('ascii')
    parts = raw_query.split(b'&')
    for part in parts:
        if part.startswith(prefix):
            raw_value = part[len(prefix):]
            return urllib.parse.unquote_to_bytes(raw_value)
    return None


def _bencode_error(message):
    """Return a bencoded error response."""
    return bencode({b'failure reason': message.encode('utf-8')})


@tracker_bp.route('/announce')
def announce():
    raw_query = request.query_string

    # 1. Extract passkey and resolve user
    passkey = request.args.get('passkey')
    if not passkey:
        return _bencode_error('Missing passkey'), 200, {'Content-Type': 'text/plain'}

    user = User.query.filter_by(passkey=passkey).first()
    if not user:
        return _bencode_error('Invalid passkey'), 200, {'Content-Type': 'text/plain'}

    # 2. Parse info_hash from raw query string
    info_hash_raw = _extract_raw_param(raw_query, 'info_hash')
    if info_hash_raw is None or len(info_hash_raw) != 20:
        return _bencode_error('Invalid info_hash'), 200, {'Content-Type': 'text/plain'}

    info_hash_hex = info_hash_raw.hex()

    # 3. Look up torrent
    torrent = Torrent.query.filter_by(info_hash=info_hash_hex).first()
    if not torrent:
        return _bencode_error('Torrent not found'), 200, {'Content-Type': 'text/plain'}

    # 4. Friendship gate
    if not user.is_friend_of(torrent.uploader):
        return _bencode_error('Friendship required: you must be friends with the uploader'), 200, {'Content-Type': 'text/plain'}

    # 5. Parse remaining parameters
    peer_id_raw = _extract_raw_param(raw_query, 'peer_id')
    if peer_id_raw is None or len(peer_id_raw) != 20:
        return _bencode_error('Invalid peer_id'), 200, {'Content-Type': 'text/plain'}

    try:
        port = int(request.args.get('port', 0))
        uploaded = int(request.args.get('uploaded', 0))
        downloaded = int(request.args.get('downloaded', 0))
        left = int(request.args.get('left', 0))
    except (ValueError, TypeError):
        return _bencode_error('Invalid numeric parameter'), 200, {'Content-Type': 'text/plain'}

    event = request.args.get('event', '')
    compact = request.args.get('compact', '1')
    numwant = min(int(request.args.get('numwant', 50)), 200)

    # Determine peer IP — respect 'ip' param (BEP 3) for the built-in seeder
    explicit_ip = request.args.get('ip')
    if explicit_ip:
        peer_ip = explicit_ip
    else:
        peer_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if peer_ip:
            peer_ip = peer_ip.split(',')[0].strip()

    # 6. Update peer dict
    if info_hash_hex not in peers:
        peers[info_hash_hex] = {}

    torrent_peers = peers[info_hash_hex]
    peer_key = (peer_ip, port)

    if event == 'stopped':
        torrent_peers.pop(peer_key, None)
    else:
        torrent_peers[peer_key] = {
            'peer_id': peer_id_raw,
            'ip': peer_ip,
            'port': port,
            'uploaded': uploaded,
            'downloaded': downloaded,
            'left': left,
            'last_announce': time.time(),
            'user_id': user.id,
        }

    # 7. Prune stale peers
    timeout = current_app.config.get('TRACKER_PEER_TIMEOUT', 120)
    now = time.time()
    stale = [k for k, v in torrent_peers.items() if now - v['last_announce'] > timeout]
    for k in stale:
        del torrent_peers[k]

    # 8. Build peer list (excluding requesting peer)
    interval = current_app.config.get('TRACKER_ANNOUNCE_INTERVAL', 60)
    complete = sum(1 for p in torrent_peers.values() if p['left'] == 0)
    incomplete = sum(1 for p in torrent_peers.values() if p['left'] > 0)

    peer_list = []
    for k, p in torrent_peers.items():
        if k == peer_key:
            continue
        peer_list.append(p)
        if len(peer_list) >= numwant:
            break

    # 9. Build response
    if compact == '1':
        peers_data = b''
        for p in peer_list:
            try:
                ip_parts = p['ip'].split('.')
                ip_bytes = struct.pack('!BBBB', *[int(x) for x in ip_parts])
                port_bytes = struct.pack('!H', p['port'])
                peers_data += ip_bytes + port_bytes
            except (ValueError, struct.error):
                continue

        response = {
            b'interval': interval,
            b'complete': complete,
            b'incomplete': incomplete,
            b'peers': peers_data,
        }
    else:
        peers_list = []
        for p in peer_list:
            peers_list.append({
                b'peer id': p['peer_id'],
                b'ip': p['ip'].encode(),
                b'port': p['port'],
            })
        response = {
            b'interval': interval,
            b'complete': complete,
            b'incomplete': incomplete,
            b'peers': peers_list,
        }

    return bencode(response), 200, {'Content-Type': 'text/plain'}


@tracker_bp.route('/scrape')
def scrape():
    files = {}
    for info_hash_hex, torrent_peers in peers.items():
        info_hash_bytes = bytes.fromhex(info_hash_hex)
        complete = sum(1 for p in torrent_peers.values() if p['left'] == 0)
        incomplete = sum(1 for p in torrent_peers.values() if p['left'] > 0)
        files[info_hash_bytes] = {
            b'complete': complete,
            b'incomplete': incomplete,
            b'downloaded': complete,
        }

    response = {b'files': files}
    return bencode(response), 200, {'Content-Type': 'text/plain'}
