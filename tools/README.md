# Host tools for cross-building RISC iX kernels

These tools build a RISC iX 1.21 kernel on Linux/macOS from Acorn's Kernel Binary Kit
(the "kernel binary distribution", found as `RISCiX.tar.gz` in `/usr/src/sys` on some
RISC iX discs), running RISC iX's own Norcroft `cc`, `ld`, `ar`, `ranlib`, `symorder`
and `squeeze` under [rixrun](https://github.com/evansm7/rixrun).

The kit, RISC iX binaries and kernels built from them are Acorn's and are **not** included
here.

| File | What it does |
|---|---|
| `unsqueeze.py` | Unsqueezes RISC iX squeezed binaries (magic 0x70b) to ZMAGIC (0x50b) so rixrun can run them. Implements the format in the RISC iX PRM vol 1, chapter 7. `unsqueeze.py IN OUT`, or `unsqueeze.py -r DIR` to convert a tree in place. |
| `rixrun-execve-nested.patch` | Patch for rixrun: `execve("sh -c CMD")` reruns the named RISC iX program under a nested rixrun, with its path mapped into `$RIX_ROOT`. Needed because `ranlib` runs `ar` this way. Apply with `patch -p1` in a rixrun checkout. |
| `rixbuild.sh` | Mirrors the kit's `SYSTEM/Makefile`: compiles the conf files, builds `driverlib.a`/`datalib.a`, makes `version.o`, links `vmunix`, then does copyversion, `symorder` and `squeeze`. |
| `ecide_hook.sh` | `PRE_LINK_HOOK` for `rixbuild.sh` that compiles the ecide driver. |
| `ufs43.py` | Read-only extractor for RISC iX (4.3BSD FFS, little-endian) filesystems in disc images: `ufs43.py IMAGE START_SECTOR OUTDIR [PATH-PREFIX ...]`. |
| `rixdis.py` | Disassembles RISC iX a.out objects, annotating relocations (needs `pip install capstone`). |

## Quick start

```sh
# 1. Toolchain root: a copy of a RISC iX tree containing the kit in usr/src/sys
cp -a riscix-tree rixroot; ROOT=$PWD/rixroot
for d in usr/lib usr/bin usr/ucb usr/acorn; do python3 tools/unsqueeze.py -r $ROOT/$d; done
(cd $ROOT/usr/src/sys && tar cf - include) | (cd $ROOT/usr && tar xpf -)   # kit headers

# 2. rixrun with the nested-execve patch
git clone https://github.com/evansm7/rixrun && (cd rixrun && patch -p1 < ../tools/rixrun-execve-nested.patch && make)
export RIXRUN=$PWD/rixrun/rixrun

# 3. Stock kernel -> $ROOT/usr/src/sys/M/vmunix (squeezed) and vmunix.unsqueezed
tools/rixbuild.sh $ROOT M
```

### Building with ecide

```sh
cd $ROOT/usr/src && cp -a sys sys-ecide && cd sys-ecide
mkdir dev/ecide && cp /path/to/riscix_ide/ecide*.[chs] dev/ecide/ && sed -i 's/\r$//' dev/ecide/*
cp conf/SYSTEMdevconf.h conf/Mdevconf.h && cp conf/SYSTEMlinkopts conf/Mlinkopts
mkdir M && cp SYSTEM/Makefile M/Makefile && patch -p0 < /path/to/riscix_ide/rix_kern_build.patch && rm -rf M
cd -   # back to the repository
SYSDIR=usr/src/sys-ecide PRE_LINK_HOOK=$PWD/tools/ecide_hook.sh \
  EXTRA_DRIVER_OBJS="ecide.o ecide_io.o ecide_io_asm.o ecide_parts.o" \
  VERSION_BANNER="RISC iX (M) ecide 0.21 kernel" tools/rixbuild.sh $ROOT M M
```

`rixbuild.sh` environment options: `RIXRUN` (rixrun binary), `SYSDIR` (kit copy relative to the
root, default `usr/src/sys`), `PRE_LINK_HOOK`, `EXTRA_DRIVER_OBJS`, `VERSION_BANNER`,
`RELEASE_NAME`. The optional third argument picks `conf/<CONF>devconf.h` and `<CONF>linkopts`.

## Notes

- rixrun opens files on the host as given, so the build uses paths relative to the build
  directory (`../../../..` is the root). An absolute `/usr/include` would reach the host's headers.
- The Makefile's `-Zi./KERNCOMP ./KERNCOMP.h` is replaced by `-D_BSD_C=1`: `KERNCOMP.h` only
  defines that, and the `symrename` step it triggers uses an empty rename file.
- `version.o` is built the way `SHARED/compileversion` would build it. The banner must fit
  `KERNEL_VERSION_LEN` (80 bytes including the NUL).
- Norcroft rejects CRLF line endings ("Junk after #include"), so driver sources need LF.
- The squeezed kernel has magic 0x30b, like Acorn's shipped kernels. Boot it from RISC OS with
  `*boot <name>`.
