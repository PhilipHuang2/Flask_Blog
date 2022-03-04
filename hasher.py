import os
import hashlib

def saltAndPepper(password, salt = os.urandom(32)):
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    return (key,salt)

if __name__ == "__main__":
    print("helloworld")
    print(os.urandom(32))
    key = saltAndPepper("password")
    print(key[0])
    print(key[1])