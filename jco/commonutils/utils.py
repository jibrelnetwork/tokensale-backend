import string
import random
from Crypto.Hash import keccak
from rlp.sedes import big_endian_int
from rlp.utils import str_to_bytes, encode_hex, decode_hex, ascii_chr


def is_numeric(x):
    return isinstance(x, int)


def big_endian_to_int(x):
    return big_endian_int.deserialize(str_to_bytes(x).lstrip(b'\x00'))


def to_string(value):
    if isinstance(value, bytes):
        return value

    if isinstance(value, str):
        return bytes(value, 'utf-8')

    if isinstance(value, int):
        return bytes(str(value), 'utf-8')


def sha3_256(x):
    return keccak.new(digest_bits=256, data=x).digest()


def sha3(seed):
    return sha3_256(to_string(seed))


def int_to_addr(x):
    o = [b''] * 20
    for i in range(20):
        o[19 - i] = ascii_chr(x & 0xff)
        x >>= 8
    return b''.join(o)


def normalize_address(x, allow_blank=False):
    if is_numeric(x):
        return int_to_addr(x)

    if allow_blank and x in {'', b''}:
        return b''

    if len(x) in (42, 50) and x[:2] in {'0x', b'0x'}:
        x = x[2:]

    if len(x) in (40, 48):
        x = decode_hex(x)

    if len(x) == 24:
        assert len(x) == 24 and sha3(x[:20])[:4] == x[-4:]
        x = x[:20]

    if len(x) != 20:
        raise Exception("Invalid address format: %r" % x)

    return x


def checksum_encode(addr): # Takes a 20-byte binary address as input
    addr = normalize_address(addr)
    o = ''
    v = big_endian_to_int(sha3(encode_hex(addr)))

    for i, c in enumerate(encode_hex(addr)):
        if c in '0123456789':
            o += c
        else:
            o += c.upper() if (v & (2 ** (255 - 4 * i))) else c.lower()

    return '0x' + o
