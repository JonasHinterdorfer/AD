import hashlib
import math
import os
from datetime import datetime, timezone


def bencode(obj):
    """Bencode a Python object. Supports int, bytes, str, list, dict."""
    if isinstance(obj, int):
        return b'i' + str(obj).encode() + b'e'
    elif isinstance(obj, bytes):
        return str(len(obj)).encode() + b':' + obj
    elif isinstance(obj, str):
        encoded = obj.encode('utf-8')
        return str(len(encoded)).encode() + b':' + encoded
    elif isinstance(obj, list):
        return b'l' + b''.join(bencode(item) for item in obj) + b'e'
    elif isinstance(obj, dict):
        items = sorted(obj.items(), key=lambda kv: kv[0] if isinstance(kv[0], bytes) else kv[0].encode('utf-8'))
        result = b'd'
        for k, v in items:
            if isinstance(k, str):
                k = k.encode('utf-8')
            result += bencode(k) + bencode(v)
        result += b'e'
        return result
    else:
        raise TypeError(f'Cannot bencode {type(obj)}')


def bdecode(data):
    """Decode bencoded data. Returns (decoded_object, remaining_data)."""
    if isinstance(data, (str, memoryview)):
        data = bytes(data) if isinstance(data, memoryview) else data.encode('utf-8')
    result, _ = _bdecode(data, 0)
    return result


def _bdecode(data, index):
    """Recursive descent bencoding parser. Keys stay as bytes."""
    if index >= len(data):
        raise ValueError('Unexpected end of data')

    char = data[index:index + 1]

    if char == b'i':
        # Integer
        end = data.index(b'e', index + 1)
        return int(data[index + 1:end]), end + 1

    elif char == b'l':
        # List
        result = []
        index += 1
        while data[index:index + 1] != b'e':
            item, index = _bdecode(data, index)
            result.append(item)
        return result, index + 1

    elif char == b'd':
        # Dict — keys stay as bytes
        result = {}
        index += 1
        while data[index:index + 1] != b'e':
            key, index = _bdecode(data, index)
            value, index = _bdecode(data, index)
            result[key] = value
        return result, index + 1

    elif char.isdigit():
        # Byte string
        colon = data.index(b':', index)
        length = int(data[index:colon])
        start = colon + 1
        return data[start:start + length], start + length

    else:
        raise ValueError(f'Invalid bencode data at index {index}: {char!r}')


def create_torrent(filepath, tracker_url, piece_length=None):
    """
    Create a .torrent file from a regular file.
    Returns (info_hash_hex, torrent_bytes, num_pieces, piece_length).
    """
    file_size = os.path.getsize(filepath)
    filename = os.path.basename(filepath)

    # Auto-select piece length
    if piece_length is None:
        if file_size < 50 * 1024 * 1024:
            piece_length = 256 * 1024  # 256KB
        elif file_size < 500 * 1024 * 1024:
            piece_length = 512 * 1024  # 512KB
        else:
            piece_length = 1024 * 1024  # 1MB

    # Read file and compute piece hashes
    pieces = b''
    num_pieces = 0
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(piece_length)
            if not chunk:
                break
            pieces += hashlib.sha1(chunk).digest()
            num_pieces += 1

    if num_pieces == 0:
        # Empty file edge case
        num_pieces = 1
        pieces = hashlib.sha1(b'').digest()

    # Build info dict with bytes keys (critical for correct info_hash)
    info = {
        b'name': filename.encode('utf-8'),
        b'piece length': piece_length,
        b'pieces': pieces,
        b'length': file_size,
        b'private': 1,
    }

    # Compute info_hash
    info_bencoded = bencode(info)
    info_hash = hashlib.sha1(info_bencoded).hexdigest()

    # Build full torrent dict
    torrent = {
        b'announce': tracker_url.encode('utf-8'),
        b'info': info,
        b'creation date': int(datetime.now(timezone.utc).timestamp()),
        b'created by': b'KTorrent/0.1',
    }

    torrent_bytes = bencode(torrent)
    return info_hash, torrent_bytes, num_pieces, piece_length


def personalize_torrent(torrent_bytes, passkey):
    """
    Rewrite announce URL to include the user's passkey.
    Info dict is untouched so info_hash stays the same.
    """
    torrent = bdecode(torrent_bytes)
    announce = torrent[b'announce']
    if isinstance(announce, bytes):
        announce = announce.decode('utf-8')

    # Replace or append passkey parameter
    if '?passkey=' in announce:
        base = announce.split('?passkey=')[0]
        announce = f'{base}?passkey={passkey}'
    elif '?' in announce:
        announce = f'{announce}&passkey={passkey}'
    else:
        announce = f'{announce}?passkey={passkey}'

    torrent[b'announce'] = announce.encode('utf-8')
    return bencode(torrent)


def parse_torrent(data):
    """Decode torrent and extract metadata."""
    torrent = bdecode(data)
    info = torrent.get(b'info', {})
    return {
        'announce': torrent.get(b'announce', b'').decode('utf-8', errors='replace'),
        'name': info.get(b'name', b'').decode('utf-8', errors='replace'),
        'piece_length': info.get(b'piece length', 0),
        'length': info.get(b'length', 0),
        'private': info.get(b'private', 0),
    }


def human_size(size_bytes):
    """Convert bytes to human-readable size string."""
    if size_bytes is None:
        return '0 B'
    if size_bytes == 0:
        return '0 B'
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    if i == 0:
        return f'{int(size)} B'
    return f'{size:.1f} {units[i]}'


def time_ago(dt):
    """Convert datetime to human-readable 'time ago' string."""
    if dt is None:
        return 'never'
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return 'just now'
    minutes = seconds // 60
    if minutes < 60:
        return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
    hours = minutes // 60
    if hours < 24:
        return f'{hours} hour{"s" if hours != 1 else ""} ago'
    days = hours // 24
    if days < 30:
        return f'{days} day{"s" if days != 1 else ""} ago'
    months = days // 30
    if months < 12:
        return f'{months} month{"s" if months != 1 else ""} ago'
    years = days // 365
    return f'{years} year{"s" if years != 1 else ""} ago'
