#!/usr/bin/env python3
"""Install the BD-One profile and vendor boot payload into an OpenWrt checkout."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("openwrt", type=Path)
    parser.add_argument("--network-mode", choices=("router", "lan"), default="router")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parent.parent
    source = args.openwrt.resolve()
    image_dir = source / "target/linux/rockchip/image"
    profiles = image_dir / "armv8.mk"
    if not profiles.is_file():
        parser.error(f"Not a rockchip OpenWrt source checkout: {source}")

    board = repo / "boards/bd-one"
    manifest = json.loads((board / "bootloader.json").read_text(encoding="utf-8"))
    compressed = (board / "bootloader.bin.gz").read_bytes()
    if hashlib.sha256(compressed).hexdigest() != manifest["gzip_sha256"]:
        raise SystemExit("BD-One compressed bootloader checksum mismatch")
    payload = gzip.decompress(compressed)
    if len(payload) != manifest["length_bytes"]:
        raise SystemExit("BD-One bootloader length mismatch")
    if hashlib.sha256(payload).hexdigest() != manifest["sha256"]:
        raise SystemExit("BD-One bootloader checksum mismatch")
    if manifest["offset_bytes"] != 64 * 512 or len(payload) != 16744448:
        raise SystemExit("Unexpected BD-One bootloader placement")

    dts = repo / "dts/rk3568-bd-one.dts"
    dts_text = dts.read_text(encoding="utf-8")
    if 'compatible = "bendian,bd-one\\0rockchip,rk3568";' not in dts_text:
        raise SystemExit("The DTS does not identify a BenDian BD-One")
    # The vendor export assigns ComboPHY0 to both SATA0 and USB3OTG0.
    # Keep the two physical SATA ports and retain USB2 on this USB controller.
    usb = re.search(r"\tusb@fcc00000 \{\n.*?\n\t\};", dts_text, re.S)
    if usb is None:
        raise SystemExit("Cannot locate the expected BD-One USB0 controller")
    usb_text = usb.group()
    if 'phys = <0x12 0x13 0x04>;' not in usb_text:
        raise SystemExit("Review the BD-One SATA0/USB0 PHY mapping before building")
    usb_text = usb_text.replace('phys = <0x12 0x13 0x04>;', 'phys = <0x12>;')
    usb_text = usb_text.replace('phy-names = "usb2-phy\\0usb3-phy";', 'phy-names = "usb2-phy";\n\t\tmaximum-speed = "high-speed";')
    dts_text = dts_text[:usb.start()] + usb_text + dts_text[usb.end():]
    dts_dest = source / "target/linux/rockchip/files/arch/arm64/boot/dts/rockchip" / dts.name
    dts_dest.parent.mkdir(parents=True, exist_ok=True)
    with dts_dest.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(dts_text)

    marker = "# BEGIN LOCAL BD-ONE PROFILE"
    profile_text = profiles.read_text(encoding="utf-8")
    if marker in profile_text:
        profile_text = profile_text.split(marker, 1)[0]
    elif "define Device/bendian_bd-one" in profile_text:
        raise SystemExit("Upstream already defines BD-One; review the local profile before overriding it")
    profile_text = profile_text.rstrip() + "\n\n" + marker + "\n"
    profile_text += (board / "image.mk").read_text(encoding="utf-8")
    with profiles.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(profile_text)
    shutil.copyfile(board / "bd-one.bootscript", image_dir / "bd-one.bootscript")
    (image_dir / "bd-one-bootloader.bin").write_bytes(payload)

    network = source / "files/etc/board.d/03_bd-one-network"
    network.parent.mkdir(parents=True, exist_ok=True)
    network_text = (board / "03_bd-one-network").read_text(encoding="utf-8")
    network_text = network_text.replace("@NETWORK_MODE@", args.network_mode)
    with network.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(network_text)
    network.chmod(0o755)

    print(f"BD-One original DTS SHA256: {hashlib.sha256(dts.read_bytes()).hexdigest()}")
    print(f"BD-One build DTS SHA256: {hashlib.sha256(dts_dest.read_bytes()).hexdigest()}")
    print(f"BD-One bootloader SHA256: {manifest['sha256']}")
    print(f"BD-One network mode: {args.network_mode}")
    print("Registered profile: CONFIG_TARGET_rockchip_armv8_DEVICE_bendian_bd-one")


if __name__ == "__main__":
    main()
