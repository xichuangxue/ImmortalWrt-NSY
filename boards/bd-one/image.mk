# BD-One boots with the board's vendor loader, a raw arm64 Image and its DTB.
define Build/bd-one-boot
	rm -fR $@.boot
	mkdir -p $@.boot
	$(CP) $(IMAGE_KERNEL) $@.boot/kernel.img
	$(CP) $(KDIR)/image-$(notdir $(firstword $(DEVICE_DTS))).dtb $@.boot/rockchip.dtb
	mkimage -A arm -O linux -T script -C none -a 0 -e 0 \
		-d bd-one.bootscript $@.boot/boot.scr
endef

define Build/bd-one-img
	test "$$(stat -c %s bd-one-bootloader.bin)" -eq 16744448
	PADDING=1 $(SCRIPT_DIR)/gen_image_generic.sh \
		$@ \
		$(CONFIG_TARGET_KERNEL_PARTSIZE) $@.boot \
		$(CONFIG_TARGET_ROOTFS_PARTSIZE) $(IMAGE_ROOTFS) \
		32768
	dd if=bd-one-bootloader.bin of=$@ bs=512 seek=64 conv=notrunc
endef

define Device/bendian_bd-one
  DEVICE_VENDOR := BenDian
  DEVICE_MODEL := BD-One
  SOC := rk3568
  DEVICE_DTS := rockchip/rk3568-bd-one
  SUPPORTED_DEVICES := bendian,bd-one
  KERNEL := kernel-bin
  KERNEL_INSTALL := 1
  IMAGE/sysupgrade.img.gz := bd-one-boot | bd-one-img | gzip | append-metadata
  DEVICE_PACKAGES := kmod-ata-ahci-dwc kmod-ata-ahci kmod-nvme kmod-r8169 kmod-igb kmod-phy-realtek kmod-hwmon-gpiofan
endef
TARGET_DEVICES += bendian_bd-one
