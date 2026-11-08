#!/usr/bin/env python3
"""Install the supplied G68 SPI NAND DTS, kernel options and image rules."""

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
    board = repo / "g68-spi-nand"
    target = source / "target/linux/rockchip"
    if not (target / "image/armv8.mk").is_file():
        parser.error(f"Not a Rockchip OpenWrt checkout: {source}")

    # The supplied OpenWrt config selects the existing nsy_g68-plus profile.
    # Keep that profile's DTS filename so the replacement is actually compiled.
    dts = args.dts or repo / "dts/rk3568-nsy-g68-plus-spinand.dts"
    dts_text = dts.read_text(encoding="utf-8")
    for required in ('"nsy,g68-plus"', 'compatible = "spi-nand";',
                     'label = "ubi";', 'reg = <0x05500000 0x1a900000>;'):
        if required not in dts_text:
            parser.error(f"Review SPI NAND geometry/partition changes: missing {required}")
    dts_dest = target / "files/arch/arm64/boot/dts/rockchip/rk3568-nsy-g68-plus.dts"
    dts_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(dts, dts_dest)

    # NAND_SUPPORT is derived from target features; an input .config entry alone
    # is discarded by defconfig unless the target advertises NAND capability.
    target_mk = target / "Makefile"
    target_text = target_mk.read_text(encoding="utf-8")
    match = re.search(r"^FEATURES\s*:?=([^\n]*)$", target_text, re.M)
    if match is None:
        parser.error("Cannot locate Rockchip target FEATURES")
    if "nand" not in match.group(1).split():
        target_text = target_text[:match.end()] + " nand" + target_text[match.end():]
        write_text(target_mk, target_text)

    # Merge into the target kernel config, not the OpenWrt package .config.
    version = re.search(r"^KERNEL_PATCHVER\s*:?=\s*([\d.]+)", target_text, re.M)
    if version is None or version.group(1) != "6.6":
        parser.error("This SPI NAND overlay targets Linux 6.6; review a kernel version change")
    kernel_config = target / "armv8/config-6.6"
    kernel_text = kernel_config.read_text(encoding="utf-8")
    for option in (board / "kernel.config").read_text(encoding="utf-8").splitlines():
        if not option.startswith("CONFIG_"):
            continue
        symbol = option.split("=", 1)[0]
        kernel_text = re.sub(rf"^(?:{symbol}=.*|# {symbol} is not set)\n?",
                             "", kernel_text, flags=re.M)
        kernel_text = kernel_text.rstrip() + "\n" + option + "\n"
    write_text(kernel_config, kernel_text)

    profiles = target / "image/armv8.mk"
    profile_text = profiles.read_text(encoding="utf-8")
    pattern = r"(^define Device/nsy_g68-plus\n)(.*?)(^endef$)"
    matches = list(re.finditer(pattern, profile_text, re.M | re.S))
    if len(matches) != 1:
        parser.error("Expected exactly one Device/nsy_g68-plus profile")
    match = matches[0]
    marker = "  # BEGIN LOCAL G68 SPI NAND IMAGES"
    body = match.group(2).split(marker, 1)[0].rstrip() + "\n"
    body += marker + "\n" + (board / "image.mk").read_text(encoding="utf-8")
    profile_text = (profile_text[:match.start()] + match.group(1) + body +
                    match.group(3) + profile_text[match.end():])
    write_text(profiles, profile_text)
    print(f"Installed SPI NAND DTS: {dts_dest}")
    print(f"Enabled SPI NAND/UBI kernel options: {kernel_config}")
    print("G68 outputs: raw Image, board.dtb, rootfs.ubi and rootfs.squashfs")


if __name__ == "__main__":
    main()
