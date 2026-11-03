NetBSD reference sources
========================

These files are unmodified copies from NetBSD 7.2, taken from the
NetBSD/src GitHub mirror at commit a154542 ("Welcome to NetBSD 7.2!").
They are stored flat here; their original paths, relative to
usr/src/sys/, are:

  File           Original path
  GENERIC        arch/acorn26/conf/GENERIC
  iobus.c        arch/acorn26/iobus/iobus.c
  upc_iobus.c    arch/acorn26/iobus/upc_iobus.c
  iocreg.h       arch/acorn26/iobus/iocreg.h
  ioebvar.h      arch/acorn26/ioc/ioebvar.h
  if_eh.c        arch/acorn26/podulebus/if_eh.c
  if_ehreg.h     arch/acorn26/podulebus/if_ehreg.h
  dp8390.c       dev/ic/dp8390.c
  dp8390reg.h    dev/ic/dp8390reg.h
  dp8390var.h    dev/ic/dp8390var.h
  dp83905.c      dev/ic/dp83905.c
  dp83905reg.h   dev/ic/dp83905reg.h
  dp83905var.h   dev/ic/dp83905var.h
  ne2000.c       dev/ic/ne2000.c
  ne2000reg.h    dev/ic/ne2000reg.h
  ne2000var.h    dev/ic/ne2000var.h
  upc.c          dev/ic/upc.c
  upcreg.h       dev/ic/upcreg.h
  upcvar.h       dev/ic/upcvar.h
  wdc_upc.c      dev/ic/wdc_upc.c
  wdcreg.h       dev/ic/wdcreg.h
  wdcvar.h       dev/ic/wdcvar.h
  podules        dev/podulebus/podules

What they are for
-----------------

A5000 native IDE (82C710/711 "UPC"):
  upc_iobus.c, upc.c, upcreg.h, upcvar.h  - attach/configure the UPC chip
  wdc_upc.c, wdcreg.h, wdcvar.h          - the IDE controller on the UPC
  iobus.c, iocreg.h, ioebvar.h           - acorn26 I/O bus, IOC, IOEB glue

EtherH (i-cubed EtherLan 100/200/500) on acorn26:
  if_eh.c, if_ehreg.h                    - the acorn26 EtherH driver
  dp8390.c, dp8390reg.h, dp8390var.h     - DP8390 core it is built on

RiscPC/acorn32-style alternatives, kept for comparison:
  ne2000.c/reg.h/var.h, dp83905.c/reg.h/var.h

Podule manufacturer/product IDs:
  podules

GENERIC is the acorn26 kernel config showing how these attach.

They are included for reference only and are not built as part of
this project.

Licences
--------

Each file keeps its original copyright and licence header, and that
header is the licence for the file. The files are under a mix of
BSD-style licences (2-, 3- and 4-clause), David Greenman's
permissive notice, and public domain (dp83905reg.h, if_ehreg.h,
upcreg.h).

dp83905.c, iocreg.h and podules are under 4-clause BSD licences,
which include an advertising clause. Any code derived from them
must keep those notices in full.

Any code in this project derived from these files must keep the
copyright notices and conditions of the files it came from.
