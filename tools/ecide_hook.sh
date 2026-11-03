# sourced by rixbuild.sh in the build dir: compile the ecide driver
# MIT licence, as for the rest of this repository.
for f in ecide ecide_io ecide_parts; do cc -I../dev/ecide -o $f.o ../dev/ecide/$f.c; done
cc -I../dev/ecide -o ecide_io_asm.o ../dev/ecide/ecide_io_asm.s
