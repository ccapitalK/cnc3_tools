use std::slice;
use std::ptr;
use std::mem;

// FLAGS: 0b00000LUC
#[derive(Debug)]
struct RefpackHeader {
    flags: u8,
    decompressed_len: usize,
    compressed_len: usize
}

impl RefpackHeader {
    fn from_bytes(input: &[u8]) -> Option<(Self, &[u8])> {
        if input.len() < 2 || input[1] != 0xfb || input[0] & 0x3e != 0x10 {
            return None;
        }
        let flags = ((input[0] >> 5) & 0x06) | (input[0] & 1);
        let flen = if flags & 0x4 > 0 {
            4
        } else {
            3
        };
        let mut pos = 2;
        let (compressed_len, decompressed_len) = {
            let mut take = || {
                if input[pos..].len() < flen {
                    None
                } else {
                    let mut rval = 0u32;
                    for i in &input[pos..pos+flen] {
                        rval = rval << 8;
                        rval += *i as u32;
                    }
                    pos += flen;
                    Some(rval)
                }
                    
            };
            (
                if flags & 1 > 0 {
                    //have compressed length
                    match take() {
                        Some(v) => v as usize,
                        None => return None
                    }
                } else {
                    0
                },
                match take() {
                    Some(v) => v as usize,
                    None => return None
                }
            )
        };
        Some((Self {
            flags: flags,
            decompressed_len: decompressed_len,
            compressed_len: compressed_len,
        }, &input[pos..]))
    }

    fn write_to_vec(&self, dest: &mut Vec<u8>){
        let flags = (self.flags&1) | ((self.flags&0x06) << 5) | 0x10;
        dest.push(flags);
        dest.push(0xfb);
        let flen = if self.flags & 0x4 > 0 {
            4
        } else {
            3
        };
        let mut write_value = |val: u32| {
            for i in 0..flen {
                let i = flen - i - 1;
                dest.push(((val >> (8*i)) & 0xff) as u8);
            }
        };
        if flags & 1 > 0 {
            write_value(self.compressed_len as u32);
        }
        write_value(self.decompressed_len as u32);
    }
}

fn decompress_actual(input: &[u8]) -> Option<Vec<u8>> {
    let (header, input) = match RefpackHeader::from_bytes(input) {
        Some(v) => v,
        None => return None
    };
    let mut ret_vec = Vec::new();
    let mut pos = 0usize;
    let mut stopped = false;
    while pos < input.len() {
        let com = input[pos] >> 5;
        let  plen: u32;
        let  rlen: u32;
        let rdist: u32;
        if com < 4 {
            // 2 byte command
            if pos + 1 >= input.len() {
                return None;
            }
            plen =    (input[pos] as u32) & 0x03                                   ;
            rlen =  (((input[pos] as u32) & 0x1C) >> 2) + 3                        ;
            rdist = (((input[pos] as u32) & 0x60) << 3) + (input[pos+1] as u32) + 1;
            pos += 2;
        } else if com < 6 {
            if pos + 2 >= input.len() {
                return None;
            }
            // 3 byte command
            plen =   ((input[pos+1] as u32) & 0xC0) >> 6                             ;
            rlen =   ((input[  pos] as u32) & 0x3F)  + 4                             ;
            rdist = (((input[pos+1] as u32) & 0x3F) << 8) + (input[pos+2] as u32) + 1;
            pos += 3;
        } else if com == 6 {
            if pos + 3 >= input.len() {
                return None;
            }
            // 4 byte command
            plen =    (input[pos] as u32) & 0x03                                                                   ;
            rlen =  (((input[pos] as u32) & 0x0C) <<  6) +  (input[pos+3] as u32) + 5                              ;
            rdist = (((input[pos] as u32) & 0x10) << 12) + ((input[pos+1] as u32) << 8) + (input[pos+2] as u32) + 1;
            pos += 4;
        } else {
            // 1 byte command
            if input[pos] >= 0xfc {
                plen = (input[pos] & 0x03) as u32;
                stopped = true;
            } else {
                plen = (((input[pos] & 0x1F) + 1) << 2) as u32;
            }
            rlen = 0u32;
            rdist = 0u32;
            pos += 1;
        }
        // check if enough remaining bytes in input, and enough bytes already output
        if pos + plen as usize > input.len() || rdist as usize > ret_vec.len() + (plen as usize) {
            return None;
        }
        ret_vec.extend((&input[pos..pos+(plen as usize)]).iter().cloned());
        pos += plen as usize;
        // append back reference
        if rlen > 0 {

            let end = ret_vec.len();
            let beg = end - (rdist as usize);
            let mut rlen = rlen as usize;
            let rdist = rdist as usize;
            let mut append_chunk = |beg, end| {
                for i in beg..end {
                    let v = ret_vec[i];
                    ret_vec.push(v);
                }
            };

            while rdist < rlen {
                append_chunk(beg,end);
                rlen -= rdist;
            }
            append_chunk(beg,beg+rlen);
        }
    }
    if ret_vec.len() != header.decompressed_len || !stopped {
        None
    }else{
        Some(ret_vec)
    }
}

fn compress_actual(input: &[u8]) -> Vec<u8> {
    let mut ret_vec = Vec::new();
    RefpackHeader {
        flags: if input.len() > 0xffffff {
            0x04
        } else {
            0
        },
        decompressed_len: input.len(),
        compressed_len: 0
    }.write_to_vec(&mut ret_vec);
    //macro_rules! add_tuple {
    let add_tuple = |data: &[u8], rdist: u32, rlen: u32| -> bool {
        // TODO: Finish this
        true
    };
    ret_vec
}

//================================================================
// Public interface stuff
//================================================================

#[repr(C)]
pub struct OutVec {
    data: *mut u8,
    len: usize
}

#[no_mangle]
pub extern "C" fn square(x: u32) -> u64 {
    (x as u64) * (x as u64)
}

#[no_mangle]
pub extern "C" fn decompress(input: *const u8, len: usize) -> OutVec {
    let in_vec = unsafe {
        slice::from_raw_parts(input, len)
    };

    let mut decompressed = match decompress_actual(in_vec) {
        Some(v) => v,
        None => return OutVec {
            data: ptr::null_mut(),
            len: 0
        }
    };

    // remove extra space
    decompressed.shrink_to_fit();
    assert!(decompressed.len() == decompressed.capacity());

    // forget to dealloc memory, before returning it
    let out_vec = OutVec {
        data: decompressed.as_mut_ptr(),
        len: decompressed.len()
    };
    mem::forget(decompressed);
    out_vec
}

#[no_mangle]
pub extern "C" fn compress(input: *const u8, len: usize) -> OutVec {
    let in_vec = unsafe {
        slice::from_raw_parts(input, len)
    };

    let mut compressed = compress_actual(in_vec);

    // remove extra space
    compressed.shrink_to_fit();
    assert!(compressed.len() == compressed.capacity());

    // forget to dealloc memory, before returning it
    let out_vec = OutVec {
        data: compressed.as_mut_ptr(),
        len: compressed.len()
    };
    mem::forget(compressed);
    out_vec
}

#[no_mangle]
pub unsafe extern "C" fn free_outvec(input: OutVec) {
    if input.data != ptr::null_mut(){
        drop(Vec::from_raw_parts(input.data, input.len, input.len));
    }
}

#[cfg(test)]
mod tests {
    use std::fs::File;
    use std::io::Read;
    #[test]
    fn decompress() {
        let mut test_file = File::open("tests/dec_test").expect("Failed to open file");
        let mut expt_file = File::open("tests/dec_expt").expect("Failed to open file");
        let mut tv = Vec::new();
        let mut ev = Vec::new();
        test_file.read_to_end(&mut tv).expect("Failed to read file to end");
        expt_file.read_to_end(&mut ev).expect("Failed to read file to end");
        let dv = ::decompress_actual(tv.as_slice()).unwrap();
        assert!(dv == ev);
    }
    //#[test]
    //fn compress() {
    //    let mut expt_file = File::open("tests/dec_expt").expect("Failed to open file");
    //    let mut ev = Vec::new();
    //    expt_file.read_to_end(&mut ev).expect("Failed to read file to end");
    //    let compressed = ::compress_actual(ev.as_slice());
    //    let round_trip = ::decompress_actual(compressed.as_slice()).unwrap();
    //    assert!(round_trip == ev);
    //}
}
