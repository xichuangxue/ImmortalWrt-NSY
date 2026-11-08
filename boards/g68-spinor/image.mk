# Partition limits match dts/rk3568-nsy-g68-plus-spiNor.dts.
  BOOT_FLOW :=
  KERNEL := kernel-bin
  KERNEL_INSTALL := 1
  KERNEL_SIZE := 24576k
  KERNEL_SUFFIX := -Image
  ARTIFACTS := board.dtb
  ARTIFACT/board.dtb := copy-file $$(KDIR)/image-rk3568-nsy-g68-plus.dtb | check-size 512k
  KERNEL_IN_UBI :=
  UBOOTENV_IN_UBI :=
  UBINIZE_PARTS :=
  FILESYSTEMS := squashfs
  IMAGES := rootfs.squashfs
  IMAGE/rootfs.squashfs := append-rootfs | check-size 19968k
