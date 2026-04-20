from Crypto.Cipher import AES
from Crypto.Util.number import long_to_bytes, bytes_to_long, getPrime
from hashlib import sha256
from Crypto.Util.Padding import pad
import random
import subprocess
import json
import secrets


GLOBAL_M = 2**19 - 1
GLOBAL_A = random.randint(1, 2**19) 
GLOBAL_C = random.randint(1, 2**19)

def LCG():
    seed = random.randint(0, GLOBAL_M - 1)
    
    def randfunc(num_bytes):
        nonlocal seed 
        
        result = bytearray()
        while len(result) < num_bytes:
            seed = (GLOBAL_A * seed + GLOBAL_C) % GLOBAL_M

            # we have custom LCG at home, custom LCG at home:
            expanded = (seed * 0x85ebca6b) % (2**32)

            result.extend(expanded.to_bytes(4, 'big'))
            
        return bytes(result[:num_bytes])
        
    return randfunc


def rsa_encrypt(msg):
    e = 65537

    p = getPrime(1024)
    q = getPrime(1024)

    n = p * q
    phi = (p - 1) * (q - 1)
    d = pow(e, -1, phi)

    ciphertext = pow(bytes_to_long(msg.encode()), e, n)

    data = {
        "ciphertext": long_to_bytes(ciphertext).hex(),
        "n": n
    }

    data = json.dumps(data)

    return data


def aes_encrypt(msg, key):
    nonce = secrets.token_bytes(8)
    aes = AES.new(key, AES.MODE_CTR, nonce=nonce)
    ciphertext = aes.encrypt(pad(msg.encode(), 16)).hex()
    return f"{nonce.hex()}:{ciphertext}"


def ecc_encrypt(msg):
    result = subprocess.check_output(['sage', 'curve_gen.sage.py'], text=True)
    result = json.loads(result)
    
    p = result["p"]
    G = result["G"]
    private_key = result["private_key"]
    public_key = result["public_key"]

    key = sha256(int(private_key).to_bytes(32, 'big')).digest()[:16]
    iv = secrets.token_bytes(16)
    aes = AES.new(key, AES.MODE_CBC, iv)
    ct = aes.encrypt(pad(msg.encode(), 16))

    data = {
        "ciphertext": ct.hex(),
        "iv": iv.hex(),
        "p": int(p),
        "G": (int(G[0]), int(G[1])),
        "public_key": (int(public_key[0]), int(public_key[1]))
    }

    data = json.dumps(data)

    return data


def otp_encrypt(msg):
    key = secrets.token_bytes(len(msg))
    with open("otp_keys", "a") as f:
        f.write(key.hex()+"\n")

    ciphertext = bytes([m ^ k for m, k in zip(msg.encode(), key)])

    return ciphertext.hex()


def fallback_encrypt(msg):
    enc = ""
    for char in msg:
        enc += sha256(char.encode()).hexdigest()[:4]

    return enc
