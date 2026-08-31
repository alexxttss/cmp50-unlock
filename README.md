# CMP50 Unlock (Multi-GPU Fixed Edition)

[Русская версия](README_RU.md) | [Agent installation runbook (RU)](AGENT_INSTALL_RU.md) | [Prebuilt Release](https://github.com/alexxttss/cmp50-unlock/releases/tag/v610.43.03-multigpu) | [Original project](https://github.com/xrip/cmp50hx-unlock)

An updated, Multi-GPU-compatible mirror of research and patches for the NVIDIA CMP 50HX. The original research and patches were created by **[xrip](https://github.com/xrip)** in **[xrip/cmp50hx-unlock](https://github.com/xrip/cmp50hx-unlock)**.

This repository includes a critical fix for **Multi-GPU / Multi-Card rigs** (e.g. Intel X79 motherboards with 2+ CMP 50HX cards in dual PCIe x16 slots), resolving dynamic WPR2 memory allocation mismatches (`REFWSEC_STATE_MISMATCH`).

---

## Quick Start: Install Prebuilt Driver Binaries (Ubuntu 24.04 / Kernel 6.8)

If you are running Ubuntu 24.04 with Linux Kernel 6.8.x and NVIDIA driver 610.43.03, you can install the prebuilt, hash-verified kernel modules directly without building from source:

```bash
# 1. Download prebuilt driver archive from Release
wget https://github.com/alexxttss/cmp50-unlock/releases/download/v610.43.03-multigpu/cmp50-unlock-prebuilt-610.43.03-ubuntu24.04-kernel6.8.tar.gz

# 2. Extract into kernel modules update directory
sudo mkdir -p /lib/modules/$(uname -r)/updates/cmp50-unlock
sudo tar -xzvf cmp50-unlock-prebuilt-610.43.03-ubuntu24.04-kernel6.8.tar.gz -C /lib/modules/$(uname -r)/updates/cmp50-unlock/

# 3. Update module dependencies and initramfs
sudo depmod -a $(uname -r)
sudo update-initramfs -u -k $(uname -r)

# 4. Reboot system
sudo reboot
```

After rebooting, verify that both GPUs are active:
```bash
nvidia-smi -L
nvidia-smi
```

---

## Scope & Specifications

| Field | Value |
| --- | --- |
| GPU | NVIDIA CMP 50HX / TU102 |
| PCI vendor/device | `10de:1e09` |
| NVIDIA subsystem | `10de:1554` |
| MSI subsystem | `1462:371f` |
| Driver source | NVIDIA open-gpu-kernel-modules `610.43.03` |

### Ordered Patch Set

1. `01-cmp50-stockflow.patch` — GSP/RM stockflow, SM issue-rate path, and **Multi-GPU dynamic WPR2 memory range fix**.
2. `02-cmp50-rt-core-count.patch` — Host-side RT core count reporting.
3. `03-cmp50-rebar.patch` — CMP50-specific Resizable BAR setup.
4. `04-cmp50-pcie-gen2.patch` — PCIe endpoint & upstream-bridge Gen2 retraining.

---

## Building from Source

To build from source on your target Linux machine:

```bash
# Clone repository
git clone https://github.com/alexxttss/cmp50-unlock.git
cd cmp50-unlock

# Run automated build script (downloads open-gpu-kernel-modules 610.43.03, verifies SHA256, applies patches)
bash ./build.sh

# Install compiled modules
kernel_release="$(uname -r)"
sudo mkdir -p "/lib/modules/${kernel_release}/updates/cmp50-unlock"
sudo cp -a artifacts/610.43.03-${kernel_release}/*.ko "/lib/modules/${kernel_release}/updates/cmp50-unlock/"
sudo depmod -a "${kernel_release}"
sudo update-initramfs -u -k "${kernel_release}"
sudo reboot
```

---

## LLM Optimization (llama.cpp)

To achieve **500+ tokens/sec Prompt Processing** and 2x faster token generation with `llama.cpp` on CMP 50HX:

Use the `DISABLE_DP4A` (DP2A emulation) patch by **[arabel1a](https://github.com/arabel1a)** ([llama.cpp #24616](https://github.com/ggml-org/llama.cpp/pull/24616)) when compiling `llama.cpp`:

```bash
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_FLAGS="-DDISABLE_DP4A --fmad=false"
cmake --build build -j --config Release
```

---

## Rollback / Recovery Instructions

To revert back to stock NVIDIA kernel modules:

```bash
sudo rm -rf /lib/modules/$(uname -r)/updates/cmp50-unlock
sudo depmod -a $(uname -r)
sudo update-initramfs -u -k $(uname -r)
sudo reboot
```

---

## Attribution & Acknowledgments

### CMP50 Unlock Kernel Driver Research & Patches
- Author: **[xrip](https://github.com/xrip)**
- Original Repository: **[github.com/xrip/cmp50hx-unlock](https://github.com/xrip/cmp50hx-unlock)**

### LLM DP2A / DISABLE_DP4A Emulation Research
- Author: **[arabel1a](https://github.com/arabel1a)**
- Research & Microbenchmarks: **[arabel1a/ml-on-cmp](https://github.com/arabel1a/ml-on-cmp)**
- llama.cpp Issue & PR: **[llama.cpp#24616](https://github.com/ggml-org/llama.cpp/pull/24616)**

## ⚡ Dynamic Idle Power Management Daemon

CMP 50HX GPUs draw ~85W per card in idle state P0 because driver-level power limits cannot be reduced below 100W via \`nvidia-smi -pl\`.

We provide an ultra-lightweight dynamic power daemon (\`tools/power-daemon/cmp-power-daemon.py\`) that monitors GPU utilization using NVML C bindings:
- **Idle (utilization = 0% for >1s):** Automatically locks GPU clocks to 300 MHz (\`nvmlDeviceSetGpuLockedClocks\`), reducing idle power to **~50-60W per card** (saving ~55W total idle power across dual cards).
- **Active (utilization > 0%):** Instantly unlocks clocks back to dynamic Boost (1800+ MHz) in sub-millisecond time with zero latency or performance degradation during LLM inference.

### Installation
```bash
sudo cp tools/power-daemon/cmp-power-daemon.py /usr/local/bin/
sudo chmod +x /usr/local/bin/cmp-power-daemon.py
sudo cp tools/power-daemon/cmp-power-daemon.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cmp-power-daemon.service
```

## 🚀 PCIe Gen 3 & Gen 2 Auto-Negotiation Unlock

CMP 50HX cards are factory-locked to PCIe Gen 1 (2.5 GT/s) in VBIOS descriptor endpoints.

Our driver includes an automated PCIe link retrain engine (\`patches/04-cmp50-pcie-gen3.patch\`):
- **On PCIe 3.0 Hosts (X99, Ivy Bridge-E v2, Ryzen, modern Intel/AMD):** Automatically negotiates **PCIe Gen 3 (8.0 GT/s)** doubling bus throughput to **~15.8 GB/s** on x16 links.
- **On Legacy PCIe 2.0 Hosts (X79 Sandy Bridge-E v1):** Automatically falls back to **PCIe Gen 2 (5.0 GT/s)** for maximum stability without signal dropouts.
