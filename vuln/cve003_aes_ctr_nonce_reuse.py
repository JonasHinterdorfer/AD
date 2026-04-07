#!/usr/bin/env python3
# Given two AES-CTR ciphertexts from same key+nonce, xor(ct1, ct2)=xor(pt1, pt2)
import binascii

c1 = bytes.fromhex(input('ct1 hex: ').strip())
c2 = bytes.fromhex(input('ct2 hex: ').strip())
x = bytes(a ^ b for a, b in zip(c1, c2))
print('[+] ct1^ct2:', x.hex())
print('[*] If one plaintext is known, recover keystream and decrypt the other.')
known = input('known plaintext for ct1 (optional): ')
if known:
    ks = bytes(a ^ b for a, b in zip(c1, known.encode()))
    p2 = bytes(a ^ b for a, b in zip(c2, ks))
    print('[+] recovered pt2:', p2.decode(errors='replace'))
