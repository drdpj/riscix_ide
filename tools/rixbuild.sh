#!/bin/bash
# MIT licence, as for the rest of this repository.
# Relink a RISC iX 1.21 kernel from the Kernel Binary Kit, cross-built with rixrun.
# Mirrors SYSTEM/Makefile.  usage: rixbuild.sh RIXROOT BUILDNAME [CONFNAME]
#   RIXROOT   root of an (unsqueezed-toolchain) RISC iX tree with the kit in usr/src/sys
#   BUILDNAME build directory created under usr/src/sys (copied from SYSTEM)
#   CONFNAME  prefix of ../conf/<CONF>devconf.h / linkopts (default SYSTEM)
# Extra objects: set EXTRA_DRIVER_OBJS (paths relative to the build dir).
# Extra compile steps: set PRE_LINK_HOOK to a script sourced in the build dir.
set -e
ROOT=$(cd "$1" && pwd); B=$2; CONF=${3:-SYSTEM}
RIXRUN=${RIXRUN:-rixrun}              # path to the patched rixrun binary
export RIX_ROOT=$ROOT
SYS=$ROOT/${SYSDIR:-usr/src/sys}   # SYSDIR: alternative kit copy, same depth
cd "$SYS"
rm -rf "$B"; mkdir "$B"; cd "$B"
cp ../SYSTEM/KERNCOMP.* ../SYSTEM/ps_conf.[ch] ../SYSTEM/sysent.h ../SYSTEM/version.c . 2>/dev/null || true
ln -s ../SHARED SHARED
cp ../conf/${CONF}devconf.h devconf.h
cp ../conf/lineconf.h lineconf.h
cp ../conf/${CONF}linkopts linkopts

R=../../../..                       # build dir -> RIX root, relative
run() { "$RIXRUN" "$@"; }
CC="$R/usr/lib/cc"   # -Zi./KERNCOMP only runs symrename with an empty rename file
CFLAGS="-D_BSD_C=1 -Fn -R -D_KERNEL -j$R/usr/include,. -DQUOTA -DSYSACCT -DINET -DISO -DNFSSERVER -DNFSCLIENT -DUFS -DGATEWAY -DCHECK"
cc() { echo "  cc $*"; run $CC -c $CFLAGS "$@"; }

cc ../conf/param.c
cc ../conf/conf.c
cc ../conf/md_conf.c
cc ../conf/xcbconf.c
cc ../sys/tty_conf.c
cc ../sys/pty_data.c
cc ../net/ppp_data.c
cc ../net/sl_data.c
cc -o ps_conf.o ps_conf.c
cc -o md.o ../dev/md/md.c

[ -n "$PRE_LINK_HOOK" ] && . "$PRE_LINK_HOOK"

S=SHARED
DRIVER_OBJS="$S/badblk.o $S/cent.o $S/dk.o $S/econet.o $S/econetmc.o $S/en_io.o $S/es.o
 $S/fdc.o $S/fdc_fiq.o $S/hawk.o $S/hawkv12.o $S/hawk_io.o $S/if_ea.o $S/if_ea_move.o
 $S/if_en.o $S/if_et.o $S/if_ppp.o $S/if_sl.o $S/lbp_dev.o $S/lbp_fiq.o md.o $S/nym.o
 $S/partition.o $S/ps_copy.o $S/ps_direct.o $S/ps_dmac.o $S/ps_driver.o $S/ps_irq.o
 $S/ps_scsi.o $S/ps_sequential.o $S/ps_soft_irq.o $S/ps_xfer.o $S/scsi.o $S/tty_fifo.o
 $S/tty_mki.o $S/tty_pty.o $S/tty_tb.o $S/winc.o $S/zilog.o $EXTRA_DRIVER_OBJS"
echo "  ar driverlib.a"; rm -f driverlib.a
run $R/usr/bin/ar qc driverlib.a $DRIVER_OBJS
run $R/usr/bin/ranlib driverlib.a
rm -f datalib.a
run $R/usr/bin/ar qc datalib.a pty_data.o ppp_data.o sl_data.o
run $R/usr/bin/ranlib datalib.a

# version.o: what SHARED/compileversion does (it execs cc, which rixrun can't nest cleanly):
# RELEASENAME, OBJECTNUMBER=0 and VERSIONSTRING as a byte list.
PRODUCT=${VERSION_BANNER:-"RISC iX ($B) cross-built kernel"}
RELNAME=${RELEASE_NAME:-"${USER:-cross} #1 special:"}
VTEXT="$PRODUCT $RELNAME made $(LC_ALL=C date '+%a %b %e %H:%M:%S %Y')"
VTEXT=${VTEXT:0:79}                  # KERNEL_VERSION_LEN is 80 including the NUL
VBYTES=$(python3 -c 'import sys; print(",".join("0x%02x"%b for b in sys.argv[1].encode()+b"\0"))' "$VTEXT")
echo "  cc version.c  [$VTEXT]"
run $CC -c $CFLAGS "-DRELEASENAME=\"$RELNAME\"" -DOBJECTNUMBER=0 "-DVERSIONSTRING=$VBYTES" version.c

SHARED_OBJS=$(sed -n '/^SHARED_OBJS=/,/^$/p' ../SYSTEM/Makefile | grep -o '\$S/[A-Za-z_0-9]*\.o' | sed 's/\$S/SHARED/')
LOCAL_OBJS="conf.o md_conf.o tty_conf.o xcbconf.o ps_conf.o"
echo "  ld vmunix"
rm -f vmunix
run $R/usr/bin/ld $(cat linkopts) -o vmunix -e start -T 01800000 \
    SHARED/locore.o param.o $SHARED_OBJS $LOCAL_OBJS version.o \
    SHARED/ufslib.a SHARED/nfslib.a driverlib.a datalib.a SHARED/deslib.a
ls -la vmunix

# copyversion: copy version_info into the a.out header's a_version (offset 32, 36 bytes)
python3 - vmunix <<'PY'
import struct, sys
p = sys.argv[1]; a = bytearray(open(p, 'rb').read())
mag, text, data, bss, syms = struct.unpack_from('<5I', a, 0)
so = 0x8000 + text + data; stro = so + syms; vi = None
for k in range(syms // 12):
    sx, ty, ot, de, val = struct.unpack_from('<IBBhI', a, so + k * 12)
    if 4 <= sx and a[stro + sx:stro + sx + 14] == b'_version_info\0':
        vi = val; break
off = vi - 0x01800000 + 0x8000
a[32:68] = a[off:off + 36]
open(p, 'wb').write(a)
print('  copyversion: version_info at %#x' % vi)
PY
# symorder (optional in the Makefile; speeds up ps/w/vmstat)
grep -v '^#' ../conf/symbols.raw | sed 's/^	//' | sort -u > symbols.sort
echo "  symorder"; run $R/usr/ucb/symorder symbols.sort vmunix || echo "  (symorder failed; continuing)"
cp vmunix vmunix.unsqueezed
echo "  squeeze"; run $R/usr/acorn/squeeze vmunix
chmod 755 vmunix
ls -la vmunix vmunix.unsqueezed
