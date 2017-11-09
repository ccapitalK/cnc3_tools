#!/usr/bin/env python3

import sys

class NotRefpackedError(ValueError):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)

def decompress(data):
    """
    decompress data using the refpack algorithm
    raises NotRefpackedError if data is detected to not be refpacked
    """
    if data[1] != 0xfb or data[0] & 0x3e != 0x10:
        raise NotRefpackedError("Expected refpacked data, invalid header")
    # parse flags
    flags = {}
    flags['L'] = data[0] >> 7
    flags['U'] = data[0] >> 6 & 1
    flags['C'] = data[0]      & 1
    flen = 4 if flags['L'] else 3
    pos = 2
    stop = False
    outbuf = b''

    # parse de/compressed size fields
    if flags['C']:
        compressed_size = data[pos:pos + flen]
        pos += flen
    decompressed_size = data[pos:pos + flen]
    pos += flen

    # decompress
    while not stop:
        com = data[pos] >> 5
        if com < 4:
            #print("2 byte command")
            plen =   (data[pos] & 0x03)     
            rlen =  ((data[pos] & 0x1C) >> 2) + 3
            rdist = ((data[pos] & 0x60) << 3) + data[pos+1] + 1
            pos += 2
        elif com < 6:
            #print("3 byte command")
            plen =  ((data[pos+1] & 0xC0) >> 6)
            rlen =  ((data[  pos] & 0x3F)  + 4)
            rdist = ((data[pos+1] & 0x3F) << 8) + data[pos+2] + 1
            pos += 3
        elif com == 6:
            #print("4 byte command")
            plen  =  (data[pos] & 0x03)
            rlen  = ((data[pos] & 0x0C) <<  6) + data[pos+3] + 5
            rdist = ((data[pos] & 0x10) << 12) + (data[pos+1] << 8) + data[pos+2] + 1
            pos += 4
        elif com == 7:
            if data[pos] >= 0xfc:
                #print("stop command")
                plen = data[pos] & 0x03
                stop = True
            else:
                #print("1 byte command")
                plen = ((data[pos] & 0x1F) + 1) << 2
                pass
            rlen = 0
            rdist = 0
            pos += 1

        #print(plen, rlen, rdist)
        outbuf += data[pos:pos+plen]
        pos += plen
        if rlen > 0:
            seg = outbuf[-rdist:]
            while len(seg) < rlen:
                outbuf += seg
                rlen -= len(seg)
            outbuf += seg[:rlen]
        #print(outbuf)
        #input()
    return outbuf

#TODO: make this actually compress, instead of serializing
def compress(data):
    """
    compress data using the refpack algorithm
    """
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
