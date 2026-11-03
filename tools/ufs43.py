#!/usr/bin/env python3
"""Minimal read-only 4.3BSD FFS (RISC iX, little-endian) extractor.

usage: ufs43.py IMAGE START_SECTOR OUTDIR [PATH-PREFIX ...]
Extracts regular files, directories and symlinks; device nodes are listed
in OUTDIR.devices.txt instead of created. Optional PATH-PREFIX arguments
(e.g. /usr/include) restrict extraction to those subtrees.
START_SECTOR is the partition start (primary superblock at +16 sectors).
"""
# MIT licence, as for the rest of this repository.
import os, struct, sys, stat

class FS:
    def __init__(self, img, start):
        self.f = open(img, 'rb')
        self.base = start * 512
        sb = self.rd(8192, 2048)
        i = lambda o: struct.unpack_from('<i', sb, o)[0]
        assert i(1372) == 0x011954, 'bad magic'
        self.iblkno, self.cgoffset, self.cgmask = i(16), i(24), i(28)
        self.bsize, self.fsize, self.frag = i(48), i(52), i(56)
        self.ipg, self.fpg = i(184), i(188)
        self.inopb = self.bsize // 128
        self.nindir = self.bsize // 4

    def rd(self, off, n):
        self.f.seek(self.base + off)
        return self.f.read(n)

    def frag_rd(self, fragno, n):
        return self.rd(fragno * self.fsize, n)

    def inode(self, ino):
        cg = ino // self.ipg
        cgstart = self.fpg * cg + self.cgoffset * (cg & ~self.cgmask)
        fb = cgstart + self.iblkno + ((ino % self.ipg) // self.inopb) * self.frag
        d = self.frag_rd(fb, self.bsize)
        o = (ino % self.inopb) * 128
        di = d[o:o + 128]
        mode, nlink, uid, gid = struct.unpack_from('<HhHH', di, 0)
        size = struct.unpack_from('<I', di, 8)[0]
        mtime = struct.unpack_from('<i', di, 24)[0]
        atime = struct.unpack_from('<i', di, 16)[0]
        db = list(struct.unpack_from('<12i', di, 40))
        ib = list(struct.unpack_from('<3i', di, 88))
        return dict(mode=mode, nlink=nlink, uid=uid, gid=gid, size=size,
                    mtime=mtime, atime=atime, db=db, ib=ib, raw=di)

    def blocks(self, ino_d):
        """Yield fragment addresses of each logical block (0 = hole)."""
        for b in ino_d['db']:
            yield b
        def ind(addr, level):
            if addr == 0:
                for _ in range(self.nindir ** (level + 1)):
                    yield 0
                return
            ptrs = struct.unpack('<%di' % self.nindir, self.frag_rd(addr, self.bsize))
            for p in ptrs:
                if level == 0:
                    yield p
                else:
                    yield from ind(p, level - 1)
        for lvl, a in enumerate(ino_d['ib']):
            yield from ind(a, lvl)

    def data(self, ino_d):
        size = ino_d['size']
        out = bytearray()
        for b in self.blocks(ino_d):
            if len(out) >= size:
                break
            n = min(self.bsize, size - len(out))
            out += self.frag_rd(b, n) if b else bytes(n)
        return bytes(out[:size])

    def readdir(self, ino_d):
        d = self.data(ino_d)
        o = 0
        while o + 8 <= len(d):
            ino, reclen, namlen = struct.unpack_from('<IHH', d, o)
            if reclen == 0:
                o = (o // 512 + 1) * 512
                continue
            if ino:
                yield d[o + 8:o + 8 + namlen].decode('latin-1'), ino
            o += reclen


def walk(fs, ino, path, out, devs, prefixes, seen):
    d = fs.inode(ino)
    for name, cino in fs.readdir(d):
        if name in ('.', '..'):
            continue
        p = path + '/' + name
        if prefixes and not any(p.startswith(x) or x.startswith(p + '/') for x in prefixes):
            continue
        c = fs.inode(cino)
        t = c['mode'] & 0o170000
        dst = out + p
        try:
            if t == 0o040000:
                os.makedirs(dst, exist_ok=True)
                walk(fs, cino, p, out, devs, prefixes, seen)
            elif t == 0o100000:
                if cino in seen:
                    if os.path.exists(seen[cino]):
                        os.link(seen[cino], dst)
                        continue
                with open(dst, 'wb') as fh:
                    fh.write(fs.data(c))
                seen[cino] = dst
            elif t == 0o120000:
                tgt = fs.data(c).decode('latin-1')
                os.symlink(tgt, dst)
            else:
                maj = struct.unpack_from('<i', c['raw'], 40)[0]
                devs.write('%s %o dev=0x%x\n' % (p, c['mode'], maj))
                continue
            if t != 0o120000:
                os.chmod(dst, (c['mode'] & 0o7777) | 0o600 | (0o100 if t == 0o040000 else 0))
                os.utime(dst, (c['atime'], c['mtime']))
        except Exception as e:
            print('ERR', p, e, file=sys.stderr)


if __name__ == '__main__':
    img, start, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    prefixes = sys.argv[4:]
    fs = FS(img, start)
    os.makedirs(out, exist_ok=True)
    with open(out.rstrip('/') + '.devices.txt', 'w') as devs:
        walk(fs, 2, '', out, devs, prefixes, {})
