#!/usr/bin/env python3

import sys
from struct import unpack_from as upf
import refpack
import argparse

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
                print("Dup entry: ", entry_name)
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

    def get_file(self, filename, auto_decompress=True):
        out_data = self.entry_table[filename]
        if auto_decompress and refpack.is_refpacked(out_data):
            out_data = refpack.decompress(out_data)
        return out_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("big_file", 
            help="name of .big file to parse")
    parser.add_argument("inner_file", nargs='?', 
            help="name of file to extract", default='')
    parser.add_argument("output_file", nargs='?', 
            help="name of output file", default='')
    parser.add_argument("--no-decompress", dest='no_decompress', help="Don't automatically decompress", action='store_true')
    args = parser.parse_args()
    big = big_file(args.big_file)
    if args.inner_file == '':
        big.dump_files()
    else: 
        if args.no_decompress:
            out_data = big.get_file(args.inner_file, False)
        else:
            out_data = big.get_file(args.inner_file)
        if args.output_file == '':
            print(out_data)
        else:
            open(args.output_file, "wb").write(out_data)
