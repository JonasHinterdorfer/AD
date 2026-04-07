import json
import sys
import os

found = False
while found != True:
    p = random_prime(2**64)

    a = randint(1, p-1)
    b = randint(1, p-1)

    try:
        E = EllipticCurve(GF(p), [a, b])
        G = E.gens()[0]
        n = G.order()

        private_key = randint(1, n-1)
        public_key = private_key * G
        
        data = {
            "p": int(p),
            "G": (int(G[0]), int(G[1])),
            "private_key": int(private_key),
            "public_key": (int(public_key[0]), int(public_key[1])),
        }

        print(json.dumps(data))
        found = True
    except Exception as e:
        pass
