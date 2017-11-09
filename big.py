#!/usr/bin/python3

import sys
from struct import unpack_from as upf
import refpack

class big_file:
    def __init__(self, filename):
        # setup file information
        self.filename = filename
        self.data = open(filename, "rb").read()
        magic = self.data[:4]
        if magic != b'BIG4':
            raise ValueError("Not a big file (INVALID MAGIC)")
        (self.size,) = upf("<I", self.data, 4)
        (self.n_files, self.d_offset) = upf(">II", self.data, 8)

        # read entry table
        self.entry_table = {}
        eoff = 16
        while len(self.entry_table) != self.n_files:
            (entry_off, entry_size) = upf(">II", self.data, eoff)
            entry_name = b''
            
            # read till null terminator
            while True:
                _to = eoff+8+len(entry_name)
                c = self.data[_to: _to+1]
                if c == b"\0":
                    break
                entry_name += c

            if entry_name in self.entry_table:
                print("Dup entries! REEEEEEEEEEEE!")
                print("Dup entries: ", entry_name)
                exit(1)
            entry_name = entry_name.decode("ascii")
            self.entry_table[entry_name] = self.data[entry_off:entry_off+entry_size]
            eoff = eoff + 8 + len(entry_name) + 1

    def dump_files(self):
        print("Size: ", self.size)
        print("NFiles: ", self.n_files)
        print("DOffset: ", self.d_offset)
        for name in self.entry_table.keys():
            print("File:\n    Name: ", name, "\n    Length: ", len(self.entry_table[name]), "\n")

    def get_file(self, filename):
        try:
            out_data = refpack.decompress(self.entry_table[filename])
        except refpack.NotRefpackedError as e:
            print(self.entry_table[filename])
            raise e
        return out_data


if __name__ == '__main__':
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print("Usage: big.py filename")
        exit(1)
    big = big_file(sys.argv[1])
    if len(sys.argv)==2:
        big.dump_files()
    elif len(sys.argv)==3:
        print(big.get_file(sys.argv[2]))
    else:
        open(sys.argv[3], "wb").write(big.get_file(sys.argv[2]))
