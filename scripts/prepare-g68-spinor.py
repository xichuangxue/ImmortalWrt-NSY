#!/usr/bin/env python3
"""Install G68 SPI NOR board support in an OpenWrt checkout."""

import argparse
from pathlib import Path
import re
import shutil


def write_text(path, content):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("openwrt", type=Path)
    parser.add_argument("--dts", type=Path, help="Input board DTS")
    args = parser.parse_args()
    source = args.openwrt.resolve()
    repo = Path(__file__).resolve().parent.parent
    board = repo / "boards/g68-spinor"
    target = source / "target/linux/rockchip"
    if not (target / "image/armv8.mk").is_file():
        parser.error(f"Not a Rockchip OpenWrt checkout: {source}")

    dts = args.dts or repo / "dts/rk3568-nsy-g68-plus-spiNor.dts"
    dts_text = dts.read_text(encoding="utf-8")
    for required in ('"nsy,g68-plus"', 'compatible = "jedec,spi-nor";',
                     'root=/dev/mtdblock6', 'rootfstype=squashfs',
                     'reg = <0x01400000 0x01800000>;',
                     'reg = <0x02c00000 0x00080000>;',
                     'reg = <0x02c80000 0x01380000>;'):
        if required not in dts_text:
            parser.error(f"Review SPI NOR partition/boot changes: missing {required}")
    if 'compatible = "spi-nand";' in dts_text or "ubi.mtd=" in dts_text:
        parser.error("Expected a SPI NOR DTS with a squashfs MTD root filesystem")

    target_mk = target / "Makefile"
    target_text = target_mk.read_text(encoding="utf-8")
    version = re.search(r"^KERNEL_PATCHVER\s*:?=\s*([\d.]+)", target_text, re.M)
    if version is None or version.group(1) != "6.6":
        parser.error("This SPI NOR overlay targets Linux 6.6; review a kernel version change")

    # The application config is derived from NAND, but this target uses NOR.
    features = re.search(r"^(FEATURES\s*:?=)([^\n]*)$", target_text, re.M)
    if features is None:
        parser.error("Cannot locate Rockchip target FEATURES")
    feature_list = [item for item in features.group(2).split() if item != "nand"]
    target_text = (target_text[:features.start()] + features.group(1) +
                   " ".join(feature_list) + target_text[features.end():])
    write_text(target_mk, target_text)

    dts_dest = target / "files/arch/arm64/boot/dts/rockchip/rk3568-nsy-g68-plus.dts"
    dts_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(dts, dts_dest)

    kernel_config = target / "armv8/config-6.6"
    kernel_text = kernel_config.read_text(encoding="utf-8")
    for option in (board / "kernel.config").read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"(CONFIG_\w+)=.+|# (CONFIG_\w+) is not set", option)
        if match is None:
            continue
        symbol = match.group(1) or match.group(2)
        kernel_text = re.sub(rf"^(?:{symbol}=.*|# {symbol} is not set)\n?",
                             "", kernel_text, flags=re.M)
        kernel_text = kernel_text.rstrip() + "\n" + option + "\n"
    write_text(kernel_config, kernel_text)

    profiles = target / "image/armv8.mk"
    profile_text = profiles.read_text(encoding="utf-8")
    matches = list(re.finditer(r"(^define Device/nsy_g68-plus\n)(.*?)(^endef$)",
                              profile_text, re.M | re.S))
    if len(matches) != 1:
        parser.error("Expected exactly one Device/nsy_g68-plus profile")
    match = matches[0]
    # Drop a previously installed local overlay before appending the NOR rules.
    body = re.split(r"^  # BEGIN LOCAL G68 SPI (?:NAND|NOR) IMAGES.*$",
                    match.group(2), maxsplit=1, flags=re.M)[0].rstrip() + "\n"
    body = re.sub(r"(?m)^(\s*DEVICE_PACKAGES\s*:?=)([^\n]*)$",
                  lambda item: item.group(1) + " " +
                  " ".join(word for word in item.group(2).split() if word != "ubi-utils"),
                  body)
    body += "  # BEGIN LOCAL G68 SPI NOR IMAGES\n"
    body += (board / "image.mk").read_text(encoding="utf-8")
    profile_text = (profile_text[:match.start()] + match.group(1) + body +
                    match.group(3) + profile_text[match.end():])
    write_text(profiles, profile_text)

    # An upstream checkout may contain the NAND export hook shown in
    # porting-spinand512.diff; its rootfs.ubi prerequisite is invalid for NOR.
    image_makefile = target / "image/Makefile"
    image_text = image_makefile.read_text(encoding="utf-8")
    hook = (r"(?ms)^ifeq \(\$\(CONFIG_TARGET_rockchip_armv8_DEVICE_nsy_g68-plus\),y\)\n"
            r"(?:(?!^endif\b).)*^endif[^\n]*\n?")
    def remove_nand_export(match):
        text = match.group(0)
        return "" if "g68-flash-images:" in text and "rootfs.ubi" in text else text
    image_text = re.sub(hook, remove_nand_export, image_text)
    write_text(image_makefile, image_text)
    print(f"Installed SPI NOR DTS: {dts_dest}")
    print(f"Configured SPI NOR and squashfs: {kernel_config}")
    print("G68 outputs: raw Image, board.dtb and rootfs.squashfs")


if __name__ == "__main__":
    main()
