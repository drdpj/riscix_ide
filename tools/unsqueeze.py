#!/usr/bin/env python3
"""Unsqueeze RISC iX squeezed demand-paged binaries (magic 0x70b -> ZMAGIC 0x50b).

Format from the RISC iX PRM vol 1, chapter 7 (Squeezed image files).
usage: unsqueeze.py IN OUT      (or: unsqueeze.py -r DIR  to unsqueeze a tree in place)
"""
# MIT licence, as for the rest of this repository.
import struct, sys, os

PAGE = 32768
SQ_MAGIC, Z_MAGIC = 0x70b, 0x50b
SQ_OFF = 68            # a_sq4items .. after struct exec (32) + struct version (36)


def decode_table(buf, pos, nbytes, nitems, last, typ):
    cp, end, prev, out = pos, pos + nbytes, -1, []
    while cp < end:
        b = buf[cp]; cp += 1
        if b == 0:
            n = 4 if typ == 4 else 3
            delta = int.from_bytes(buf[cp:cp + n], 'little'); cp += n
            prev += delta; out.append(prev)
        elif b <= 9:
            for _ in range(b):
                prev += 1; out.append(prev)
        elif b <= 91:
            prev += b - 10; out.append(prev)
        elif b <= 173:
            prev += ((b - 92) << 8) | buf[cp]; cp += 1; out.append(prev)
        else:
            prev += ((b - 174) << 16) | (buf[cp + 1] << 8) | buf[cp]; cp += 2; out.append(prev)
    out = [x & 0xffffffff for x in out]
    if len(out) != nitems or (nitems and out[-1] != (last & 0xffffffff)):
        raise ValueError('sq%d table bad (%d items, last %x want %x)' % (typ, len(out), out[-1] if out else 0, last))
    return out


def unsqueeze_page(pg, sq3, sq4):
    rpoff, wpoff, chk = struct.unpack_from('<hhI', pg, 0)
    if rpoff == 0:
        return bytes(PAGE)
    out = [0] * wpoff             # words written downwards from index wpoff-1
    wp = wpoff
    rp = rpoff                    # bytes read downwards from index rpoff-1
    total = 0

    def nxt():
        nonlocal rp
        rp -= 1
        return pg[rp]

    def one(nib):
        nonlocal wp, total
        if nib == 0:
            v = 0
        elif nib == 1:
            v = nxt(); v |= nxt() << 8; v |= nxt() << 16; v |= nxt() << 24
        elif nib <= 8:
            ix = ((nib - 2) << 8) | nxt()
            v = ((sq3[ix] << 8) | nxt()) & 0xffffffff
        else:
            ix = ((nib - 9) << 8) | nxt()
            v = sq4[ix]
        wp -= 1
        out[wp] = v
        total = (total + v) & 0xffffffff

    while wp > 0:
        n = nxt()
        one((n >> 4) & 0xf)
        if wp == 0:
            break
        one(n & 0xf)
    if rp != 8:
        raise ValueError('wrong amount (rp=%d)' % rp)
    if total != chk:
        raise ValueError('checksum')
    data = struct.pack('<%dI' % len(out), *out)
    return data + bytes(PAGE - len(data))


def unsqueeze(d):
    hdr = list(struct.unpack_from('<8I', d, 0))
    if hdr[0] != SQ_MAGIC:
        raise ValueError('not squeezed')
    text, data = hdr[1], hdr[2]
    sq4n, sq3n, sq4sz, sq3sz, sq4last, sq3last = struct.unpack_from('<6I', d, SQ_OFF)
    # find the table start: just after the header (shlibname length not documented)
    for start in range(SQ_OFF + 32, PAGE - sq4sz - sq3sz, 4):
        try:
            sq4 = decode_table(d, start, sq4sz, sq4n, sq4last, 4)
            sq3 = decode_table(d, start + sq4sz, sq3sz, sq3n, sq3last, 3)
            break
        except (ValueError, IndexError):
            continue
    else:
        raise ValueError('tables not found')
    npages = (text + PAGE - 1) // PAGE + (data + PAGE - 1) // PAGE
    body = bytearray()
    for i in range(npages):
        pg = d[PAGE * (i + 1):PAGE * (i + 2)]
        pg = pg + bytes(PAGE - len(pg))
        body += unsqueeze_page(pg, sq3, sq4)
    head = bytearray(d[:PAGE])
    struct.pack_into('<I', head, 0, Z_MAGIC)
    struct.pack_into('<6I', head, SQ_OFF, 0, 0, 0, 0, 0, 0)
    head[start:start + sq4sz + sq3sz] = bytes(sq4sz + sq3sz)
    rest = d[PAGE * (npages + 1):]          # symbols etc, if any
    return bytes(head) + bytes(body[:text + data]) + rest, start


def main():
    if sys.argv[1] == '-r':
        ok = bad = 0
        for root, ds, fs in os.walk(sys.argv[2]):
            for f in fs:
                p = os.path.join(root, f)
                if os.path.islink(p) or not os.path.isfile(p):
                    continue
                d = open(p, 'rb').read(PAGE * 64)
                if len(d) < 4 or struct.unpack_from('<I', d, 0)[0] != SQ_MAGIC:
                    continue
                d = open(p, 'rb').read()
                try:
                    out, _ = unsqueeze(d)
                    mode = os.stat(p).st_mode
                    open(p, 'wb').write(out); os.chmod(p, mode); ok += 1
                except Exception as e:
                    print('FAIL', p, e); bad += 1
        print('unsqueezed', ok, 'failed', bad)
        return
    d = open(sys.argv[1], 'rb').read()
    out, start = unsqueeze(d)
    open(sys.argv[2], 'wb').write(out)
    print('ok, tables at', start, 'size', len(out))


if __name__ == '__main__':
    main()
