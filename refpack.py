#!/usr/bin/env python3

import sys
from cffi import FFI
from os.path import dirname

ffi = FFI()
ffi.cdef("""
    typedef unsigned char u8;
    typedef unsigned long long u64;
    typedef struct {
        u8 * data;
        u64 len;
    } OutVec;

    OutVec decompress(const u8 *, u64 len);
    OutVec compress(const u8 *, u64 len);
    void free_outvec(OutVec);
""")
libsage = ffi.dlopen(dirname(__file__) + "/refpack/target/debug/librefpack.so")

class NotRefpackedError(ValueError):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)

class RefunpackError(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)

def is_refpacked(data):
    return (data[1] == 0xfb and data[0] & 0x3e == 0x10)

def decompress(data):
    """
    decompress data using the refpack algorithm
    raises NotRefpackedError if data is detected to not be refpacked
    """
    if not is_refpacked(data):
        raise NotRefpackedError("Expected refpacked data, invalid header")
    outbuf = b''

    cdata = ffi.new("u8[]", data)
    out_vec = libsage.decompress(cdata, len(data))
    if out_vec.data == ffi.NULL:
        libsage.free_outvec(out_vec)
        raise RefunpackError("Failed to decompress")

    outbuf = bytes(out_vec.data[0:out_vec.len])

    libsage.free_outvec(out_vec)
    return outbuf

#TODO: make this actually compress, instead of serializing
def compress(data):
    """
    compress data using the refpack algorithm
    """
    # 4 byte length field
    outbuf = b'\x90\xfb'
    decompressed_size = len(data).to_bytes(4, byteorder='big')
    outbuf += decompressed_size
    pos = 0

    while pos < len(data):
        remaining = len(data) - pos
        chunk_len = min(remaining, 112)
        ocl = chunk_len//4
        if ocl == 0:
            outbuf += bytes([0xfc+chunk_len])
            outbuf += data[pos:pos+chunk_len]
            pos += chunk_len
        else:
            outbuf += bytes([0xe0+(ocl-1)])
            outbuf += data[pos:pos+4*ocl]
            pos += 4 * ocl
    return outbuf

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("usage: refpack [compress/decompress] <infile> <outfile>")
        sys.exit(1)
    data = open(sys.argv[2], "rb").read()
    if sys.argv[1] == "compress":
        out_data = compress(data)
    elif sys.argv[1] == "decompress":
        out_data = decompress(data)
    else:
        print("usage: refpack [compress/decompress] <infile> <outfile>")
        sys.exit(1)
    open(sys.argv[3], "wb").write(out_data)
