# G68 SPI NAND workflow

在 GitHub Actions 中运行 `nsy-g68-plus-spinand`。使用 Ubuntu 22.04 runner、仓库自带的 `GITHUB_TOKEN` 和独立工具链缓存。

## 输入及构建方式

- `../configs/g68-plus-spinand.config`：OpenWrt 应用配置；构建时额外开启 rootfs.tar.gz 导出。
- `../dts/rk3568-nsy-g68-plus-spinand.dts`：原样覆盖克隆源码中的 `rk3568-nsy-g68-plus.dts`，沿用 `nsy_g68-plus` 设备选择。
- `kernel.config`：合并到 Linux 6.6 的 Rockchip armv8 内核配置，将 SPI NAND、UBI、ubiblock、UBIFS 编译进内核。
- `image.mk`：覆盖本次构建的 G68 镜像规则，生成独立内核及 NAND 根文件系统分区镜像。
- `../scripts/prepare-g68-spinand.py`：安装以上文件及 NAND target feature。
- `../patches/bd-one/010-binutils-host-zstd.patch`：复用已有 binutils 主机端 zstd 修复；与 BD-One 启动程序无关。

原始 DTS、应用 config 保留不变，实际 OpenWrt 配置导出为 `build.config`，实际内核配置导出为 `kernel-build.config`。

## 产物

| 文件 | 格式及用途 |
| --- | --- |
| `Image` | 裸 ARM64 内核，供已有启动程序配合独立 DTB 使用 `booti` 加载 |
| `board.dtb` | 本次编译的独立设备树，同时以 `rk3568-nsy-g68-plus-spinand.dtb` 归档 |
| `rootfs.ubi` | 4 KiB 页、256 KiB 擦除块；volume 0 为 squashfs `rootfs`，另含自动扩展的 `rootfs_data` 卷 |
| `rootfs.squashfs` | 未封装 UBI 的根文件系统，用于已有 UBI 卷的维护 |
| `rootfs.tar.gz` | 根文件系统归档 |
| `g68-spinand-sha256sums` | 主要产物校验值 |

`Image`、`board.dtb`、`rootfs.ubi` 按 `porting-spinand512.diff` 第 152～154 行的约定整理至 `bin/target/rockchip/armv8/`，再上传到 Actions Artifact 和 Release。这里的 `target` 为单数，与 OpenWrt 常规 `bin/targets/` 目录不同。

## 分区约定与启动条件

分区来自输入 DTS，Flash 总容量为 512 MiB：

| 分区 | 起始偏移 | 大小 |
| --- | --- | --- |
| loader | `0x00000000` | 8 MiB |
| uboot | `0x00800000` | 4 MiB |
| trust | `0x00c00000` | 4 MiB |
| misc | `0x01000000` | 4 MiB |
| kernel | `0x01400000` | 64 MiB |
| dtb | `0x05400000` | 1 MiB |
| ubi | `0x05500000` | 425 MiB |

输入 DTS 的启动参数为：

```text
console=ttyS2,1500000 ubi.mtd=ubi ubi.block=0,rootfs root=/dev/ubiblock0_0 rootfstype=squashfs rootwait ro
```

已有启动程序需要支持本板 SPI NAND，按以上分区加载 `Image` 和 `board.dtb`，并传递这些启动参数，使用 `booti` 启动。

本工作流提供分区产物，不包含已适配 SPI NAND 启动的 loader、U-Boot 或 trust，也不生成整片 Flash 镜像。输入 config 选择的现有 G68 U-Boot 包可能仍会参与源码构建，其配置不代表已完成 NAND 启动适配。

`rootfs.ubi` 面向 `ubi` 分区，应由支持坏块管理的 NAND/UBI 工具写入；原有 SD/eMMC `sysupgrade.img.gz` 的布局不适用于这些分区。Rockchip 平台的 NAND 在线 sysupgrade 流程尚未在本工作流中适配。

DTS 注释写的是 `MT29F4G01ABBFD`；芯片实际识别由驱动读取 ID 完成，本工作流未更改该注释或硬件供电设置。

本工作流尚需 GitHub 编译及 G68 实机启动验证。
