#!/usr/bin/env python3
"""Disassemble a RISC iX (a.out OMAGIC/ZMAGIC, little-endian ARM26) object file,
annotating relocations and symbols.  usage: rixdis.py FILE.o [SYMBOL-SUBSTRING]
"""
# MIT licence, as for the rest of this repository.
import struct, sys
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM

def load(path):
    d = open(path, 'rb').read()
    mag, text, data, bss, syms, entry, trs, drs = struct.unpack_from('<8I', d, 0)
    hdr = 32
    to = hdr; do = to + text; tro = do + data; dro = tro + trs
    so = dro + drs; stro = so + syms
    def sname(sx):
        e = d.index(b'\0', stro + sx); return d[stro + sx:e].decode('latin-1')
    symtab = []
    for k in range(syms // 12):
        sx, ty, ot, de, val = struct.unpack_from('<IBBhI', d, so + k * 12)
        symtab.append((sname(sx) if sx else '', ty, val))
    relocs = {}
    for k in range(trs // 8):
        addr, w = struct.unpack_from('<II', d, tro + k * 8)
        num = w & 0xffffff; pcrel = (w >> 24) & 1; ext = (w >> 27) & 1
        name = symtab[num][0] if ext else {4: '.text', 6: '.data', 8: '.bss'}.get(num, 'seg%d' % num)
        relocs[addr] = (name, pcrel)
    labels = {}
    for n, ty, v in symtab:
        if (ty & 0x1e) == 4 and n:      # N_TEXT
            labels.setdefault(v, []).append(n)
    return d[to:to + text], d[do:do + data], relocs, labels, symtab

def main():
    path = sys.argv[1]; want = sys.argv[2] if len(sys.argv) > 2 else None
    text, data, relocs, labels, symtab = load(path)
    md = Cs(CS_ARCH_ARM, CS_MODE_ARM); md.skipdata = True
    show = want is None
    for ins in md.disasm(text, 0):
        if ins.address in labels:
            ls = labels[ins.address]
            if want is not None:
                show = any(want in l for l in ls) or (show and not any(l.startswith('_') for l in ls))
            if show: print('\n%s:' % ' '.join(ls))
        if not show: continue
        r = relocs.get(ins.address)
        note = '   ; reloc %s%s' % (r[0], ' (pcrel)' if r[1] else '') if r else ''
        print('%06x: %-8s %s%s' % (ins.address, ins.mnemonic, ins.op_str, note))
        # word literal relocations
    if want is None:
        for a, (n, p) in sorted(relocs.items()):
            pass

if __name__ == '__main__':
    main()
