# Separate images for the partitions described by the supplied DTS.
# Match porting-spinand512.diff: booti loads a raw Image and a separate DTB.
  KERNEL := kernel-bin
  KERNEL_INSTALL := 1
  KERNEL_SIZE := 65536k
  KERNEL_SUFFIX := -Image
  ARTIFACTS := board.dtb
  ARTIFACT/board.dtb := copy-file $$(KDIR)/image-rk3568-nsy-g68-plus.dtb | check-size 1024k
  BLOCKSIZE := 256k
  PAGESIZE := 4096
  SUBPAGESIZE := 4096
  KERNEL_IN_UBI :=
  UBOOTENV_IN_UBI :=
  UBINIZE_PARTS :=
  UBINIZE_OPTS := -E 5
  FILESYSTEMS := squashfs
  IMAGES := rootfs.ubi rootfs.squashfs
  IMAGE/rootfs.ubi := append-ubi | check-size 435200k
  IMAGE/rootfs.squashfs := append-rootfs
