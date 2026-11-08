# G68 SPI NOR workflow

在 GitHub Actions 中选择 `nsy-g68-plus-spinor`，点击 **Run workflow**。使用 Ubuntu 22.04 runner 和自动提供的 `GITHUB_TOKEN`。

## 提交文件

- `.github/workflows/nsy-g68-plus-spinor.yml`
- `configs/g68-plus-spinor.config`
- `dts/rk3568-nsy-g68-plus-spiNor.dts`（注意文件名中的大小写）
- `scripts/prepare-g68-spinor.py`
- `boards/g68-spinor/image.mk`
- `boards/g68-spinor/kernel.config`
- `boards/g68-spinor/README.md`

还需保留仓库中已有的 `diy-mini.sh`、`scripts/init-settings.sh`、`scripts/preset-clash-core.sh`、`configfiles/` 及 `patches/bd-one/010-binutils-host-zstd.patch`。

## 构建方式

应用配置基于 `configs/g68-plus-spinand.config`，关闭 NAND capability、ubi-utils、UBIFS extroot/security 选项。原有应用选择保留，根文件系统为 squashfs。

准备脚本在编译前原样复制指定 DTS 到克隆源码的 `rk3568-nsy-g68-plus.dts`，合并 NOR/MTD/squashfs 内核选项，并修改 `Device/nsy_g68-plus` 的 `armv8.mk` 镜像规则，生成裸内核、独立 DTB 和直接用于 NOR 的 squashfs 分区文件。

OpenClash 核心和数据库仅在启用 `luci-app-openclash` 时预装。工具链缓存和 Release 标签使用 SPI NOR 专属前缀。

## 产物与分区

| 上传文件 | 格式 | NOR 偏移 | 分区上限 |
| --- | --- | --- | --- |
| `Image` | 裸 ARM64 内核，用 `booti` 启动 | `0x01400000` | 24 MiB |
| `board.dtb` | 使用指定 DTS 编译的独立 DTB | `0x02c00000` | 512 KiB |
| `rootfs.squashfs` | squashfs 根文件系统 | `0x02c80000` | 19.5 MiB |

三者均上传至 Actions Artifact 和 Release，同时提供输入/最终配置、DTS、源码修改记录及 `g68-spinor-sha256sums`。

以上偏移来自输入 DTS，其 Flash 总容量为 64 MiB。应用较多时可能超出 19.5 MiB rootfs 分区；构建会执行大小检查，需精简 `configs/g68-plus-spinor.config` 中的应用或重新规划硬件实际可用空间后再编译。内核和 DTB 同样检查各自上限。

已有启动程序需要识别本板 SPI NOR，将 `Image` 和 `board.dtb` 加载到不重叠的内存区域后使用 `booti` 启动，并传递 DTS 中的参数：

```text
console=ttyS2,1500000 root=/dev/mtdblock6 rootfstype=squashfs rootwait ro
```

`mtdblock6` 依赖 DTS 中的分区顺序以及没有其他 MTD 设备在它之前注册，实机需核对 `/proc/mtd`。工作流提供三个分区产物，启动程序沿用已适配的 SPI NOR loader/U-Boot。

本工作流尚未完成 GitHub 编译及 G68 实机启动验证。
