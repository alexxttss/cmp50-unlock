# CMP 50HX research path

Status: the authenticated stockflow path is now installed and live-tested on a
CMP 50HX. Full SM and Tensor work is proved. A separate host RT-count patch
also proved that the zero count is an API exposure gate. A read-only live SM
trace proves that the first ray-query machine-code group raises warp error 9,
`INVALID_OPCODE`, at decode, before FECS stalls and reports Xid 109; the
faulting address latches deterministically at `0x738`/`0x73c` and repeats across
reboot. As of 2026-08-12, real RT execution is assessed as not achievable by any
software or firmware change: the gate is a physical RT floorsweep fuse the SM
samples at reset, below every writable register reached by the driver, GSP-RM,
the signed Booter, the netlist, and the FECS feature override. See the
feasibility assessment below. The compute path is unaffected.
On 2026-08-13, a board-gated NVIDIA kernel-module change also made the CMP
BAR1 aperture 16 GiB. The state survived a cold boot and passed the compute,
Tensor, and OpenCL checks below.
The same all-feature module now also opens the protected TU102 PCIe policy and
trains the card at PCIe Gen2 x4. A clean package build survived a cold boot,
passed every live check, and doubled measured host-transfer bandwidth without
a compute or VRAM-bandwidth regression.

## Target

The target is PCI ID `10de:1e09`, a Turing `TU102` CMP 50HX with 56 SMs and
3584 CUDA cores. It is not an RTX 2080 die: RTX 2080 uses TU104. The useful
target is normal RTX-class Turing behavior from the enabled TU102 units, with
the stock 10 GB memory layout left unchanged.

### End-user all-feature package

[`packages/cmp50hx-all-610.43.03`](../packages/cmp50hx-all-610.43.03/README.md)
is the single supported build path for all proved CMP 50HX changes. It combines
the full instruction issue-rate path, the board-scoped 56 RT-core report, and
the 16 GiB BAR1 ReBAR path, and the board-scoped PCIe Gen2 path in one clean
patch against NVIDIA's official `610.43.03` source tag. It also checks the
per-patch source and IDA evidence in
[`packages/cmp50hx-all-610.43.03/patches/README.md`](../packages/cmp50hx-all-610.43.03/patches/README.md).
natural 3584 CUDA and 448 Tensor counts after reboot.

The package checks source and artifact hashes, the running kernel ABI, PCI ID,
PCI class, and the tested `10de:1554` or `1462:371f` subsystem before install.
It saves rollback data, does not unload the live driver, and includes one live
verification command. The full remote build passed on kernel
`6.8.0-137-generic` on 2026-08-13.

This package does not claim real RT execution, a link wider than x4, display,
NVDEC, or NVENC. The 56 RT-core value opens the host API only; the physical RT
execution fuse remains closed.

### Host ReBAR state

On 2026-08-13 the Gigabyte AB350M-DS3H V2 test host was updated to modified F54
firmware with ReBarDxe 0.3. `ReBarState=32` enables automatic selection of the
largest size advertised by each device. After reboot, Ryzen 3 2200G Vega BAR0
was 1 GB and BAR2 was 256 MB, both GPU drivers loaded, and Linux reported zero
PCI resource-allocation errors. The image hashes, flash path, and full host
check are in
[`artifacts/ab350m-ds3h-v2-rebar-f54/VERIFY.md`](../artifacts/ab350m-ds3h-v2-rebar-f54/VERIFY.md).

The CMP path is now also working, through the NVIDIA kernel module rather than
UEFI. On PCI ID `10de:1e09`, module parameter `cmp50_rebar_size=8` changes the
TU102 XVE ReBAR selector at BAR0 `0x88dcc` from `0` to `8` and its size mask at
`0x88bbc` from `0x400` to `0x7fc00`. The normal NVIDIA BAR resize path then
rebuilds the bridge window and assigns a 16 GiB BAR1 aperture. The earlier
PSTRAPS path at `0x101000`/`0x10100c` did not accept the size write; it is not
used by the working patch.

The change was first tested by a live module swap at 128 MiB, then at 16 GiB.
It was installed in initramfs and proved again after a cold boot into kernel
`6.8.0-137-generic`. Linux reports Region 1 as `size=16G`; `nvidia-smi` reports
BAR1 total `16384 MiB`; the card stays in P0 and keeps the full issue-rate
override, 3584 CUDA cores, 448 Tensor cores, and the host-side report of 56 RT
cores. The final all-feature `nvidia.ko` SHA-256 is
`cb320f3ffc89892cf9938a569c2f8919d4eee3a4b3c466353ddf0a4580593798`.
Its latest package rollback is
`/var/lib/cmp50hx-all/backups/20260813T094002Z`; the original ReBAR-only
pre-install files remain at `/var/tmp/cmp50-rebar-install-backup-20260813T0745Z`.
Source, patch, live-swap tool, register proof, and rollback notes are in
[`experiments/cmp50-rebar-kernel`](../experiments/cmp50-rebar-kernel/README.md).

## Evidence levels

This is an R&D project. Each claim uses one of these levels:

1. **Read-only observation:** data returned by the target card, RM, PCI sysfs,
   or a benchmark.
2. **IDA-backed finding:** a path proved in the exact GSP image, but not yet
   tested on the card.
3. **Stockflow evidence:** a mechanism visible in the audited patch, with a
   hardware result reported by its authors.
4. **Local hardware result:** the same before/write/after test run by us. This
   level now exists for stockflow, Tensor work, the RT-count gate, and the RT
   execution failure below.

An address found in firmware is not, by itself, proof that a host write is safe
or that the write changes performance.

## Feasibility assessment for real RT execution, 2026-08-13

This section states the current answer to the project's RT-execution goal and
grades the evidence. Short form: **no software-reachable state has been found
that makes the SM accept the ray-query opcodes, and every privilege level and
state class that could plausibly hold such a gate has now been checked and
excluded except one that cannot be tested here.** The remaining gate behaves as
a physical RT floorsweep fuse sampled by the SM at reset.

### What is proved on this card

1. The first ray-query instruction faults inside the SM with warp error 9,
   `INVALID_OPCODE`, at instruction decode. It is deterministic: the same SM,
   `GPC2/TPC0/SM0`, latches the same faulting address `0xdf5ea5bc10` on two runs
   separated by a reboot (`runs/20260812T1240Z-esr-addr`,
   `runs/20260812T1300Z-esr-addr-repeat`). A hardware decode rejection cannot be
   satisfied by changing any later reporting or exception-handling code.
2. The RT fuse `0x21168` reads zero, and both of the only two GSP readers of its
   OBJFUSE ID `0xff00008e` (`0x529b5a0`, `0x52bcefc`) use it solely to compute a
   reported core count. Neither writes SM, clock, power, context, or dispatch
   state. Raising the reported count to 56, which this project already does,
   therefore exposes the API without enabling execution.
3. The three GR init registers that separate an RT-capable TU102 from a non-RT
   TU116 (`0x419bc8`, `0x419bf0`, `0x419e5c`) reach the RT-capable TU102 values
   live, but a ten-phase read-only timeline shows exactly how. After GSP init
   the tuple is mixed: `00398a2c/844077fe/00005cc1`. It stays unchanged through
   graphics state load and static-info load. Only
   `kgraphicsCreateGoldenImageChannel` changes the last two words, producing
   `00398a2c/944077fe/000058c1`. These registers are golden-context state, not
   the fixed opcode gate. Full evidence is in
   `experiments/cmp50-rt-register-timeline`.
4. The RT fuse shadow does not accept an overriding write even at the highest
   privilege in the boot chain. A normal host BAR0 write does not stick, and the
   signed Booter write of `1` to `0x21168`, performed before GSP-RM starts, read
   back zero both immediately and after GSP ready
   (`experiments/cmp50-rt-fuse-booter`).
5. The FECS feature-override block at `0x409650..0x40966c`, which the stockflow
   payload already opens and writes for SM issue-rate, is not an RT gate. Its
   registers govern issue-rate throttle and FECS-level features; the feature
   readout `0x409660 = 0xf3` is consumed by FECS falcon ucode, and GSP-RM reads
   it only as the diagnostic the stockflow patch added. It has no literal reader
   in the GSP image that branches on it for RT.
6. An exhaustive direct-OBJFUSE audit found only five GSP callers of the
   `readFuseById` HAL slot. The only RT ID is `0xff00008e`, and it feeds the
   count reader at `0x529b5a0`; the other IDs are unrelated masks. Symbolic
   execution of the full OBJFUSE HAL initializer for TU102 through TU117
   (`HalVarIdx 37..41`) found 67 installed slots and no RT/non-RT split.
7. The same trace over all 489 KernelGraphics HAL slots found only 20 methods
   that split exactly between RT-capable TU102/TU104/TU106 and non-RT
   TU116/TU117. The known RT context/layout methods are identical. The split
   methods reduce to count/reporting, ECC or chip workarounds; in particular,
   the TU116/TU117 `+0xc88` wrapper only changes register-map ID `0x444` after
   the common init method. No method controls SM ray-opcode legality.
8. The 18 differing FECS bytes are only nine call targets. TU102 target
   `0x72a3` and TU116 target `0x6ffb` contain the same byte-for-byte 32-bit
   multiply helper. This closes the last apparent FECS code delta as an RT
   gate. Full evidence is in `experiments/cmp50-rt-opcode-gate`.
9. A two-read live CMP VBIOS dump matches every option-ROM chain in the
   supplied CMP update image. Against the supplied RTX 2080 Ti image, all 41
   valid six-digit GR register operations decoded by envytools are identical.
   Neither image contains a raw reference to RT fuse `0x21168` or the three RT
   netlist words. No RTX-only VBIOS GR init write exists in the decoded path.
   Full evidence is in `experiments/cmp50-vbios-comparison`.

### What remains untested, and why the prior is low

- A distinct fuse-override register that could force the SM's sampled RT value.
  The fuse block at `0x21000+` is a hardware fuse controller; its writable
  shadow already rejects a signed-Booter write (point 4), which is the strongest
  privilege available here. An override that reaches the SM decoder, if one
  exists, would have to outrank that, which no NVIDIA firmware path in the GSP
  image does.
- A read-only live comparison against a real RTX TU102 (milestone 3). The
  VBIOS-side comparison is now done and found no RTX-only GR init operation,
  but a ROM cannot expose live sampled fuse or post-GR state. No RTX TU102 card
  is available. Until it is, the impossibility claim is "no software path found
  and every checked class excluded", not "proved for the silicon".

### Conclusion

For a software and firmware unlock, which is the scope of this project, real RT
execution on CMP 50HX is assessed as **not achievable**: the gate is a
hardware decode property fixed by a physical fuse the SM samples at reset, below
every writable register reached by the driver, GSP-RM, the signed Booter, the
netlist, and the FECS feature override. The positive goal, 56 reporting RT cores
with a working ray pipeline, stops at API exposure. The only ways past it that
remain are outside software: a real RTX TU102 reference to disprove the fuse
model, or physical fuse work. Neither is a driver change.

This does not weaken the compute result. Full SM speed, 3584 CUDA cores, 448
Tensor cores, and the 10 GB layout are unaffected and still pass.

## Live hardware checkpoint: 2026-08-11

The test card is a `10de:1e09` CMP 50HX on Linux with the NVIDIA 610.43.03
open kernel module. The V551 stockflow patch and the board-scoped RT-count
override are installed and survive reboot. After a clean boot the card enters
P0, reports full issue rates, and runs at about `1905 MHz` during the checks,
with a reported `2100 MHz` SM maximum. The post-reboot checks below were made
on 2026-08-11 and the kernel log had no new Xid.

The 2026-08-12 console capture also contains older
`POST_FWSEC_COMMIT_FAIL`/`rm_init_adapter failed` lines from warm module-load
attempts. They precede the final successful `SIGNED_FULLSPEED_STOCK_RELOCK`,
`GSP_READY`, and DRM initialization lines. A warm load on this host needs a PCI
function reset before loading the module; otherwise those old failures can be
mistaken for the current state. The final `No compatible format found` and
`Cannot find any crtc or sizes` messages are display/KMS scanout warnings on
the headless CMP board, not CUDA, Tensor, or RT execution errors.

### Proved working

- RM reports `3584` CUDA cores and `448` Tensor cores.
- The corrected FP16 WMMA test gives correct output and about
  `107.1-107.2 TFLOPS` through real HMMA instructions.
- The full-speed stockflow state is repeatable after a module reload. Its FECS
  speed readout is zero, which is the full-speed value.

Tensor work is therefore already unlocked. There is no current Tensor feature
patch to add. LLM work should use the normal CUDA/Tensor path.

### Full-speed performance matrix and raster gate, 2026-08-17

A fresh read-only performance pass was made on the installed all-feature
610.43.03 package. The new low-level tests were built in `/var/tmp`; no system
library, module, firmware, clock, or power setting changed.

| Path | Fresh result |
|---|---:|
| RM issue-rate and core-count gate | `PASS_CMP50HX_ISSUE_RATE_AND_COUNTS` |
| DP4A issue test | `2782.423` G thread-instructions/s |
| DP2A-pair issue test | `4435.777` G thread-instructions/s |
| FFMA issue test | `2584.518` G thread-instructions/s |
| FMUL+FADD issue test | `4404.997` G thread-instructions/s |
| FP16 Tensor WMMA | `106.819 TFLOPS`, exact sample check passed |
| OpenCL FP32 | `13.501 TFLOPS` |
| OpenCL coalesced read/write | `504.98 / 474.54 GB/s` |
| Pinned CUDA PCIe H2D/D2H | `1.702 / 1.709 GB/s`, data check passed |
| Vulkan raster, five long runs | `99.65-100.01 Gpix/s`, mean `99.782` |
| Vulkan pixel check | `8192/65536` orange pixels, pass |

All 79 combined-test telemetry samples stayed in P0 at `1905 MHz`. Power was
`61.43-118.15 W`, temperature was `42-46 C`, and no new NVRM, Xid, AER, or
PCIe error appeared. The separate OpenCL run also ended cleanly at P0 with no
VRAM allocation left.

The raster source from PR #30 is now a regular optional test under
`tools/cmp50/raster`. This copy fixes C11 clock visibility and keeps Vulkan
`lineWidth=1.0f`. The PR's GA102 `0x823xxx` register block is unmapped on this
TU102 card, while the corrected test is already near `100 Gpix/s`; none of the
PR register writes should be ported.

The verifier was also made quiet. It no longer sends the unsupported SM
throttle-control GET or the `ALLENGINES=0xffffffff` class-list GET. The parser
never used these optional results. The rebuilt verifier kept the full package
pass and produced zero new NVRM lines.

The IDA check now closes the indirect firmware path. TU102 stores callback
`0x528f508` in `Graphics+0xb08`. Function
`kgraphicsApplyInitOverrides_inferred` loads that slot and calls it at
`0x52a5a4c` for `RMOverrideSmSpeedSelect`, and at `0x52a5a8c` for
`RMOverrideSmSpeedSelect1`. The callback constructs only register-map IDs
`0x9664` and `0x966c`. A raw RISC-V instruction scan found no matching
`0x9670` or `0x9674` construction in this path. The old IDB comment that sent
this TU102 path to the alternate OBJFUSE callback was corrected and saved.

BAR0 `0x409670` remains a read-only research point, not an unlock candidate.
There is no checked firmware use or measured speed limit that supports a write.
Raw output and hashes are in
[`artifacts/cmp50-performance-matrix-20260817`](../artifacts/cmp50-performance-matrix-20260817/VERIFY.md).

A short `llama.cpp` hardware smoke test on 2026-08-12 loaded the 12 GB
`Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf` model with the fit planner using about
`8700 MiB` of the 10 GB card. It produced valid output at about `44.5` prompt
tokens/s and `42.6` generation tokens/s. The 240-second wrapper ended only
because `llama-cli` stayed at its interactive prompt after generation. No
process or new NVRM/Xid error remained, and the card returned to P0 with zero
VRAM use. This is a smoke result, not a standardized model benchmark.

### llama.cpp benchmark: Qwen3.6 35B.A3B

The existing CUDA-enabled llama.cpp tree at `/var/tmp/llama.cpp` was completed
with the `llama-bench` target and run on the same card. The benchmark used the
local `/var/tmp/Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf` model, three repetitions, an
8,192-token fit context, Q8 KV cache, Flash Attention, and `2048/2048`
batch/ubatch sizes. Exact command and raw JSON are in
`experiments/cmp50-llama-bench/runs/20260812T065300Z`.

| Phase | Mean | Spread |
|---|---:|---:|
| Prompt, 512 tokens | `264.292 t/s` | `5.924 t/s` |
| Generation, 128 tokens | `48.429 t/s` | `0.665 t/s` |

Both phases completed with exit code 0. This is higher than the earlier
interactive smoke result because `llama-bench` excludes tokenization, sampling,
and interactive prompt overhead. The model is about `11.8 GB` while the card
has `9798 MiB` visible VRAM, so the run uses llama.cpp's fit planner and is not
an all-GPU 35B measurement. It is nevertheless a valid end-to-end CUDA result
for the current 10 GB CMP configuration.

An initial batch sweep with `n_ubatch=512` found the best generation mean at
`n_batch=512` (`48.960 t/s`), while prompt throughput peaked at
`n_batch=2048` (`266.682 t/s`). This is not yet the final setting: larger
ubatches still need a focused comparison. The sweep data is in the session's
remote `/var/tmp/cmp50-llama-batch-stage1-20260812T070000Z.json` output.

The GPU stayed healthy: P0 at `1905 MHz`, `40 C` before and `43 C` after, with
zero VRAM use reported after the run. This confirms that the stockflow compute
path supports useful LLM inference throughput. It predates and does not measure
the later PCIe Gen2 unlock.

### llama.cpp benchmark: Qwen3.5 9B Q4_K_XL

The downloaded `unsloth/Qwen3.5-9B-MTP-GGUF` quant was then benchmarked with
the same CUDA-enabled `llama-bench` target, three repetitions, an 8,192-token
fit context, Q8 KV cache, Flash Attention, and `2048/2048` batch/ubatch sizes.
The exact command and raw evidence are in
`experiments/cmp50-llama-bench/runs/20260812T071937Z`.

| Phase | Mean | Spread |
|---|---:|---:|
| Prompt, 512 tokens | `1888.711 t/s` | `64.452 t/s` |
| Generation, 128 tokens | `68.052 t/s` | `0.080 t/s` |

The model file is `6135034208` bytes with SHA-256
`362f85a2d7dbc0259e926d5ac33ca0d0f17fd3753496d65bfd2106384c929d3f`. Relative
to the earlier Qwen3.6 35B.A3B quant at `264.292` prompt t/s and `48.429`
generation t/s, this 9B quant is about `7.15x` faster for prompt processing
and `1.41x` faster for generation. This is a model-size result, not evidence
of an additional RTX 2080 Ti hardware feature.

The card reported `9798 MiB` visible VRAM and compute capability `7.5`; it
stayed at P0, rose from `43 C` to `48 C`, and returned to `0 MiB` VRAM use
after the run.

### Real one-shot answer

To measure an actual user request, `llama-cli` was run with the exact prompt:

> I want to wash my car. The car wash is only 100m away from my house, should i walk or drive?

The final invocation used the Qwen chat template, `--single-turn` (`-st`),
reasoning disabled for a concise response, a fixed seed, and a 512-token cap.
The exact transcript and before/after GPU captures are in
`experiments/cmp50-llama-bench/runs/20260812T073126Z`.

```text
[ Prompt: 244.9 t/s | Generation: 65.6 t/s ]
```

The model completed its answer and recommended driving because the car must be
present at the wash; it noted walking only makes sense if the user wants a
short exercise or to save a small amount of fuel. The process exited cleanly,
and the card returned from `42 C` to `47 C` with `0 MiB` VRAM use.

`-st` is essential: `-cnv` without `-st` left `llama-cli` waiting for another
interactive turn. A focused batch sweep for this smaller model remains the
next useful LLM measurement.

### Linux undervolt investigation

The remote host was checked before changing any power setting. The CMP 50HX
reports a `225 W` current/default/max power limit range of `100-225 W`, and
the baseline `llama-cli` run peaked at `230.46 W` according to the GPU's
instantaneous power samples while running at up to `1905 MHz` SM and `7000 MHz`
memory. The run produced `194.7` prompt tokens/s and `72.5` generation
tokens/s, completed with no CUDA stderr, and reached `55 C`.

This Linux driver does not expose a direct millivolt or fixed-point voltage
setter through `nvidia-smi`: `-q -d VOLTAGE` returns no usable GPU voltage
field. It does expose the older NVML GPC VF offset control on this CMP. A
read-only probe reports the current offset as `0` and an accepted range of
`-1000..1000`. The offset is a curve-equivalent control; the actual voltage in
millivolts remains hidden. The normal supported headless controls are a power
cap (`nvidia-smi -pl`), a GPC VF offset, and a locked GPU clock, all reversible
with the documented reset commands.

There is a closer MSI-Afterburner-like Linux path through `nvidia-settings`
and the NV-CONTROL X extension: Coolbits plus
`GPUGraphicsClockOffsetAllPerformanceLevels`. The public `gpu_undervolt`
script uses this method, but requires Ubuntu Desktop/Xorg and Coolbits, and
its tested-card table does not include CMP 50HX. This host is headless, has no
X display, and its installed `nvidia-settings` cannot start because the GTK
libraries are absent. No X/Coolbits changes were made.

#### OpenCL-Benchmark VF-offset test

The official OpenCL-Benchmark was used to test a temporary efficiency profile:

```text
GPC VF offset: +200
GPU clock lock: 1905 MHz
GPU power limit: 180 W
```

Five consecutive runs completed with status 0. The average was `13.536
TFLOPS` FP32, `26.954 TFLOPS` FP16, and `48.512 TIOPS` INT8, with `43.608 s`
wall time and `179.29 W` peak sampled power. No new NVRM Xid or AER lines
appeared. The helper restored offset `0`, unlocked the GPU clock, and restored
the `225 W` power limit after the run.

The earlier `225 W` OpenCL control averaged `13.460 FP32`, `26.632 FP16`, and
`47.872 INT8` with a `230.46 W` peak. This profile therefore cuts about `51 W`
from the observed peak without a measured OpenCL throughput loss. It is the
current best tested efficiency profile, but it is not yet part of the
end-user patch: the exact voltage is unknown and the control is runtime state.

A follow-up `170 W` / `+300` trial did not complete an OpenCL run within the
`240 s` bound. It produced no benchmark metrics and is rejected as an
end-user profile; the card was restored after the trial.

#### Exact `llama-cli` 30-second Pareto sweep

The current power/throughput result uses the exact user workload recorded in
`experiments/cmp50-undervolt/llama-cli-power-sweep.sh`. Every profile was run
five times. A run is accepted only when the final
`[ Prompt: ... t/s | Generation: ... t/s ]` line appears; the watchdog is
`30 s`, with a short cleanup grace period for the normal post-metric exit.
The harness records live power, temperature, and before/after NVRM Xid/AER
counts.

| Profile | Prompt average | Generation average | Peak sampled power | Max temp | Result |
|---|---:|---:|---:|---:|---|
| Stock `225 W`, unlocked | `234.4 t/s` | `73.20 t/s` | `226.67 W` | `60 C` | `5/5` |
| `180 W`, `+200`, `1950 MHz` | `235.1 t/s` | `73.82 t/s` | `182.40 W` | `55 C` | `5/5` |
| `170 W`, `+200`, `1980 MHz` | `235.9 t/s` | `71.86 t/s` | `178.12 W` | `54 C` | `5/5` |
| `160 W`, `+200`, `1980 MHz` | `236.1 t/s` | `72.02 t/s` | `166.59 W` | `50 C` | `5/5` |

The recommended stock-level profile is `180 W / +200 / 1950 MHz`: its measured
generation result is within normal run-to-run variation of the stock control
while lowering the sampled peak by about `44 W`. The power-first profile is
`160 W / +200 / 1980 MHz`: it lowers the sampled peak by about `60 W` and
reduces generation throughput by about `1.6%` on this workload. Both profiles
completed five of five runs with no new NVRM Xid/AER line during confirmation.

The reproducible control utility accepts:

```text
sudo /home/xrip/cmp50-vfctl apply             # 180 W, +200, 1950 MHz
sudo /home/xrip/cmp50-vfctl set 160 200 1980  # power-first point
sudo /home/xrip/cmp50-vfctl reset            # 225 W, offset 0, unlocked clocks
```

The CMP 50HX/Turing path does not support the NVML memory-lock API. Its
memory overclock control is the memory VF offset API, which accepts an offset
in MHz rather than a fixed memory-clock value. `status` reads the current
offset and the valid range from the driver.

```text
sudo /home/xrip/cmp50-vfctl status
sudo /home/xrip/cmp50-vfctl mem-offset OFFSET_MHZ
sudo /home/xrip/cmp50-vfctl set 160 200 1980 MEM_OFFSET_MHZ
sudo /home/xrip/cmp50-vfctl set-range 160 200 1800 1980 MEM_OFFSET_MHZ
sudo /home/xrip/cmp50-vfctl reset            # also sets memory offset to 0
```

The `apply` profile leaves the memory offset untouched. On the tested host the
driver reports a memory-offset range of `-2000..6000 MHz`. The controls are
runtime state only; reset them after a test.

Raw confirmation roots on the test host are
`/home/xrip/cmp50-llama-power-sweep-20260814Tconfirm180`,
`/home/xrip/cmp50-llama-power-sweep-20260814Tconfirm170`, and
`/home/xrip/cmp50-llama-power-sweep-20260814Tconfirm160c1980`.

#### Historical concise power-cap sweep

An earlier reversible sweep was run with a concise `llama-cli` request at
`200 W`, `180 W`, and `160 W`. The exact command, answer, live power samples,
and before/after GPU captures are in
`experiments/cmp50-undervolt/README.md` and the linked raw run directories.

| Power limit | Peak sampled power | Prompt | Generation | Max temp | Result |
|---:|---:|---:|---:|---:|---|
| `225 W` baseline* | `230.46 W` | `194.7 t/s` | `72.5 t/s` | `55 C` | stable |
| `200 W` | `191.20 W` | `182.4 t/s` | `63.5 t/s` | `49 C` | correct answer |
| `180 W` | `173.81 W` | `183.6 t/s` | `61.8 t/s` | `49 C` | correct answer |
| `160 W` | `160.08 W` | `183.7 t/s` | `60.0 t/s` | `48 C` | correct answer |

`*` The 225 W row used the earlier long-reasoning command and is not directly
throughput-comparable with the concise sweep rows. The three capped rows use
identical commands. All exited cleanly, returned the same drive recommendation,
and had no `llama-cli` stderr or observed CUDA failure.

For that earlier short test, `180 W` was the best practical efficiency point:
it cuts about `56 W` from the peak baseline while losing only about `2.7 t/s`
generation versus `200 W`. `160 W` is also stable but costs about `5.5 t/s`
generation versus `200 W`.

A true fixed `800 mV` point still cannot be read back or requested directly on
this headless CMP path. The tested GPC VF offset is the current supported
curve-equivalent route.

#### Live 180 W test

For real-use observation, the GPU power limit was changed from `225 W` to
`180 W` with `nvidia-smi -pl` while the same LLM workload ran. After the
observation period, the power limit was restored to the standard `225 W`
value; the card immediately reported `1905 MHz` SM and `7000 MHz` memory
clocks with no active power-cap throttle reason.

The user's live-use comparison after restoring the standard limit showed
generation increasing from `76.22` to `85.54 t/s`: `+9.32 t/s`, or about
`+12.2%`. This confirms that the 180 W cap causes a noticeable serving
throughput loss even though the server remains functional.

#### Live 180 W + fixed 1800 MHz test

For the next real-use test, the GPU was configured with:

```text
nvidia-smi -pl 180
nvidia-smi -lgc 1800,1800
```

The card reported an `180 W` power limit, locked `1800 MHz` SM/graphics clock,
and normal `7000 MHz` memory. The test has now been closed: the GPU clock lock
is reset and the standard `225 W` limit is back. The driver reports no active
power-cap or application-clock override. Rollback was:

```text
nvidia-smi -rgc
nvidia-smi -pl 225
```

### OpenCL-Benchmark result: near RTX 2080 Ti scalar speed

The official [ProjectPhysX/OpenCL-Benchmark](https://github.com/ProjectPhysX/OpenCL-Benchmark)
was built and run on the remote card on 2026-08-12. The exact source commit,
raw output, and hashes are kept in `experiments/cmp50-opencl-benchmark`.
Two consecutive device-0 runs compiled all OpenCL kernels and completed without
an OpenCL, NVIDIA, or GPU error:

| Metric | Run 1 | Run 2 |
|---|---:|---:|
| FP64 | `0.420 TFLOPS` | `0.420 TFLOPS` |
| FP32 | `13.519 TFLOPS` | `13.516 TFLOPS` |
| FP16 OpenCL | `26.715 TFLOPS` | `26.714 TFLOPS` |
| INT64 | `3.418 TIOPS` | `3.418 TIOPS` |
| INT32 | `13.240 TIOPS` | `13.240 TIOPS` |
| INT16 | `11.561 TIOPS` | `11.668 TIOPS` |
| INT8 / DP4A | `48.288 TIOPS` | `48.231 TIOPS` |
| Coalesced read | `504.02 GB/s` | `504.11 GB/s` |
| Coalesced write | `472.42 GB/s` | `472.80 GB/s` |

#### 16 GiB ReBAR regression check, 2026-08-13

The same binary, driver, device ID, and command were used after a cold boot
with 16 GiB BAR1. Each pass used a 1 GiB buffer, 256 samples per compute and
device-memory test, and 16 samples per host transfer. All three passes exited
with status 0. Their median is compared with the saved pre-ReBAR run 2:

| Metric | Pre-ReBAR | 16 GiB BAR1 median | Change |
|---|---:|---:|---:|
| FP64 | `0.420 TFLOPS` | `0.417 TFLOPS` | `-0.71%` |
| FP32 | `13.516 TFLOPS` | `13.410 TFLOPS` | `-0.78%` |
| FP16 OpenCL | `26.714 TFLOPS` | `26.701 TFLOPS` | `-0.05%` |
| INT64 | `3.418 TIOPS` | `3.391 TIOPS` | `-0.79%` |
| INT32 | `13.240 TIOPS` | `13.232 TIOPS` | `-0.06%` |
| INT16 | `11.668 TIOPS` | `11.563 TIOPS` | `-0.90%` |
| INT8 / DP4A | `48.231 TIOPS` | `47.842 TIOPS` | `-0.81%` |
| Coalesced read | `504.11 GB/s` | `503.97 GB/s` | `-0.03%` |
| Coalesced write | `472.80 GB/s` | `471.31 GB/s` | `-0.32%` |
| Misaligned read | `418.12 GB/s` | `415.57 GB/s` | `-0.61%` |
| Misaligned write | `124.22 GB/s` | `123.37 GB/s` | `-0.68%` |
| PCIe send | `0.85 GB/s` | `0.85 GB/s` | `0.00%` |
| PCIe receive | `0.85 GB/s` | `0.85 GB/s` | `0.00%` |
| PCIe bidirectional | `0.85 GB/s` | `0.85 GB/s` | `0.00%` |

Every median is within 1% of the saved result. This proves no broad OpenCL
performance regression, but it does not prove a speed gain. This benchmark
moves OpenCL buffers through the driver and is not a direct BAR1 mapping test,
so unchanged PCIe throughput is expected. Raw outputs and the comparison are
in `experiments/cmp50-opencl-benchmark/runs/20260813T074922Z-rebar16g`.
After the runs, BAR1 was still 16 GiB, the card was healthy in P0, and the
kernel log had no new Xid, AER, BAR-allocation, or GPU error.

#### PCIe Gen2 x4 result, 2026-08-13

The same benchmark binary was run immediately before and after the board-gated
kernel Gen2 change. Linux sysfs and NVIDIA RM reported Gen1 x4 before and Gen2
x4 after. Both runs exited with status 0:

| Metric | Gen1 x4 | Gen2 x4 | Change |
|---|---:|---:|---:|
| FP32 | `13.425 TFLOPS` | `13.415 TFLOPS` | `-0.07%` |
| Coalesced read | `504.82 GB/s` | `503.79 GB/s` | `-0.20%` |
| Coalesced write | `472.72 GB/s` | `473.25 GB/s` | `+0.11%` |
| PCIe send | `0.85 GB/s` | `1.70 GB/s` | `+100.0%` |
| PCIe receive | `0.85 GB/s` | `1.71 GB/s` | `+101.2%` |
| PCIe bidirectional | `0.85 GB/s` | `1.69 GB/s` | `+98.8%` |

The final clean-package boot logged two `CMP50_GEN2: POLICY_PASS` lines and a
first-attempt `CMP50_GEN2: RETRAIN_PASS`. It also passed the issue-rate/count
verifier, kept BAR1 at `16384 MiB`, and had no Xid or AER fault. Exact hashes,
boot ID, values, and remote log paths are recorded in
[`experiments/cmp50-pcie-gen2/runs/20260813T0932Z-kernel-gen2/RESULT.md`](../experiments/cmp50-pcie-gen2/runs/20260813T0932Z-kernel-gen2/RESULT.md).
The endpoint and upstream bridge both reported active 5 GT/s x4 status and a
5 GT/s target. Linux kept the endpoint's early-boot `max_link_speed` sysfs
cache at 2.5 GT/s, so that stale maximum field is not used as the live gate.

#### Clean split-series reinstall and OpenCL non-regression, 2026-08-17

The package was rebuilt from the clean NVIDIA source archive with all four
ordered patches, installed through `manage.sh`, rebooted, and verified on the
remote CMP50HX. Three runs of the same OpenCL-Benchmark binary all exited with
status `0`. The saved result and raw output are in
[`experiments/cmp50-opencl-benchmark/runs/20260817T073530-split-install/RESULT.md`](../experiments/cmp50-opencl-benchmark/runs/20260817T073530-split-install/RESULT.md).

| Metric | Baseline | Split-series median | Change |
|---|---:|---:|---:|
| FP32 | `13.516 TFLOPS` | `13.417 TFLOPS` | `-0.73%` |
| FP16 | `26.714 TFLOPS` | `26.719 TFLOPS` | `+0.02%` |
| Coalesced read | `504.11 GB/s` | `503.99 GB/s` | `-0.02%` |
| Coalesced write | `472.80 GB/s` | `473.20 GB/s` | `+0.08%` |
| Misaligned write | `124.22 GB/s` | `123.85 GB/s` | `-0.30%` |
| PCIe send / receive | `0.85 / 0.85 GB/s` | `1.70 / 1.71 GB/s` | `+100% / +101%` |

Every measured median was no more than 1% below the saved baseline. The
independent PCIe capture reported active Gen2 x4, the GPU returned to P0 with
`0 MiB` used, and no NVIDIA Xid or PCIe error appeared.

A later direct PROM dump proves that the CMP VBIOS is not the source of the
Gen1 cap. Its init script explicitly changes `0x880a8` low nibble to `2`, which
requests Gen2; the RTX 2080 Ti reference has a no-op at the same point. The
stock CMP target later becoming `1` places the cap after VBIOS init, in the
protected policy already opened by the all-feature kernel path. The exact ROM
comparison is in `experiments/cmp50-vbios-comparison`.

The official project’s RTX 2080 Ti reference is `68` SMs, `4352` cores at
`1545 MHz`, and `13.448` theoretical FP32 TFLOPS. The CMP 50HX measured
`13.516 TFLOPS`, or about `100.5%` of that FP32 reference. The result is
consistent with the CMP’s higher observed `1905 MHz` stockflow clock offsetting
its lower `56`-SM count. This is a strong confirmation that the compute path is
already near RTX 2080 Ti scalar OpenCL speed; it does not measure Tensor Core
HMMA, for which the separate CUDA result remains approximately `107.2` FP16
Tensor TFLOPS.

The benchmark printed `Gen1 x16` for PCIe in both runs, but its own method
estimates generation while assuming x16 width. That label is not accepted as
PCIe proof; Linux sysfs, NVIDIA RM, and the kernel retrain result are the
authoritative Gen2 x4 evidence.

The post-run card stayed healthy in P0 at about `1905 MHz`, `41-42 C`, with
zero VRAM use and no compute process left running.

### RT-count gate: proved, not cosmetic

The exact GSP path for RM information index `0x22` reads OBJFUSE ID
`0xFF00008E`. On TU102 this is BAR0 `0x21168`, bit 0. The live card reads zero,
so the stock GSP returns zero RT cores.

The test patch in `experiments/cmp50-rt-count-override` changes only the host
RM static GR cache for the two supported CMP 50HX board IDs. Its live result
was:

| State | RM RT cores | `VK_KHR_ray_query` |
|---|---:|---|
| Stockflow only | `0` | not exposed |
| Host count override | `56` | exposed |

CUDA and Tensor counts stayed at `3584` and `448`. This proves that at least
one NVIDIA user-mode gate uses the reported RT-core count. The override is not
only a display change. The combined V551-stockflow plus RT-count module now
survives reboot. Its rollback path is recorded in
`cmpunlocker-v0.1.28-linux-x64-50hx-stockflow/BACKUP_DIR-610.43.03-RTCOUNT.txt`.

The first reboot after installation still reported zero because the initramfs
held the older stockflow-only `nvidia.ko`. Running `update-initramfs` for the
active kernel put the new module in the boot image. The second reboot then
reported `56`, full issue rates, correct `107.19 TFLOPS` Tensor output, and no
new Xid. A persistent module install must therefore verify both the module on
disk and the copy in initramfs.

### Exact GSP RT-count use

The exact GSP method is now split from a bad IDA function boundary, typed, and
named `kgraphicsGetRtCoreCount_TU102_inferred` at `0x529b5a0`. TU102 HAL index
37 installs it at `KernelGraphics+0xb68`. It reads OBJFUSE ID `0xff00008e`; if
the bit is set, it calls the active-TPC accessor at `KernelGraphics+0x9a8` and
returns twice that count for a non-partitioned TU102. The accessor is named
`kgraphicsGetActiveTpcCount_inferred` at `0x5252bac`.

The exact 610.43.03 executable contains only two functions that construct
OBJFUSE ID `0xff00008e`. The TU102 function above builds it with the instruction
pair at `0x529b5d0`/`0x529b5e8`. The alternate function, now named
`kgraphicsGetRtCoreCount_FuseOrLegacy_inferred` at `0x52bcefc`, builds the same
ID at `0x52bcf64`/`0x52bcf6c`. The HAL table selects one of these functions for
the same `KernelGraphics+0xb68` slot. A full immediate and call-use scan found
no third GSP reader of this exact fuse ID and no reader that writes RT power,
clock, context, or dispatch state.

An exhaustive scan of the `KernelGraphics+0xb68` call pattern found three
consumers in this image:

1. GR information switch case `0x22`, which is
   `NV0080_CTRL_GR_INFO_INDEX_RT_CORE_COUNT`.
2. Two architecture variants that fill NVIDIA's exact 36-byte
   `VMIOPD_GRSMINFO` structure and store the result in its final
   `rtCoreCount` field at offset `0x20`.

The only later path that builds this structure outside the GR-information
handler reads `maxWarpsPerSM` at offset `0x0c`; it does not read
`rtCoreCount`. No context-load, FECS/GPCCS, or ray-dispatch caller of the count
method exists in this GSP image.

This makes two earlier statements compatible: the host count patch is useful
because NVIDIA user mode uses the reported count as an API gate, but the GSP
fuse branch itself is a reporting path. Bypassing the branch in GSP would make
its own report say `56`; it is not expected to fix the first-traversal Xid 109.
The count override remains part of the target state as requested, while the
execution fix must be below this method.

### RT context buffers: present and selected before execution

The read-only RM probe now sends public control
`NV2080_CTRL_CMD_GR_GET_ENGINE_CONTEXT_PROPERTIES` (`0x2080122d`) for all 26
defined engine-context IDs. On the live card, both RT-specific buffers are
valid with or without the count override:

| Context buffer | Size | Alignment | RM status |
|---|---:|---:|---:|
| `GRAPHICS_RTV` | `532480` | `256` | `NV_OK` |
| `GRAPHICS_RTV_CB_GLOBAL` | `524288` | `256` | `NV_OK` |

The TU102 `KernelGraphics::bRtvCbSupported` HAL property is also true in the
exact GSP image. The exact 610.43.03 source and disassembly match at the next
level: `kgrctxMapGlobalCtxBuffers_IMPL` at `0x52dc680` tests that property and
maps `GR_GLOBALCTX_BUFFER_RTV_CB` (ID 3) into the channel VAS. Its one-buffer
helper is now split and named `kgrctxMapGlobalCtxBuffer_IMPL` at `0x52dc22c`.
The matching unmap helper at `0x52dd13c` is named
`kgrctxUnmapGlobalCtxBuffer_IMPL`. Their real prototypes and useful local
names are applied in the IDB.

A zero-sized buffer, a false TU102 support property, or an omitted high-level
RTV global-buffer map is therefore not the current failure. The exact
FECS/GPCCS consumption and low-level RT-query state still need proof.

### GFXP control layout: active path, no CMP gate found

The exact 610.43.03 GSP image has four unpublished internal GR controls that
were hidden inside bad IDA function boundaries:

| Command | Handler | Parameter size | Inferred operation |
|---|---:|---:|---|
| `0x20800a10` | `0x52332d4` | `0x28` | Return GFXP control-buffer properties |
| `0x20800a11` | `0x523342c` | `0x10` | Map caller memory and build the GFXP layout |
| `0x20800a12` | `0x5233650` | `0x110` | Enable selected GFXP layout entries |
| `0x20800a13` | `0x5233880` | `0x114` | Disable selected GFXP layout entries |

TU102 HAL index 37 installs these Graphics methods:

| Virtual slot | TU102 target | Result |
|---|---:|---|
| `Graphics+0xdb8` | `0x52928ac` | Returns size `1124`, alignment `4096` |
| `Graphics+0xdc0` | `0x5280a0c` | Builds the CPU-visible GFXP control layout |
| `Graphics+0xdc8` | `0x52810c8` | Updates its entry masks and active count |
| `Graphics+0xe88` | `0x5294afc` | Returns the RTV field offsets for local buffer ID 7 |

The `+0xdc0` builder gets local context-buffer properties for IDs 3, 4, 5,
6, and 7. Its optional RTV section checks the real
`KernelGraphics+0x14f` `bRtvCbSupported` byte. That byte is true for TU102 for
every RM HAL index. None of the three TU102 methods contains a direct CMP,
board-ID, or SKU branch.

The control-block header inside the 1124-byte allocation is now typed in IDA
as `NV_CTXSW_GFXP_POOL_CTRL_BLK_TU102_INFERRED`. The header is `0x64` bytes.
Its first `0x58` bytes use NVIDIA's published Pascal GFXP control fields.
TU102 adds three 32-bit fields:

| Offset | Field |
|---:|---|
| `0x58` | `gfxpRtvSize` |
| `0x5c` | `globalRtvSize` |
| `0x60` | `rtvOffset` |

The new `Graphics+0xe88` method accepts only local context-buffer ID 7 and
returns exactly these offsets. The layout builder writes all three fields and
has no CMP test.

The promoted-buffer IDs are now corrected. Public promote IDs `3..12` map to
internal IDs `0..9`; therefore public ID 8 is internal ID 5, the real
`GFXP_CTRL_BLK`. Internal IDs 7 and 8 are the restricted and unrestricted
privilege access maps. The earlier working assumption that internal ID 8 was
the GFXP control block was wrong.

This also closes a false lead at `0x51ea548`. Exact 610.43.03 source matching
identifies it as `gpuConstructUserRegisterAccessMap_IMPL`. The values at
`pGpu+0x3fa8`, `+0x3fb0`, and `+0x3fb8` are the two register-access-map
pointers and their size, not RT/GFXP templates.

The recovered data path is:

```text
CPU-RM -> internal cmd 0x20800a11 -> GSP handler 0x523342c
       -> Graphics+0xdc0 -> write GFXP layout into caller memory
       -> CPU-RM fills the control block
       -> promote public ID 8 / internal ID 5
       -> FECS consumes its offsets and sizes
```

A small read-only user-client probe is kept at
`experiments/cmp50-rt-control-probe/rm_gfxp_static_probe.c`. Command
`0x20800a10` was run twice on the live 610.43.03 card, once while another GPU
client existed and once with zero VRAM use and zero GPU load. Both calls
returned ioctl success, RM status `0x56`, and a zero output structure. The
idle rerun added no Xid and did not allocate GPU memory. This result cannot
separate a normal user-client access rejection from the handler's own first
property-query failure, because both can report the same status. It does prove
that this unpublished internal control is not a useful direct user-space read
path; the stronger memory-mapping commands were not tried.

The IDB now has evidence-scoped names, prototypes, local names, and comments
for these handlers and methods. `_inferred` remains in every unpublished name.
This cluster gives no safe CMP bypass to patch: GFXP setup is present and the
TU102 layout path is selected. The next execution gate is more likely in the
CPU-RM data supplied to this path, FECS/GPCCS consumption, or a lower hardware
state transition.

The first FECS comparison also gives a strong negative result. The TU102 FECS
block at IMEM `0x0f56..0x14a3` reads control fields `+0x58`, `+0x5c`, and
`+0x60`. The same block and the same reads exist at the same addresses in the
non-RT TU116 FECS image. The ranges differ in only 18 bytes: nine `lcall`
targets use TU102 helper `0x72a3` versus TU116 helper `0x6ffb`. No other
instruction in that range changes. This means the visible RTV/GFXP block is
common GR context setup, not a TU102-only RT-enable gate.

### Exact TU102 versus TU116 netlist data comparison

The full decompressed TU102, TU106, and TU116 netlists were split into all 40
declared regions and compared byte for byte. Most non-code regions are exactly
the same on all three chips. Among the register-init payloads, the TU102 versus
TU116 difference reduces to three register values:

| BAR0 register | TU102/TU106 | TU116 |
|---:|---:|---:|
| `0x419bc8` | `0x00398a2c` | `0x00398a42` |
| `0x419bf0` | `0x944077fe` | `0x844077fe` |
| `0x419e5c` | `0x000058c1` | `0x00005cc1` |

The `0x419bf0` and `0x419e5c` entries occur in both region ID `0x05` and the
indexed copy in region ID `0x0a`; `0x419bc8` occurs in region ID `0x06`.
Region ID `0x12` is one selector word: `0x18` for TU102/TU106 and `0x0c` for
TU116. The live CMP 50HX reads exactly the TU102/TU106 values for all three
registers. Thus the card already runs the RT-chip netlist data; replacing or
patching the register-init tables is not a current unlock candidate.

The GPCCS comparison is also almost empty. TU102 and TU116 GPCCS IMEM have the
same `12584`-byte size and differ in only three bytes: one compare immediate
at IMEM `0x2f8a` (`3` versus `1`) and one 16-bit subtraction immediate at
`0x2fc8` (`0x1e00` versus `0x2180`). TU102 and TU106 differ in only the latter
immediate. GPCCS DMEM differences are limited to the image header/version text.
There is no missing RT traversal implementation to copy from the RTX GPCCS
image into the CMP path.

A TU102/TU106 FECS path at IMEM `0x48e8..0x4c94` copies nine words from
`0x584200..0x584240` to `0x481a00..0x481a40` when FECS DMEM flag `0x11f4` is
enabled. This first looked RT-specific because the direct code block is absent
from TU116. The full data comparison disproves that label: region ID `0x21`,
which lists the `0x481aXX` registers, is byte-identical on TU102, TU106, and
TU116. A read-only live snapshot also found all nine source and target words
zero. FECS method IDs `0x69` and `0x6a` set and clear the `0x11f4` flag, but
their host meaning is not yet named. This path must stay a neutral GPC-state
lead, not an RT patch target.

Together these checks move the remaining gate below normal TU102 netlist
selection and below the shared RTV/GFXP allocation path. The best remaining
working hypothesis is fuse-derived hardware or protected early-GR state that
changes real ray-instruction execution. That hypothesis is not yet proved and
does not justify another live ray-query run by itself.

### Real RT execution: blocked after exposure

With the count set to 56, Vulkan accepts the device, ray-query extension and
features. BLAS, TLAS, and the compute ray-query pipeline all build. Corrected
tests with 64 rays and with one true invocation both end at `vkQueueWaitIdle`
with:

```text
Xid 109, CTX SWITCH TIMEOUT, Info 0x4c010
```

An earlier apparent one-ray pass was invalid: integer dispatch division sent
zero workgroups. The probe now uses ceiling division, pushes the exact ray
count, and bounds each invocation. The corrected one-ray run fails in about
six seconds.

The 2026-08-12 dispatch-isolation test narrows this further:

| Shader case | Important SPIR-V operation | Result |
|---|---|---|
| Control | no ray-query operation | one dispatch completed; no Xid |
| Initialize only | `OpRayQueryInitializeKHR`, then `OpRayQueryGetRayTMinKHR`; no `OpRayQueryProceedKHR` | device lost and the same Xid 109 in about six seconds |
| Original query | initialize plus `OpRayQueryProceedKHR` | same Xid 109 |

All cases use the same BLAS, TLAS, acceleration-structure descriptor, pipeline
layout, and graphics context. The control case proves that object setup and an
ordinary dispatch are safe. Traversal is not required to trigger the fault:
entering ray-query state at `OpRayQueryInitializeKHR` is enough. The generated
SPIR-V was checked with `spirv-dis` before execution. Sources and the repeatable
procedure are in `experiments/cmp50-rt-dispatch-isolation`.

#### Nearest machine-code boundary

Fresh NVIDIA disk-cache objects were decoded into their NVUC sections. Every
shader that contains `OpRayQueryInitializeKHR`, including the dead-result and
full-proceed variants, begins with the same four 128-bit SM75 instructions at
offsets `0x10..0x40`:

```text
0x10  d0730000 00000000 00000000 00ea0f00
0x20  d4790000 00020000 00000000 00e80f00
0x30  d3730000 00000000 00000000 00e20f00
0x40  d273ff00 00000300 ff040e00 00e20f00
```

Both the installed CUDA 12 `nvdisasm` and the official CUDA 13.3 build skip
these four words without naming them. The safe control shader has the same
`RayQueryKHR` SPIR-V capability and acceleration-structure descriptor, but it
does not contain this instruction group. Its normal second instruction starts
at `0x10`. The full-proceed shader starts with the same four words and then
continues into its larger traversal sequence.

The closest proved machine boundary is therefore this initialize prologue, or
the hardware state entered by it. We have not yet assigned exact instruction
names. It is stronger evidence than the SPIR-V boundary alone, but it does not
yet identify which of the four words is rejected.

#### Live SM exception capture: invalid opcode proved

`tools/cmp50/rt_warp_esr_capture.py` maps BAR0 read-only and samples the exact
per-SM registers read by the 610.43.03 GSP exception handler. The TU10x aperture
scan found 56 active SM register sets; the other candidate slots returned the
normal `0xbadfxxxx` absent-unit value. This independently agrees with the
physical 56-SM topology.

One bounded initialize-only dispatch gave this order:

| Time from capture start | Unit or block | Change |
|---:|---|---|
| `689.631 ms` | `GPC2/TPC0/SM0` | `HWW_WARP_ESR=0x00000009` (`INVALID_OPCODE`), `HWW_GLOBAL_ESR=0x00000004`, report mask `0x00000000` |
| `7714.724 ms` | FECS | context-switch status changed to `0x00002001`; signal/status changed to `0x00000140` |
| about six seconds after submit | RM | Xid 109, `CTX SWITCH TIMEOUT`, `Info 0x4c010` |

The captured words at `0x728`/`0x72c` were `0x00000104:0x07c12b72`. They were
recorded as `HWW_WARP_ESR_PC`. That label is now disproved; see the next
section. This value must not be mapped to one of the four 128-bit words above.

#### Correction 2026-08-12: `0x728`/`0x72c` is not a fault-latched PC

The earlier plan was to decode `HWW_WARP_ESR_PC` and map `0x00000104:0x07c12b72`
onto one of the four undecoded SM75 words. Re-reading the saved capture
`runs/20260812T1105Z-warp-esr/rt-warp-live.json` shows the premise was wrong.
Four facts come from that file alone, with no new hardware run:

- the two words moved on **all 56** active SMs, 422 changes in total, while
  `warp_esr` moved on exactly one SM;
- every one of those 422 changes happened with `warp_esr` unchanged;
- at the faulting sample the pair did **not** change:
  `pc=0x00000104:0x07c12b72` before and after `esr=0x0->0x9`;
- across the whole run only four distinct low values ever appeared
  (`0x06c12b72`, `0x07c12b72`, `0x04c1eb72`, `0x07c5eb76`) and none is
  16-byte aligned, which an SM75 instruction address must be.

The faulting SM's own history makes this plain. It changed value seven times
before the fault and not at all during it:

```text
420.084 ms  0x00000174:0x06c12b72 -> 0x00000174:0x07c5eb76
428.390 ms  0x00000174:0x07c5eb76 -> 0x00000174:0x06c12b72
513.926 ms  0x00000174:0x06c12b72 -> 0x00000174:0x07c5eb76
519.313 ms  0x00000174:0x07c5eb76 -> 0x00000174:0x06c12b72
546.523 ms  0x00000174:0x06c12b72 -> 0x00000174:0x04c1eb72
552.150 ms  0x00000174:0x04c1eb72 -> 0x00000174:0x06c12b72
676.490 ms  0x00000174:0x06c12b72 -> 0x00000104:0x07c12b72
689.631 ms  esr 0x0 -> 0x9, pair unchanged
```

Four repeating values shared by 56 SMs is per-unit state with a few bit
fields, not a program counter. `0x728`/`0x72c` are therefore unidentified SM
state. `tools/cmp50/rt_warp_esr_capture.py` now names them `sm_state_728` and
`sm_state_72c` rather than `warp_esr_pc_lo`/`_hi`.

#### The unsampled pair at `0x738`/`0x73c`

The GSP exception handler does not form a PC from `0x728`/`0x72c` at all. It
logs those words raw. It gets a separate 64-bit address from a dedicated helper
at `0x5276138`, now named `graphicsReadSmExceptionAddrPair_inferred` in the
IDB, which reads TPC-relative `0x738` (lo) and `0x73c` (hi) at `smId * 0x80`.
The caller combines them at `0x5288a9c` as `(hi << 32) + lo`. That helper has
exactly one cross-reference: the SM warp-exception handler itself, so it exists
only for this path.

`0x738`/`0x73c` were never sampled in the 20260812T1105Z run. The sampler now
reads them as `esr_addr_lo`/`esr_addr_hi`.

#### Confirmed on hardware 2026-08-12: the latched address is `0xdf5ea5bc10`

Two runs settled this, a safe one first.

`runs/20260812T1230Z-control-esr-addr` dispatched the control shader, which
completes and raises no Xid. Over 3083 samples on 56 SMs, `0x738`/`0x73c` never
left zero, while `0x728`/`0x72c` moved 494 and 56 times across every SM and
passed through the exact pair `0x07c12b72:0x00000104` that the earlier run had
recorded as the faulting PC. A value that occurs routinely in fault-free work
cannot be the address of a rejected instruction. An idle read just before it
returned `0x04c1eb72:0x00000174` identically on all 56 SMs, which no per-warp PC
could do, with `0x738`/`0x73c` at zero.

`runs/20260812T1240Z-esr-addr` then repeated the initialize-only shader. At
`1291.302 ms` on `GPC2/TPC0/SM0`:

```text
                before        after
warp_esr        0x00000000    0x00000009   INVALID_OPCODE
global_esr      0x00000000    0x00000004
esr_addr_hi     0x00000000    0x000000df
esr_addr_lo     0x00000000    0x5ea5bc10
sm_state_728    0x07c12b72    0x07c12b72   unchanged
sm_state_72c    0x00000104    0x00000104   unchanged
```

The latched address is `(0xdf << 32) + 0x5ea5bc10 = 0xdf5ea5bc10`. It is
16-byte aligned, as an SM75 instruction address must be. It was zero before the
fault, latched only at the fault, and returned to zero at GR reset at
`5903.147 ms`. The `0xbadf1201` values that appear on GPC4 at `5898.809 ms` are
the absent-unit response as the GR unit collapsed, not additional faults.

So `0x738`/`0x73c` is the fault-latched address pair, and this is the first
captured address of the rejected ray-query instruction. The run reproduced the
same Xid 109, `CTX SWITCH TIMEOUT`, `Info 0x4c010`, and needed a host reboot;
after the reboot the card returned to `PASS_CMP50HX_FULL_SPEED`,
`PASS_CMP50HX_ALL_TARGETS_FULL_SPEED`, `CMP_SKU=1`, and `3584`/`56`/`448`.

#### The address is not yet a shader offset

`0xdf5ea5bc10` cannot be converted to a shader offset from that run alone. The
shader's base virtual address was not captured at the same time, and a later
allocation cannot be assumed to land at the same address.

The next run has to capture both together: the ioctl and shader-address trace,
which the harness already supports through `nvidia_ioctl_trace.so`, and this ESR
sampler. Then `0xdf5ea5bc10 - shader_base` gives an offset that can be tested
against the four unknown 128-bit words at `0x10`, `0x20`, `0x30`, and `0x40`.
Only that comparison names the rejected instruction.

This is a correction of method, not of the failure itself. The SM still rejects
a ray-query instruction with `INVALID_OPCODE`; only the claim that we held its
address is withdrawn.

#### FECS did not stall immediately after the SM fault

The same file also refines the documented order. FECS context-switch status
recovered after the fault and only stalled seven seconds later:

```text
687.096 ms  ctxsw_status 0x00000002 -> 0x00020002
689.631 ms  SM fault, warp_esr 0x0 -> 0x9
1188.015 ms ctxsw_status 0x00020002 -> 0x00000002   (back to normal)
7714.724 ms ctxsw_status 0x00000002 -> 0x00002001,
            signal_status 0x00000180 -> 0x00000140  (stall)
```

The sequence `ray instruction -> SM INVALID_OPCODE -> FECS stall -> Xid 109`
still holds in time order, but FECS ran normally for about 6.5 seconds in
between. Any explanation that needs the SM fault to wedge FECS directly has to
account for that gap.

This proves the first fault is an SM instruction-decode rejection. FECS and
Xid 109 are later effects. Silencing the GSP exception handler, clearing the
Xid report, or changing only the report mask cannot give the rejected opcode
valid execution meaning. The useful patch must change the fuse-derived or
protected SM/GR state that controls opcode legality. Raw capture files are in
`experiments/cmp50-rt-dispatch-isolation/runs/20260812T1105Z-warp-esr`.

#### `enableRayQueryColdStartWAR`: tested and rejected for this prologue

The exact 610.43.03 `libnvidia-glvkspirv.so` has SHA-256
`ebe38ab3d407ce6a71237006d6d2a9fc0420374700d0a0070a00ee828db5e899`.
It contains a real boolean compiler option named
`enableRayQueryColdStartWAR`. Its options structure stores the byte at
`+0x1c2`; the stock constructor clears it, and two code-generation paths read
it.

A temporary user-space-only compiler copy was tested. A live uprobe during
pipeline creation showed that the first consumer ran once and the second did
not run. At the first consumer, `r10=0`, `dl=0`, `cl=0`, and `r9=0`; the zero
`dl` guard makes the stock code skip the workaround even when the option byte
is forced to one. Forcing the option and both option branches still produced
byte-identical SM75 code. A stronger compile-only test jumped directly to that
consumer's own workaround flag rewrite; the extracted 256-byte text section
still had SHA-256
`fbcc1bcf52eb4ee03b7ddb44e4bfa98ae2a21677199fd33d18906f336d7e7c52`,
identical to stock.

The helper in `tools/cmp50/patch_glvkspirv_coldstart.c` records the exact-build
patch and byte checks. It is an experiment, not an install patch. This result
rejects that compiler option as the producer of the four-word prologue for the
current shader. It does not rule out a different hardware cold-start fix.

One run of the ordinary forced-option copy accidentally omitted
`--setup-only`; it dispatched the known initialize shader and reproduced the
same Xid 109 and `Info 0x4c010`. The server was rebooted and returned healthy.
The hard-force compiler copy was never dispatched.

Do not repeat the initialize or traversal cases without a new patch or new
tracing; both are now known reset-required failures. The test GPU was rebooted
afterward. The persistent patch returned with P0, full issue rates, `3584`
CUDA cores, `448` Tensor cores, and the requested reported count of `56` RT
cores.

The failure is after API exposure and object construction, at the first
ray-query state instruction. The SM first rejects a ray-query instruction as
`INVALID_OPCODE`; only later does FECS enter the `SWITCH` form of a GR
context-switch timeout and report `0x0004c010`. The exact rejected word and the
state bit that controls its legality remain open. A fuse-derived opcode gate,
protected early-GR state, or missing RT power/context setup can still be the
cause, but the first observed fault is now exact. It is not a Tensor problem
and it is not explained by workload size.

#### Exact submitted command stream

The matching control and initialize-only runs were captured with envytools'
MMT support. `tools/cmp50/vulkan_ray_query_bench.c --record-only` first gave a
safe check: both cases can build and record the full command buffer without a
submit or an Xid. A later controlled pair submitted each case once; the RT run
reproduced Xid 109 and the machine was rebooted.

`mmt_bin2dedma` converted both complete traces to text. The local helper
`tools/cmp50/mmt_extract_pushbuffer.py` then rebuilt the final GPFIFO submit:

- submission 11 of 12;
- five GPFIFO entries, 394 push-buffer words in total;
- control SHA-256
  `d8be8121f5ae35141dd7ce32e6aa8e99e495ae34ec32fdeed05a2c84489554e5`;
- initialize-only SHA-256
  `d8be8121f5ae35141dd7ce32e6aa8e99e495ae34ec32fdeed05a2c84489554e5`.

The final GPU method streams are byte-identical. The RT trace has 118 extra
CPU writes before the last doorbell, but they update the user-mode queue and
shader-address records; they are not extra GPU class methods. The only proved
execution input that changes is the SM75 shader code containing the four
unknown ray-query instructions.

This rules out a missing Vulkan-side RT-enable method in the final submit. It
does not rule out state made earlier by GSP, FECS/GPCCS, or hardware from the
RT fuse. That lower state is now the main target.

#### Signed-Booter write probe of the RT fuse word

The normal host BAR0 write to `0x21168` was already known not to stick. A
second, smaller test used the working signed-Booter stockflow writer before
GSP-RM starts. It wrote `1` to `0x21168` after the protected reset window was
opened, without changing any RT shader or Falcon image.

Two added read-only log points gave the same result:

```text
FULLSPEED_STOCK_RELOCK_WPR_DOWN_HANDOFF_PASS ... RTFUSE=00000000
CMP50_GSP_READY_V551: ... rtfuse=0x00000000
```

The first read is directly after the signed Booter returns; the second is after
GSP is ready. Therefore the write never became visible. GSP did not clear a
temporary one. No ray query was submitted with this candidate, no Xid was
logged, and the known-good installed modules were restored from RAM.

The repeatable diagnostic patch and builder are in
`experiments/cmp50-rt-fuse-booter`. This closes the simplest direct-write
override. It does not prove that the fuse has no other override control or
that lower hardware never consumes it.

### Exact Xid 109 register snapshot

`nvidia-debugdump` was taken while the one-ray context was still timed out.
The raw archive is private test data and is not stored in this repository.
The schema-less protobuf register records decode as follows:

| Register | Failure value | Later RM snapshot | Known role |
|---:|---:|---:|---|
| `0x409b00` | `0x80274824` | `0x802748e5` | FECS current channel address |
| `0x409b04` | `0x00274824` | `0x802748e5` | FECS next channel address |
| `0x409c00` | `0x00002001` | `0x00000002` | FECS context-switch state/status, exact bits still open |
| `0x409400` | `0x00000140` | `0x00000180` | FECS signal/status |
| `0x409c18` | `0x00000000` | `0x00000000` | FECS interrupt status |

The dump also records `0x400704 = 0x80010510` and
`0x400708 = 0x00419b48`. Envytools' TU102 register XML identifies these as
`PGRAPH.TRAPPED_ADDR` and `PGRAPH.TRAPPED_DATA_LOW`, not as one MMIO method
address plus another register. The trapped address decodes to method `0x510`
on subchannel 1; `0x00419b48` is its data. NVIDIA's Turing compute class names
method `0x510` `NVC5C0_SET_FALCON04`, while graphics class C597 places that
method at `0x2310`. The trace creates both C597 and C5C0 objects, but the exact
subchannel binding has not yet been rebuilt, so the compute-class match is a
strong inference rather than final proof. In either case, `0x419b48` must not
be treated as the missing ray-only MMIO register.

`tools/cmp50/protobuf_wire_dump.py` makes the decode repeatable without a
protobuf schema:

```bash
python tools/cmp50/protobuf_wire_dump.py rm_00.pb \
  --path 3.105.2 --registers
python tools/cmp50/protobuf_wire_dump.py error_data.pb \
  --path 2.331.3 --registers
```

### Firmware and IDA boundary

The current IDA database is the exact 610.43.03 TU10x GSP/RM RISC-V ELF,
SHA-256 `c10c2866e360154e822087957bc4269168e44f8d45922110e67fd751355806f9`.
It is already firmware analysis, but it is the high-level controller.

The Xid reporter had a bad IDA function boundary. It is now split, typed, and
named `fifoReportCtxswTimeout` at `0x511c63c`. All four RV64 callers pass
`pGpu`, a FIFO object, a channel object, and a 32-bit info word. The function
uses the exact string at `0x40af410` and sends Xid `0x6d` (109). Its parameters,
`channelId`, `pChannelData`, and `errorData` are named in the IDB.

The TU102-family timeout-status handler at `0x51677c0` is now named
`fifoHandleCtxswTimeout_TU102_inferred`, typed, and given evidence-based local
names in the IDB. It first reads a hardware timeout-info word from BAR0 at
`0x51678cc`. For the observed `0x0004c010`, the owner field is zero, so the
handler marks it as a reportable channel timeout, extracts channel ID `0x10`,
resolves the channel, and only then calls `fifoReportCtxswTimeout` at
`0x5167b44`. This is a post-fault reporting path. Removing that final call can
hide Xid 109, but it cannot clear the already timed-out FECS state or make the
shader finish. A useful patch must change the state entered before the timeout,
not only its report.

The upstream SM exception decoder at `0x5288724` is now named
`graphicsHandleSmWarpException_inferred`. Its RV64 call contract, object
pointers, GPC/TPC/SM arguments, and exception-register locals are named and
typed conservatively in the IDB. It reads TPC-relative `0x728`, `0x72c`,
`0x730`, `0x734`, and `0x76c`. Switch case 9 uses the exact text `Illegal
Instruction Encoding`; case 11 uses `Illegal Instruction Parameter`. The live
ray test reached case-9 state in hardware. This function decodes and handles an
error already raised by the SM; it is not the producer of the opcode-enable
state.

### GPCCS object and TU102 loader map

IDA had merged several real RV64 functions in the GPCCS ucode-loader region.
The corrected boundaries are now:

| Start | End | IDB name | Evidence |
|---:|---:|---|---|
| `0x524a0b0` | `0x524a41c` | unchanged | Existing function ends before a fresh frame |
| `0x524a41c` | `0x524aa60` | `gpccsLoadCtxswUcode_reg21xx_inferred` | Fresh frame; GPCCS HAL callback target |
| `0x524aa60` | `0x524b1ec` | `gpccsLoadCtxswUcode_TU102_regF1xx_inferred` | Fresh frame; TU102-selected GPCCS callback |
| `0x524b1ec` | `0x524b9c4` | `gpccsLoadCtxswUcode_reg51xx_inferred` | Fresh frame; GPCCS HAL callback target |
| `0x524b9c4` | `0x524bcb0` | `sub_524B9C4` | Fresh frame only; owner and meaning remain open |

The constructor at `0x596e864` is now named and typed
`__nvoc_objCreate_GPCCS(GPCCS **, Dynamic *, unsigned int)`. It allocates and
clears exactly `0x220` bytes. Its metadata points to a class definition with
size `0x220` and class ID `0x4781e8`, which matches `GPCCS` in NVIDIA's
generated 610.43 source. A conservative `GPCCS` structure is applied in IDA.
The proved fields are:

| Offset | Field |
|---:|---|
| `0x58`, `0x60`, `0x68` | NVOC base-object pointers |
| `0x70` | post-load callback |
| `0x78` | context-switch ucode loader callback |
| `0x1d0` | IMEM image pointer |
| `0x1d8`, `0x1dc` | IMEM aligned and raw byte sizes |
| `0x1e0` | DMEM image pointer |
| `0x1e8`, `0x1ec` | DMEM aligned and raw byte sizes |
| `0x1f4`, `0x1f8` | IMEM and DMEM word sums |

Unknown space remains explicit padding. The exact private NVIDIA method names
are not guessed.

The inferred HAL binder at `0x5944de4` reads `HalVarIdx` from offset `0x10` of
its `GpuHalspecOwner` argument. TU102 has index 37: group 1 and low-bit index
5. The group-1 mask sends that index to `0x524aa60`, stored in GPCCS slot
`+0x78` at `0x5945078`. This is direct proof that TU102 uses the `0xf1xx`
loader, not a nearby implementation.

The TU102 loader reads the typed IMEM/DMEM pointers and sizes, honors
`RMForceGrUcodeLoad`, and writes these register windows:

| Use | Register |
|---|---:|
| IMEM control / data / tag | `0xf180` / `0xf184` / `0xf188` |
| DMEM control / data | `0xf1c0` / `0xf1c4` |

The alternate loaders use the same data model with `0x21xx` and `0x51xx`
windows. Their exact chip owners are not yet proved. Comments at the binder,
constructor, loader starts, and write loops record this evidence in the IDB.

### Netlist selection and image layout

The exact producer of those GPCCS image fields is now mapped. IDA function
`kgraphicsParseNetlistImage_inferred` at `0x5258cf0` takes `OBJGPU *`,
`KernelGraphics *`, and a 32-bit load flag. It walks a pointer table at offset
`0xc00` of the object held at `pGpu+0x1ee8`. NVIDIA's generated object model and
the use of that table support `GraphicsManager` as the object's likely type,
but the `OBJGPU` field name remains marked as inferred.

Each pointed-to netlist image has this exact layout:

| Offset | Type | Meaning |
|---:|---|---|
| `0x00` | `NvU32` | image version |
| `0x04` | `NvU32` | region count |
| `0x08` | array | 12-byte region descriptors |

Each descriptor is three `NvU32` values: region ID, data size, and data offset.
The offset is relative to the start of the image. The parser first locates
regions `0x0f` and `0x12`; the first word of region `0x12` is the image's
netlist number. The generic parser also has paths for these newer-layout
context-switch microcode regions:

| Region | Destination |
|---:|---|
| `0x3d`, `0x3e` | FECS images |
| `0x3f` | GPCCS DMEM pointer and sizes at `+0x1e0/+0x1e8/+0x1ec` |
| `0x40` | GPCCS IMEM pointer and sizes at `+0x1d0/+0x1d8/+0x1dc` |

These four IDs are not present in the normal TU102 image found below. The
active TU102 image uses the older 40-region layout. The table records real
parser paths, but it must not be read as the region list of the TU102 image.

The selected number comes through the GPU HAL slot at `+0x328`. The common
implementation is named `gpuGetNetlistNumber_inferred` at `0x51f60e4`; the
TU102 wrapper is `gpuGetNetlistNumber_TU102_inferred` at `0x5218b30`. If the
common source returns zero, the TU102 wrapper reads BAR0 `0x00100c7c`. A set
bit in mask `0x00900000` selects fallback netlist `0x90`; clear bits reach an
assertion path.

A new read-only live check found:

| Source | Value |
|---|---:|
| Host RM GPU-info index `0x12` (`NETLIST_REV0`) | `0` |
| Host RM GPU-info index `0x13` (`NETLIST_REV1`) | `0` |
| GSP-forwarded GPU-info index `0x12` | `0` |
| GSP-forwarded GPU-info index `0x13` | `0` |
| BAR0 `0x00100c7c` | `0x00010400` |
| `0x00100c7c & 0x00900000` | `0` |

#### Embedded image inventory and the normal TU102 choice

The bindata table in this exact GSP ELF is now parsed directly. Its private
record type is 24 bytes: uncompressed size, compressed size, data pointer,
flags, and relative offset. All 495 nonzero records inflate correctly as raw
DEFLATE. Exactly six records have the GR netlist image header and region-table
shape consumed by `kgraphicsParseNetlistImage_inferred`:

| Chip path | Chip HAL index | Bindata entry / record VA | Size / compressed | Region `0x12` | Decompressed SHA-256 |
|---|---:|---|---:|---:|---|
| TU102 | 37 | 34 / `0x4bf4408` | `0x1ecc8` / `0xbcc2` | `0x18` | `598f8e529afdcf220d1b20df44fcf3a31047710e119d8c3fb370c28a82eb5ba7` |
| TU104 | 38 | 36 / `0x4bf4438` | `0x20398` / `0xc247` | `0x18` | `24c6b1c2c21af67603c5d953b7aaeb3882aa3ef4e547028b1d731c2100a36288` |
| TU106 | 39 | 32 / `0x4bf43d8` | `0x1ecc0` / `0xbcc3` | `0x18` | `b70c061f6755046dd63ba4dff11be15a779c2210fa33323aa63f72e582f74812` |
| TU116 | 40 | 33 / `0x4bf43f0` | `0x1ea18` / `0xbb0d` | `0x0c` | `726221cdc1a014e1489e919b4b3e2cda0da836e0e200e4bd168044c65521721d` |
| TU117 | 41 | 35 / `0x4bf4420` | `0x1ea18` / `0xbb0e` | `0x0c` | `13d9bf8bf3c43071fed91f488243979bdfc6728737b3a2ee16822ff961e2376a` |
| GA100 | 42 | 37 / `0x4bf4450` | `0x2ce00` / `0x1055e` | `0x15` | `28774dc54e9800ef27ce2fdf85ebfc1f1721df82c57e86a45b3cc43605264349` |

The chip choice is also proved in code. Function
`chipHalVarIdxFromArchImpl_TU10x_inferred` at `0x58e6ab0` maps architecture
`0x16` and implementations `2, 4, 6, 8, 7` to HAL indices `37..41`. The parent
mapper gives GA100 index 42. The KernelGraphics HAL binder uses index 37 for
TU102 and installs only `kgraphicsGetNetlistImage_TU102_inferred` at
`0x5b12834`; the other five main image slots are zero-return stubs.

`kgraphicsAcquireNetlistImages_inferred` at `0x5231904` walks the six pointer
slots at inferred `GraphicsManager+0xc00`, calls the selected accessors, passes
each non-null storage record to the exact open-source function
`bindataStorageAcquireData`, and stores the inflated image pointer. This joins
the bindata records to the parser and proves that they are runtime inputs, not
false-positive data.

For the normal physical TU102 path, entry 34 is therefore the sole non-null
embedded candidate and its netlist number is `0x18`. The only embedded
netlist numbers in this firmware are `0x18`, `0x0c`, and `0x15`; there is no
embedded `0x90` image. This explains the failed force-`0x90` test without
needing another GPU reset.

The two public revision values do not reveal the active netlist in the stock
host driver. Exact 610.43.03 source in
`subdevice_ctrl_gpu_kernel.c::getGpuInfos` hard-codes both indices to zero.
IDA shows that GSP's physical handler is different: index `0x12` calls the
same GPU HAL method at `+0x328`, and index `0x13` calls its adjacent revision
method. The board-scoped diagnostic patch in
`experiments/cmp50-netlist-forward` forwards these two GET requests to GSP
instead of replacing their results.

The forwarding patch was built against the exact combined V551-stockflow and
RT-count source and loaded as a temporary module. Both physical GSP results
were still zero. The zero is therefore not only a host-side placeholder. This
does not mean that no netlist is loaded: the image parser can use region
`0x0f` to choose an image when the getter returns zero, then stores that
image's region-`0x12` value at `KernelGraphics+0x1194`.

No `RMForceNetlistNumber` setting was present in the normal live module
parameters or modprobe configuration. A temporary diagnostic load with
`RMForceNetlistNumber=0x90` was tested after a PCI function reset. It did not
reach a usable GPU: GSP initialization timed out, the stockflow retry path then
reported Booter error `0x29`, and RM ended with
`RmInitAdapter failed (0x62:0xffff:2119)`. The test is rejected and must not be
repeated as an unlock path. Unloading the test module, applying PCI FLR, and
loading the normal installed module restored the card to P0 with `3584` CUDA,
`448` Tensor, `56` reported RT cores, and the same on-disk module hash.

The normal TU102 image choice is no longer open: it is entry 34 with number
`0x18`. A forced `0x18` live load would ask for the same image and would add
little evidence while still requiring a module unload and GPU reset, so it
was not run.

This also removes the earlier CMP-specific-netlist idea as the main Xid 109
cause. The chip HAL key is TU102 architecture/implementation, not CMP SKU, and
the same standard TU102 image is selected. FECS/GPCCS may still read RT fuse or
context state while running, but there is no separate CMP netlist to replace.

The next main target is below image selection and below the now-closed GSP
count path: RT-class state used when the first traversal method reaches GR,
plus the exact FECS context field that fails to switch. The persistent host
count patch should stay because it is already proved to open the user-mode API
gate, but a second patch must fix real execution rather than change either the
reported count or the netlist number.

### Exact production Falcon images

The normal embedded TU102 netlist contains the exact production context-switch
firmware used by this driver. The older-layout region mapping is proved by the
GSP parser and the corrected TU102 loader:

| Region ID | Payload | Bytes | SHA-256 |
|---:|---|---:|---|
| `0x01` | FECS IMEM | `29373` | `1be861e5ce2eb6349d5a24d91b4280735c09a217941485e9eace9d3e80572cea` |
| `0x00` | FECS DMEM | `5272` | `a8b25b50bc4bab115f0f17516d5a3331f1a48672db2b00a90af73af0255ec7cd` |
| `0x03` | GPCCS IMEM | `12584` | `f8a57f19da68a98131dcb736d66ceae7cd145e1de214427866b8036a7b713c4b` |
| `0x02` | GPCCS DMEM | `2896` | `11a54e23a2443b236e0bc38384792cd5a7ef2902c8c8bdfac33fce31cfc21dbf` |

`tools/cmp50/extract_gsp_netlist.py` makes the extraction repeatable from the
exact GSP ELF and bindata record VA `0x4bf4408`. The local IDA 9.4 install has
no Falcon processor, so both exact IMEM images were decoded with `envydis` as
Falcon generation `fuc6`. They decode from offset zero with no invalid
instruction marker:

| Exact 610.43.03 image | Decode lines |
|---|---:|
| `fecs_imem_exact_610.43.03.bin` | `9623` |
| `gpccs_imem_exact_610.43.03.bin` | `4159` |

The public TU102 images remain useful comparison inputs, but they are different
builds:

| Public reference image | Bytes | SHA-256 | Decode lines |
|---|---:|---|---:|
| `fecs_inst.bin` | `29080` | `1f1b45a2ad4ebbf38a18dff10ef0ad3c32fa93184678c4f8741a2b64036997c1` | `9538` |
| `gpccs_inst.bin` | `12717` | `484632eef86de685e3bd113c074aadbcd20328aedc46b896015c531f383c1624` | `4197` |

They are not safe patch inputs for 610.43.03 because their sizes and hashes do
not match the production images above.

The exact 610.43.03 file `ucodes_tu10x-610.43.03.bin` is not that payload. It
is 12032 bytes, SHA-256
`dcbdf512ab09b7f6d946e7f415bcfbc9137f5db1cf0c3c576f4b34b5275acb38`, and
contains a 24-byte `NVUCODES` header with version 1, 496 entries, and
fingerprint `0x8d1990ab6b98ae2b`. Every byte after that header is zero. It
therefore contains no FECS or GPCCS instruction image to patch.

The Rust `faucon` project was also built and tested. Its current main branch
explicitly supports only `fuc5`. It decodes the Turing GPCCS image through
offset `0x2b`, then fails on the `fuc6` `bclr $flags, $p2` instruction at
offset `0x2e`. It is a possible base for future `fuc6` tooling, but it is not
an exact disassembler or emulator for this payload today.

#### RTX versus non-RT Turing netlist signature

All 40 regions were extracted for TU102, TU104, TU106, TU116, and TU117. Only
regions `0x00`, `0x01`, `0x02`, `0x03`, `0x05`, `0x06`, `0x0a`, and `0x12`
differ. Regions `0x05`, `0x06`, and `0x0a` split exactly into one common value
set for RT-capable TU102/TU104/TU106 and another for TU116/TU117. The entire
register-table difference is three values:

| BAR0 register | TU102/TU104/TU106 | TU116/TU117 |
|---:|---:|---:|
| `0x00419bc8` | `0x00398a2c` | `0x00398a42` |
| `0x00419bf0` | `0x944077fe` | `0x844077fe` |
| `0x00419e5c` | `0x000058c1` | `0x00005cc1` |

A read-only live BAR0 check on CMP 50HX returned all three RT-capable values
exactly. The card therefore loads and retains RTX-style GR netlist state; a
GTX-style netlist is not the missing execution gate.

The proved RT-count fuse shadow at BAR0 `0x21168` remains zero. A tightly
scoped volatile host write probe requested bit 0 and read it back immediately.
The value stayed zero and the GPU remained healthy at P0. This proves that an
ordinary host BAR0 write cannot change the shadow after initialization. It
does not rule out a privileged early-Booter override or a different override
register.

After the timeout capture, the same test module was reloaded through FLR with
no debug registry keys. The card returned to P0 at about 1905 MHz. The combined
stockflow and RT-count module was then installed, added to initramfs, and
verified after reboot. No real ray dispatch was repeated because it is a known
reset-required failure until the context-switch path changes.

## Current evidence

`DP4A` is present and gives correct results, but public tests show a much lower
issue rate than on RTX Turing. `DP2A` and separate multiply/add paths can be
faster. This proves an instruction-rate limit, not a missing `DP4A` unit.

NVIDIA driver 610.57.04 exposes these fuse results through
`NV2080_CTRL_CMD_GR_GET_SM_ISSUE_RATE_MODIFIER`:

- `IMLA0`
- `FMLA16`
- `DP`
- `FMLA32`
- `FFMA`
- `IMLA1` through `IMLA4`

The same header defines full speed and reduced speeds down to 1/64. The GSP
firmware reads these fuse values before the host driver reports them.

### GSP SM-speed override branch

An early trace found an alternate implementation at `0x52abe9c`. It passes
relative OBJFUSE offsets `0x381c` and `0x3820`, which the TU102 OBJFUSE
resolver would map to BAR0 `0x2181c` and `0x21820`. That address translation is
valid for this function, but a full HAL trace now proves that this function is
not the final TU102 Graphics callback.

For TU102 chip HAL index 37, final `Graphics+0xb08` is `0x528f508`, named
`graphicsWriteSmSpeedSelectOverridesViaRegMap_inferred` in the IDB. It writes
register IDs `0x9664` and `0x966c` through the register-map object at
`Graphics+0x1200`. These IDs match the protected FECS registers used by the
working stockflow path: BAR0 `0x409664` and `0x40966c`.

The old OBJFUSE pair remains useful only as evidence for the alternate
implementation:

| Relative offset | TU102 BAR0 |
|---:|---:|
| `0x381c` | `0x2181c` |
| `0x3820` | `0x21820` |

The same resolver maps relative `0x1378` to published TU102
`NV_FUSE_OPT_NVDEC_DISABLE` at `0x21378`, which is an independent check. The
address translation is proved, but it does not make `0x2181c`/`0x21820` the
TU102 SM-speed path. A direct write tool based on that old assumption is now
disabled.

The effective TU102 readback format is now separate, proved evidence. The
TU102 KernelGraphics HAL binder installs
`kgraphicsGetSmIssueRateModifier_TU102_inferred` at `0x528fcf0`. It reads a
32-bit word from register offset `0x9668` and expands these fields:

| Field | Readback bits |
|---|---:|
| `IMLA0` | `2:0` |
| `FMLA16` | `5:3` |
| `DP` | `6` |
| `FMLA32` | `9:7` |
| `FFMA` | `12:10` |
| `IMLA1` | `15:13` |
| `IMLA2` | `18:16` |
| `IMLA3` | `21:19` |
| `IMLA4` | `24:22` |

This proves the field order and the effective speed-select values reported by
RM. Together with the corrected TU102 `+0xb08` callback, it also joins the GSP
registry override path to the same FECS register family used by stockflow.
Stockflow is still different because it opens the protected FECS PLM through
the signed Booter path before writing the values.

The adjacent FECS registers are now partly identified and are not an RT
shortcut. Envytools names `0x409658`
`NV_PGRAPH_PRI_FECS_FEATURE_OVERRIDE_ECC`. NVIDIA's published GV100 register
header names `0x409660` `NV_PGRAPH_PRI_FECS_FEATURE_READOUT` and defines bit
16 as the effective ECC-DRAM enable. The live CMP value `0x000000f3` has bit
16 clear. No GSP TU102 Graphics HAL function in the scoped `0x5280000` through
`0x5291000` scan references `0x9654`, `0x9658`, `0x965c`, or `0x9660`; the
proved references in that family are the SM-speed override/readback registers
`0x9664`, `0x9668`, and `0x966c`. Registers `0x409654` and `0x40965c` remain
unnamed, but their location alone is not evidence of an RT enable.

A later full Graphics-HAL scan found four TU102-selected readers of `0x409660`
outside that first address range. They test bits `12`, `13`, `17`, and the pair
`18:19`, with a software override byte for each result. This first looked like
a good RT lead because the binder mask `0xE0` selects chip indices 5, 6, and 7,
which are TU102, TU104, and TU106. The state-owner trace disproves that reading:
`0x505f0a0` reads the exact registry keys `RMEnableL1ECC`, `RMEnableSMECC`,
`RMEnableSHMECC`, and `RMNoECCFuseCheck`, then manages the same feature-byte
cluster used by those readers. The mask groups Graphics ECC implementations;
it is not proof of an RT-capable-die gate.

The IDB now names that owner
`graphicsApplyEccRegistryOverrides_inferred`. The four TU102 readers at
`0x52fd660`, `0x52fd8dc`, `0x52fd95c`, and `0x52fd9dc` have bit-specific ECC
names, typed `(OBJGPU *, Graphics *)` parameters, and comments that keep the
exact ECC unit names unresolved. No byte or live register was patched. This
closes `0x409660` as the next RT experiment while preserving it as useful ECC
documentation.

The fuse-space values at BAR0 `0x21804` and `0x21814` are also not proved RT
feature controls on TU102. The exact GSP has one method that reads relative
fuse offset `0x3814`, but the OBJFUSE HAL binder selects it only for a different
chip-family index. For TU102 (`HalVarIdx 37`, low index 5), the same table slot
is now named `objfuseHalSlot168NoOp_TU102_inferred`, a six-instruction no-op,
while the next slot is the constant-true
`objfuseHalSlot170ReturnTrue_TU102_inferred`. Both functions and the two binder
stores are named or commented in the IDB. The published
`NV_FUSE_FEATURE_READOUT` name found in
the 610.43.03 source belongs to GA100 at `0x823814`; it does not name TU102
BAR0 `0x21814`. The read-only BAR0 tool therefore keeps both TU102 addresses
only as unknown observations and no longer labels either one as an RT feature
override.

The exact GPCCS image also contains I/O instructions that name address
`0x21800`, including a runtime branch at GPCCS IMEM `0x158c` to a block at
`0x1682` that writes `0x04000000`. This is not RT-specific evidence. The
TU116 GPCCS image has the same block byte-for-byte; the complete TU102/TU116
GPCCS images differ at only three later bytes. On the live CMP 50HX, a
read-only BAR0 read of `0x21800` returns zero after GPCCS is running. The
instruction can be a chip/platform branch, a write-only or self-clearing
control, or a Falcon I/O mapping detail. It is therefore recorded in the
probe, but is not a safe RT-write candidate.

## Authenticated stockflow package

The local `cmpunlocker-v0.1.28-linux-x64-50hx-stockflow` package was compared
with the [official project](https://github.com/pearlfortune/cmpunlocker) and its
[`v0.1.28` release](https://github.com/pearlfortune/cmpunlocker/releases/tag/v0.1.28):

- the official archive SHA-256 is
  `f113dd5680f4c098e973d15eca59145cf2ace4b2358907b22c8f454039fc464a`;
- the binary, build scripts, patches, `LICENSE`, `NOTICE`, and checksum file in
  the local folder match the official archive;
- the local `README.en.md` is an extra file from the repository's newer main
  branch, not a file from that release archive;
- all three files in the shipped checksum manifest match;
- the `610.43.03` patch applies cleanly in a read-only dry run to NVIDIA's
  source tarball with the exact SHA-256 required by the build script.

The package supports device `10de:1e09` only when the subsystem is either
`10de:1554` or `1462:371f`. The patch contains code for driver versions
`580.173.02` and `610.43.03`. The newer README also lists a `580.159.03` lane,
but no stockflow patch for that driver is present in this package.

The upstream report says `610.43.03` was tested on one card and on six
`1462:371f` cards, including repeated reboots. We have now also reproduced the
610.43.03 full-speed result locally, including a persistent install and clean
module reloads.

### Static mechanism

The patch does not flash the VBIOS. It enlarges the Booter signature allocation
to `0xfa00` bytes and places a crafted ROP payload in it. The payload reuses
code gadgets in NVIDIA's signed SEC2 Booter. It does not load a new unsigned
Falcon program.

The key ordered stores made by the payload are:

| Step | BAR0 target | Value | Purpose in the patch |
|---:|---:|---:|---|
| 1 | `0x00409650` | `0xffffffff` | Open FECS feature-override PLM |
| 2 | `0x00409664` | `0x88888888` | Set SM speed override word 0 |
| 3 | `0x0040966c` | `0x00000008` | Set SM speed override word 1 |
| 4 | `0x00409650` | `0xffffff8f` | Put the FECS PLM back |
| 5 | `0x001fa828` | `0x00000000` | Drop WPR2 high bound |
| 6 | `0x008403c4` | `0x000000ff` | Open the SEC2 reset window |
| 7 | `0x001fa824` | `0x1ffffe00` | Set the WPR2 low sentinel |
| 8 | `0x008403c4` | `0x000000ff` | Keep the reset window for handoff |

The chain uses the Booter writer gadget at PC `0x10aa`. It then releases the
ACR mutex owner token `0xc2` at secure-bus address `0x8e18`, clears `MAILBOX0`,
and enters NVIDIA's cleanup-and-halt path at PC `0x7c43`.

The host patch checks exact readback states, rebuilds the stock signature,
clears SEC2 state, runs the normal FWSEC path, restores the stock WPR2 range,
and then starts normal GSP/RM. One narrow path changes an exact CMP-only GSP RPC
`NV_ERR_TIMEOUT` result to `NV_OK`; later health and full-speed gates still run.
This timeout mask is a real risk and must be watched in `dmesg`.

The package binary is a stripped, static root program. Static strings show
module unload/load, process stop, persistent module install, rollback journals,
and two undocumented autounlock commands. It has now been run on the test card
and its persistent 610.43.03 path is working. Its claim that the card cannot be
bricked should still be read only as "no SPI/VBIOS flash": the ray-query test
proved that a protected-state or driver failure can hang a GPU until reset.

### Independent Booter image mapping

The signed Booter image can be recovered without running the package or opening
a GPU device. `tools/cmp50/extract_booter.py` reads NVIDIA's generated bindata C
file, checks its declared sizes, decodes raw DEFLATE, and refuses to overwrite
an existing output directory:

```bash
python3 tools/cmp50/extract_booter.py \
  --source "$NVIDIA_SRC/src/nvidia/generated/g_bindata_kgspGetBinArchiveBooterLoadUcode_TU102.c" \
  --output cmp50-booter-610.43.03
```

For the exact `610.43.03` source pinned by the package, the production image is
`0xe700` bytes and has SHA-256
`e0f0fc93da097b5b68e5af3adb58b2235ed1fad5fce0b23592d3895af44cb743`.
The decoded nine-word header is:

| Field | Value |
|---|---:|
| OS code offset / size | `0x0000` / `0x0100` |
| OS data offset / size | `0x8500` / `0x6200` |
| Application count | `1` |
| Application code offset / size | `0x0100` / `0x8400` |
| Application data offset / size | `0x0100` / `0` |

NVIDIA sets `bBootFromHs = false` for TU102. Its direct loader copies the first
code range to IMEM address `0`, then copies the secure range from file offset
`0x100` to IMEM address `0x100`; both offsets are also used as Falcon tags.
Therefore, for this exact image, Booter PC `x` maps to uncompressed image and
`booter-load-tu102-prod-imem-layout.bin` offset `x`. It also confirms that the
production signature patch is at image offset `0x8700`, or DMEM offset `0x200`.

There is an important limit. The first `0x100` bytes are a clear non-secure
Falcon loader stub. `envydis -m falcon -V fuc6` decodes that range cleanly,
including the initial stack setup, the `0x31` mailbox sentinel, the secure-code
transfer, and the call to PC `0x100`. The application range from `0x100` is an
opaque secure payload in the archive. The same disassembler does not decode a
valid instruction stream at stockflow PC `0x10aa`. Byte windows at the listed
PCs are therefore archive ciphertext, not runtime gadget bytes.

This independently proves the image identity and address layout, but not the
meaning of any stockflow gadget. NVIDIA also describes HS Falcon state as a
[host-inaccessible black box](https://download.nvidia.com/open-gpu-doc/Falcon-Security/1/Falcon-Security.html).
A direct IDA import of the extracted production payload would only analyze
ciphertext. Independent gadget proof needs a decrypted runtime IMEM dump or
another matching cleartext image. Until then, PCs `0x10aa`, `0x0d27`, `0x1cdd`,
and `0x7c43` remain stockflow-source claims backed by its reported hardware
result, not IDA-backed findings.

## Stockflow alone is a compute path, not a PCIe path

The question was whether the working
`cmpunlocker-v0.1.28-linux-x64-50hx-stockflow` path should have been used for
the Gen2 experiment. The answer is: it is the right path for the compute
limiter, but it cannot change the PCIe link capability.

The `610.43.03` patch changes the signed TU102 Booter flow. Its relevant
hardware state is:

- SEC2 Falcon/Booter execution and cleanup;
- FWSEC and GSP/RM handoff;
- FECS feature-override PLM at `0x00409650`;
- FECS SM speed override words at `0x00409664` and `0x0040966c`;
- WPR2 bounds at `0x001fa824` and `0x001fa828`;
- SEC2 reset protection at `0x008403c4`.

The full-speed values are `FECS[0]=0x88888888` and `FECS[1]=0x00000008`,
followed by the protected handoff and normal GSP/RM startup. This is why the
same card already reaches about `107.2` FP16 Tensor TFLOPS with `3584` CUDA
and `448` Tensor cores.

The patch was searched for PCIe capability/config-space identifiers, including
`RMPcieLinkSpeed`, `NV_XVE`, `CAP_EXP`, and PCIe link-speed/width writes. None
were found. The one `0x880` occurrence is a signed Booter signature-descriptor
offset, not PCIe BAR0 offset `0x88084`/`0x88088`/`0x880a8`.

Therefore we did not take the wrong route. We tested two separate controls:

```text
stockflow -> signed Booter/SEC2/FWSEC -> FECS/WPR2 -> compute speed
PCIe test -> RMPcieLinkSpeed/RmForceEnableGen2 -> endpoint capability/training
```

The old stockflow patch alone cannot produce Gen2. The working all-feature
patch extends its signed-Booter transaction to open the separate TU102 XP3G
policy page, then applies the recovered Turing PCIe controls and asks the
upstream bridge to retrain. Compute and PCIe remain separate controls even
though one end-user module now carries both.

## Historical PCIe Gen2 experiment: negative result on 2026-08-12

This section records why registry values alone were insufficient. It is not
the current result; the protected kernel path reached Gen2 x4 on 2026-08-13.

The isolated experiment in `experiments/cmp50-pcie-gen2` was run on the remote
`10de:1e09` CMP 50HX with subsystem `10de:1554` and the installed NVIDIA
610.43.03 open kernel module. The root baseline confirmed:

- GPU endpoint: current Gen1 x4; Linux PCIe capability Gen1 x16;
- upstream AMD bridge `0000:00:01.1`: current Gen1 x4, maximum Gen3 x8;
- NVIDIA RM summary: maximum Gen2 x16, current Gen1;
- active `RegistryDwords`: empty.

The temporary module load accepted exactly:

```text
RMPcieLinkSpeed=0x1;RmForceEnableGen2=0x1
```

After the load, NVIDIA RM still reported `Current 1`. Both the GPU endpoint
and the upstream bridge remained at `2.5 GT/s PCIe`, x4. `nvidia-smi -L`
remained healthy. No matching NVIDIA Xid, PCIe AER fault, bus drop, GSP
timeout, or Gen2 training failure was found. The normal module was restored;
the final `RegistryDwords` value was empty and the link returned to Gen1 x4.

A second root read-only capture checked the raw PCIe capability and BAR0
mirror. The endpoint returned `CAP_EXP+0c.l=0x00453d01` (maximum Gen1 x16),
`CAP_EXP+10.l=0x10410140` (current Gen1 x4), and
`CAP_EXP+30.l=0x00000001` (target Gen1). BAR0 offsets `0x88084`, `0x88088`,
and `0x880a8` returned the same maximum, current, and target values. The
upstream bridge returned maximum Gen3 x8 and current Gen1 x4.

The exact GSP function `init_pcie_registry_settings` at `0x4CA3218` reads
`RMPcieLinkSpeed` and stores its raw DWORD at the PCIe state object offset
`+0xA40`; the checked disassembly has no PCIe Link Capabilities write. The
open driver source reads `RmForceEnableGen2` only to set
`PDB_PROP_CL_PCIE_FORCE_GEN2_ENABLE`. This makes the result stronger than a
single failed training attempt: the endpoint advertises no Gen2 capability.

A current read-only capture on host `192.168.1.221` checked the same card
again. It adds the PCIe Supported Link Speeds Vector `LinkCap2=0x0002`
(2.5 GT/s only), the same value through PCI config and the NVIDIA BAR0 mirror,
and `CYA_0 bit2 DIS_G2=0` (Gen2 is not disabled by that simple control). The
AMD bridge still reports Gen1-3 support. The 170HX `OPT_GEN23`/`OPT_GEN3`
registers are unmapped on TU102, and the XP3G override block is PLM-locked.
The capture is kept in
`experiments/cmp50-pcie-gen2/runs/20260812T1317Z-170hx-regset/capture.txt`.

One later signed-Booter candidate changed the first FECS PLM target to the
inferred XP3G PLM `0x8e1b0`. It read `0xffffff8f` before and after a successful
Booter run. A final payload audit shows that the second-exploit branch requested
only `0xffffffff` at `0x8e1b0`. Its later `0xffffff8f` write targets FECS PLM
`0x409650`, not XP3G. The host read the candidate immediately after the Booter
call and before the stock signature rebuild. This result is `write_ignored`.
The probe only read LinkCap, LinkCap2, and LinkCtl2; it did not write them or
retrain the link.

A focused IDA pass over `gsp_tu10x_610.43.03.elf` then checked full constants,
RISC-V split addresses, data xrefs, function-pointer tables, and the relevant
disassembly. It found no direct stock-GSP reference to `0x8e1b0..0x8e1bc`, so
the exact PLM name remains inferred. It did find the separate
`RMPcieLinkSpeed` hardware policy routine at `0x4cb25b8`. That routine directly
changes Link Control 2 `0x880a8`, `PRIV_MISC_1` `0x8841c`, `LINK_CONFIG_0`
`0x8c040`, `PL_LINK_RATE` `0x8c1c0`, and `CYA_0` `0x8c2c0`, but has no recovered
XP3G-page access. The full static record is
`experiments/cmp50-privilege-map/evidence/20260812-xp3g-gsp-ida-map.md`.

Therefore, this historical run proved only that the normal RM registry and
VBIOS-exposed path were insufficient. The later all-feature patch used the
exact TU102 protected path and an explicit upstream-bridge retrain; that path
is now live-proved at Gen2 x4. No lane-width override is part of the solution.
The raw report is kept in
`experiments/cmp50-pcie-gen2/runs/20260812T061026Z`, and the raw capability
proof is in `experiments/cmp50-pcie-gen2/runs/20260812T061656Z`; the current
host repeat is in `experiments/cmp50-pcie-gen2/runs/20260812T1317Z-170hx-regset`.
The corrected Booter evidence and the full target-specific access map are in
`experiments/cmp50-privilege-map`.

### Driver-local RTX 2080 Ti PCI ID alias

The 610.43.03 open kernel module copies Linux `pci_dev->device` into
`nv->pci_info.device_id` in `nv_pci_probe()` before calling
`rm_is_supported_device()` and `rm_init_private_state()`. A guarded,
off-by-default experiment replaced only that copied value with RTX 2080 Ti ID
`1e07` on physical CMP 50HX `10de:1e09`, subsystem `10de:1554` or
`1462:371f`. Linux PCI enumeration and configuration space were not changed.

The clean-boot test on subsystem `10de:1554` proved the exact handoff with:

```text
NVRM: CMP50_PCI_ALIAS: physical=10de:1e09 rm=10de:1e07 subsystem=10de:1554
```

That field is not authoritative for the later product identity. `nvidia-smi`,
CUDA, `lspci`, and sysfs all still exposed `1e09` and `NVIDIA CMP 50HX`. RM
still returned `CMP_SKU=1` and `DISPLAY_ENABLED=0`. Stock CUDA 12.0.146
`nvprof` still printed the CMP warning and recorded no activity, while stock
Nsight Compute 2022.4.1 still returned `ERR_NVCMPGPU` with exit 255. Thus the
private CMP classifier is rebuilt later from another RM source or immutable
board data; this early Linux PCI copy is not its controlling input.

The alias itself caused no regression: CUDA exited zero, all issue-rate values
remained full, RM reported 3584 CUDA, 448 Tensor, and 56 RT cores, and ReBAR
plus PCIe Gen2 x4 remained active with no Xid or PCIe AER error. The original
installed modules and alias-off boot configuration were restored afterward.
Because the alias changed no useful result, its code and module parameter were
removed from the all-feature package. The negative evidence remains in
`experiments/cmp50-pci-id-alias` so this path is not repeated.

### CUPTI and Nsight user-space unlocks

CUDA 12.0.146 `libcupti.so.12` creates a per-device state and asks the private
driver interface whether the device is CMP. On CMP 50HX it stores `1` at state
offset `0xA38`; the same initialization function then returns
`CUPTI_ERROR_CMP_DEVICE_NOT_SUPPORTED` (`42`). The public
`cuptiDeviceSupported()` call still reports the device as supported, so
overriding that public function does not bypass the real gate.

For the Ubuntu library with SHA-256
`d846f6110f1ac3a1f58ee531dadce415f6c001f7465183663a45569bb7013249`, changing
only file offset `0x12b558` from `01` to `00` stops that flag from being set.
The patched private copy has SHA-256
`b0688b349041405449b68b53e4bd5b7ec66988dc56fbadf124bb3564da8cac8f`.
`nvprof` then records the test kernel and CUDA API calls with no CMP warning or
internal profiler error. The card remains healthy and the stock system library
is not modified.

The exact guarded patcher, private-library launcher, smoke test, IDA evidence,
and live result are in `packages/cmp50-cupti-12.0.146` and
`experiments/cmp50-cupti-unlock`.

Nsight Compute 2022.4.1 has a separate copy of the same product policy. Its
`libcuda-injection.so` stores a private CMP query result at per-device state
offset `0xB2A`. The public GPU-support check, profiler session start, and PC
sampling session start all use that shared byte. Replacing only the five-byte
query call at file offset `0x85eb24` with `xor eax,eax` and NOPs keeps the
normal state setup but stores zero. The guarded private copy changed from
SHA-256 `0689cfdd20bf9cb1aabd225cdacdd61726d0368d0e8d89b9ae229d0f35222bc0`
to `e15f5740e4da6ba3792f38253e8824e207205d710c2bf9a10cdd38a7865a096c`.
On the card, `ncu` then completed one pass and read
`sm__cycles_elapsed.avg = 3,859.39` for the test kernel. Patching only later
support or session branches was rejected because it left the shared CMP state
set and made later code fail.

Nsight Systems 2022.4.2 carries its own CUDA 12 CUPTI library. Its matching
one-byte store immediate is at file offset `0x12b4b8`. The guarded private
copy changed from SHA-256
`0ae68983da177190a2b34c031d599e7a13b42682472644335b1a8de7d20ffb40`
to `8a65881f0672e1406ab4cd4673720fb92329c3abec2fed6803bcb076f468ed6d`.
The smoke test made a valid `.nsys-rep` and `gpukernsum` reported the
`cmp50_nsys_probe(float *)` kernel. The private tree also links the Ubuntu
host importer into the layout expected by `nsys`; no installed Nsight file is
changed. An A/B run in the same fixed layout, with only stock CUPTI restored,
made a report with no CUDA kernel data; the direct probe itself still exited
zero.

The version-bound Nsight packages are in
`packages/cmp50-nsight-compute-2022.4.1` and
`packages/cmp50-nsight-systems-2022.4.2`. All three packages require CMP 50HX
PCI device `10de:1e09`; their builders check the exact source hashes and their
wrappers check the patched hashes. System files stay unchanged.

## Feature matrix

| Area | Current view | Proof needed |
|---|---|---|
| CUDA scalar work | Local stockflow full-speed state is stable | Keep correctness and issue-rate regression tests |
| Tensor cores | Working: 448 cores and about 107.2 FP16 Tensor TFLOPS | LLM end-to-end tests |
| RT cores | Count 0 -> 56 exposes ray query; first ray opcode raises SM `INVALID_OPCODE`, then FECS stalls and Xid 109 follows | Find the protected opcode-legality state or override |
| 3D APIs | Vulkan device and ray-query feature exposure work with the count patch | Non-RT Vulkan/OpenGL tests; RT waits for the GR fix |
| PCIe width | Working at x4; bridge maximum is x8; no width override is used | Board inspection and a separate width experiment for anything above x4 |
| PCIe speed | Working Gen2 after protected TU102 policy setup and bridge retrain; OpenCL transfer bandwidth doubled | Keep cold-boot, Xid/AER, and transfer-bandwidth regression checks |
| Display | Display fuse and missing board output path are separate | Fuse read, engine list, board check |
| NVENC/NVDEC | May be fused off | Fuse read, engine list, encode/decode test |
| CUPTI/Nsight | Working for nvprof 12.0.146, Nsight Compute 2022.4.1, and Nsight Systems 2022.4.2 with private, hash-gated copies; real API, kernel, and SM-counter records captured | Keep system files unchanged and add separate guarded patterns for newer builds |
| Secure firmware path | Stockflow is locally working; direct code replacement is still signed/blocked | Exact FECS/GPCCS image and context trace |

## Next realistic unlock candidates

Exact RTX 2080 Ti equivalence is not possible by software alone: this card
reports `56` SMs / `3584` CUDA cores / `448` Tensor cores and has a 10 GB
memory layout, while the missing SMs and memory are physical configuration.
The useful candidates are therefore:

1. **Real RT execution — highest value and the main target.** The host count
   override already opens the user-mode API gate, and the card has the RTX
   Turing GR-netlist values and valid RT context buffers. The first
   `OpRayQueryInitializeKHR` machine-code group raises SM warp error 9,
   `INVALID_OPCODE`; FECS stalls later. The next work is to locate the
   fuse-derived or protected SM/GR field that makes these Turing ray opcodes
   legal. Patching the later exception or Xid reporter alone is not useful.
2. **CMP profiler compatibility — solved for the tested CUDA 12 tools.** RM
   still reports `CMP_SKU=1`, but private, hash-gated copies now clear the
   product-policy state in CUPTI 12.0.146, Nsight Compute 2022.4.1, and Nsight
   Systems 2022.4.2. Live tests captured CUDA APIs, kernels, a real SM metric,
   and a valid Nsight Systems report. No installed NVIDIA file is changed.
   Other versions still need their own exact byte proof. This is a tool
   compatibility unlock; it does not add SMs, RT execution, memory, or
   bandwidth. See `experiments/cmp50-cupti-unlock` and the three
   `packages/cmp50-*` profiler packages.
3. **Protected SM issue-rate tuning — already solved for this card.** TU102's
   GSP callback selects FECS register IDs `0x9664`/`0x966c`, and stockflow
   writes the matching protected BAR0 registers. RM reports all nine fields as
   `raw: 0` (full), so this path needs no more change for Tensor/LLM work. The
   earlier direct OBJFUSE helper is disabled because its TU102 premise was
   disproved.

The following are currently poor unlock targets: display (`DISPLAY_ENABLED=0`),
NVDEC (`0x21378 & 7 = 7`, no NVDEC classes), NVENC (no NVENC classes), extra
SMs, and extra memory. These have a hardware or fuse boundary. PCIe Gen2 is no
longer in this list; it is part of the supported all-feature package.

## Read-only baseline

Assumption: the test card can run Linux. From the repository root:

```bash
sudo bash ./tools/cmp50/probe.sh
```

The script accepts only `10de:1e09`. It reads sysfs, PCI configuration,
`nvidia-smi`, and a fixed set of BAR0 registers. It contains no PCI or BAR0
write operation. Use `--skip-bar0` when root BAR access is not wanted.

The two key results are:

- `<report>/<BDF>/rm-issue-rate.json`: the active issue-rate values returned by
  NVIDIA RM. `raw: 0` means full speed. Other values mean reduced speed; the
  file also gives the named ratio where NVIDIA defines one. The same GET-only
  probe now reports CMP/display flags, GPU/RT/Tensor core counts, 2D/3D/compute
  capability bits, public netlist revision indices, and class lists for
  graphics, NVDEC0, NVENC0, DPU, and all engines. It also reports size,
  alignment, and RM status for all 26 public GR engine-context buffer IDs,
  including the two RT buffers. A failed engine query is kept as an RM status,
  not hidden.
- `<report>/<BDF>/bar0.json`: raw values for the published display and NVDEC
  fuses, the secure-GSP-debug fuse, PCIe state, the separate GSP/OBJFUSE
  candidates, and the FECS/WPR2/SEC2 registers used by stockflow. It also
  decodes the effective FECS speed readout at `0x409668` and the TU102 netlist
  fallback selector at `0x00100c7c`.

The RM probe must open NVIDIA device files read/write because this is required
by the ioctl interface. It sends only public GET controls. It does not contain
a SET control or a register-write path. A C compiler is needed to build this
small probe. Build errors are saved in `rm-issue-rate-build.txt`.

## Instruction baseline

Build one test binary and keep it for both the before and after tests:

```bash
nvcc -O3 -std=c++14 -arch=sm_75 tools/cmp50/issue_bench.cu -o cmp50-issue-bench
./cmp50-issue-bench 0 | tee cmp50-issue-before.json
```

The first argument is the CUDA device index. The optional second argument is
the iteration count. The default is `131072`. The test accepts only compute
capability 7.5. It gives the best of three runs for:

- one native `DP4A` per loop;
- two native `DP2A` instructions per loop;
- one `FFMA` per loop;
- separate `FMUL` and `FADD` instructions per loop.

The float paths use inline PTX, so the compiler cannot turn separate multiply
and add instructions back into `FFMA`. A good first override must make `DP4A`
and `FFMA` faster while keeping correct sample values. Use the same clocks,
power limit, binary, and iteration count for the after test.

## Gate before the first mutation on another card

The first mutating test should be stockflow's temporary `stockflow-probe`, not
a persistent install and not a raw BAR0 write. Run it only after these facts are
recorded and reviewed:

1. The device is exactly `10de:1e09`, and the subsystem is exactly
   `10de:1554` or `1462:371f`.
2. The active driver is exactly `580.173.02` or `610.43.03`, uses NVIDIA's open
   kernel modules, and has a matching kernel build tree.
3. Secure Boot is off.
4. The read-only baseline, RM issue rates, instruction benchmark, `nvidia-smi
   -q`, `lspci -Dvvnn`, and current `dmesg` have been saved.
5. The host is reached through a remote or headless shell, GPU clients are
   stopped, and a cold power cycle is available.
6. One supported card is tested first. Memory, clocks, voltage, PCIe options,
   and other feature experiments stay unchanged.
7. The official archive and inner files match the hashes above, and the module
   candidate was built from the exact source selected by its build script.

`stockflow-probe` temporarily loads the candidate, checks health and full-speed
state, and is designed to restore the stock driver. That restore is not a power
loss guarantee. Keep the stock modules and a recovery path ready.

Do not use `stockflow-install`, `install-autounlock`, or any persistent command
for the first test. Static inspection found that install mode writes modules and
`/etc/modprobe.d/cmp50hx-v534-no-kms.conf`; autounlock also installs a systemd
service and copies the binary to `/usr/local/sbin`.

The first command, after the exact environment and candidate path are checked,
is:

```bash
sudo "$BIN" compute50hx-v534 stockflow-probe \
  --all-cmp50hx \
  --stockflow-candidate "$ART" \
  --acknowledge I-ACCEPT-50HX-V534-COMPUTE-UNLOCK
```

Success must include the package full-speed gate, a clean post-restore driver,
the same correct benchmark outputs, and no new Xid or hard Booter/GSP error.

Display, video engines, and 3D class support remain separate experiments.
PCIe Gen2 is now live-proved in the all-feature package.

## Unverified GSP registry branch

GSP 610.43.03 reads the exact registry keys `RMOverrideSmSpeedSelect` and
`RMOverrideSmSpeedSelect1`, stores both 32-bit values, and sends them through
the TU102 Graphics callback that writes FECS register IDs `0x9664` and
`0x966c`. This IDA-backed path avoids a host-side raw BAR0 write. It is not the
authenticated Booter path used by stockflow and has no isolated hardware result
yet. Its ability to pass the protected FECS write controls remains open.

Keep this as a later, isolated fine-control experiment after a stockflow
baseline is reproducible. Run it only from a headless or remote shell after the
normal NVIDIA modules have been unloaded. Make sure no other modprobe file
supplies `NVreg_RegistryDwords`; in particular, do not mix PCIe options into
this run.

```bash
sudo modprobe nvidia \
  NVreg_RegistryDwords='RMOverrideSmSpeedSelect=0x88888888;RMOverrideSmSpeedSelect1=0x00000008'
grep '^RegistryDwords:' /proc/driver/nvidia/params
sudo modprobe nvidia_uvm
```

The `/proc` line must contain exactly the two intended keys before any
benchmark is run. Then repeat the RM report and the same instruction binary:

```bash
sudo bash ./tools/cmp50/probe.sh \
  --skip-bar0 --output cmp50-rm-override
./cmp50-issue-bench 0 | tee cmp50-issue-rm-override.json
sudo dmesg | grep -Ei 'NVRM|nvidia|Xid|GSP' \
  | tee cmp50-rm-override-dmesg.txt
```

Do not change clocks, power, PCIe settings, or the binary between the before
and after runs. A useful result needs lower `RM` values plus faster `DP4A` and
`FFMA`, with the same correct output values. A module parameter shown in
`/proc` is only proof that RM received text, not proof of a register change.

If module load fails, RM values do not change, or the GPU reports an error,
unload the modules and cold-power-cycle the card. Remove the temporary module
option before the next normal boot. Do not move to raw BAR0 only because the
performance result is negative; first record the RM report, `dmesg`, and
benchmark output.

## UEFI pre-boot issue-rate experiment

`experiments/cmp50-uefi-throttle` now contains a standalone x64 EFI
application for the proven FECS SM-speed state. This is a first-stage direct
pre-boot test, not yet a port of the full signed SEC2 Booter flow.

The probe build contains no active write routine. It accepts only CMP 50HX PCI
ID `10de:1e09`, subsystem `10de:1554` or `1462:371f`, PCI display base class
`0x03`, and successful BAR0 reads. It reports FECS PLM `0x409650`, speed words
`0x409664` and `0x40966c`, and effective readout `0x409668`.

The separate apply build also needs `--apply`. It writes the PLM-open value
first and checks exact readback. If `0xffffffff` does not stick, it stops before
either speed word. If it does stick, it sets `0x88888888` and `0x00000008`,
restores the original PLM, and checks final state. It has one rollback attempt
for a partial write. It never touches SPI, VBIOS, PCIe capability, UEFI
variables, or Windows files.

Both images build without imports as relocatable PE32+ EFI applications. ABI
offset checks cover the small UEFI and PCI I/O interface used by the source.
Native mocked-transaction tests cover a blocked PLM, successful apply,
partial-write rollback, an already-full state, and an unexpected PLM.
The direct hardware test is not run yet. A negative PLM-open result means the
next UEFI stage must reproduce the signed Booter setup, WPR2 repair, FWSEC
handoff, and stock-signature cleanup; adding only more host BAR0 writes would
not help.

## Retired direct OBJFUSE BAR0 experiment

`tools/cmp50/sm_override.py` is kept only to record the old experiment and now
refuses every invocation. The first analysis assumed that alternate function
`0x52abe9c` was TU102's final SM-speed callback. Exact HAL execution disproved
that assumption: TU102 selects `0x528f508`, which uses the protected FECS path.
The following old gates and confirmation text are retained in source for audit
history, but no direct `0x2181c`/`0x21820` write is allowed.

- the PCI device is exactly `10de:1e09`;
- the NVIDIA driver is unbound;
- PCI configuration and sysfs both report power state `D0`;
- `bar0.json` belongs to the same BDF and its current register values have not
  changed;
- the public RM V1 control reports at least one reduced issue-rate field;
- all required BAR0 values are readable and are not `0xffffffff`.

Running the tool now fails closed with the corrected reason:

```bash
sudo python3 tools/cmp50/sm_override.py \
  --bdf 0000:01:00.0 \
  --baseline cmp50-baseline/0000_01_00_0
```

The old direct mode required both `--write` and this exact text:

```text
CMP50HX-1E09-DIRECT-BAR0-VOLATILE-SM-OVERRIDE-2181C-21820-COLD-RESET
```

The text no longer enables a write. Use the proved stockflow mechanism for SM
speed. Do not revive the direct OBJFUSE experiment unless a later chip-specific
HAL trace proves that this exact board selects the alternate implementation.

## Fine-tuning work after full-speed proof

The known stockflow payload sets every speed field to full. It does not yet give
us a safe live tuning interface. The local full-speed result is now stable, so
a later R&D step can test one field at a time through the same protected
SEC2/FECS path:

1. Keep the full-speed payload as the control.
2. Change one speed-select field only; keep all other fields full.
3. Record FECS readback, RM GET values, instruction rate, result correctness,
   clocks, power, temperature, and `dmesg`.
4. Test the known values in order: full, `1/2`, `1/4`, `1/8`, `1/16`, `1/32`,
   and `1/64`. The one-bit DP field can only show full or `1/2`.
5. Restore the full or stock payload and cold-power-cycle before changing a
   second field.

This will turn the current all-or-nothing unlock into measured fine control.
It should be added only after the exact card baseline and first stockflow probe
are available; otherwise we cannot tell a field effect from a boot-path error.

## Planned reference comparison: RTX 2080 Ti

The next RT study will compare this CMP 50HX with a real RTX 2080 Ti. Both use
TU102, so this is the best available reference for separating product fuses from
common TU102 firmware and driver behavior.

1. Record both cards without writes: PCI ID, subsystem, VBIOS, driver, kernel,
   BAR0 size, and PCIe state.
2. Read the same BAR0 set: RT fuse `0x21168`, display fuse `0x21C04`, NVDEC
   disable `0x21378`, secure-debug state, FECS state, and the three RT netlist
   values at `0x419BC8`, `0x419BF0`, and `0x419E5C`.
3. Compare stock RM data: RT count, engine class list, `GRAPHICS_RTV` and
   `GRAPHICS_RTV_CB_GLOBAL` context buffers, GFXP/RTV offsets, and Vulkan RT
   extensions. Keep the CMP count-override result as a separate control.
4. Compare the exact TU102 GSP paths for RT count, netlist selection, netlist
   parsing, and context setup. Do not copy a reference register value into the
   CMP without a matching write path.
5. Use record-only shader and push-buffer traces first. Submit the smallest
   RT initialize test on the RTX reference; do not repeat the CMP RT submit
   until a reference-only difference gives a safe hypothesis.
6. Decide from the first stable difference: a fuse-only difference supports a
   physical product gate; a writable state difference supports a new read-only
   probe; identical state with different opcode behavior moves the target to
   reset-time SM decode state.

The first comparison is read-only. No BAR0 write, PCIe retrain, VBIOS change, or
ray workload on the CMP is part of this plan.

## Windows UEFI DXE implementation (fresh 610.43.03 study)

`ReBarUEFI/Cmp50Pkg` is a separate implementation of the pre-OS part of the
610.43.03 CMP patches. It does not modify generic ReBarDxe and does not use the
old direct OBJFUSE experiment.

The DXE driver matches only `10de:1e09` with subsystem `10de:1554` or
`1462:371f`. Its default mode is read-only `Probe`. An armed boot can:

- expose and select the 16 GiB BAR1 size through XVE (`0x88724`, `0x88bbc`,
  `0x88dcc`) before PCI resource collection;
- install the proved Gen2 internal policy, set both PCIe ends to 5 GT/s, retrain,
  verify the negotiated link, and roll back on failure;
- write the FECS issue-rate values only if FECS PLM is already `0xffffff8f`.

The signed TU102 production Booter was checked directly from NVIDIA's MIT
610.43.03 bindata. Its image, header, signature, patch offset, and metadata are
reproducible with `Cmp50Pkg/Tools/generate_booter_asset.py`. It cannot safely be
started as a stand-alone UEFI unlock: the stock path enters after FWSEC and
requires a complete live `GspFwWprMeta` object and its GSP sysmem buffers. DXE
does not own those inputs. Guessing them or starting a second partial GSP can
damage WPR state or hang the card. A locked FECS therefore reports
`booter-precondition-missing` and performs no FECS write.

This is the key feasibility boundary. ReBAR and Gen2 are feasible in pure DXE.
The full compute result is conditional on FECS still being unlocked, and Windows
may reset the state after ExitBootServices. If Windows 610.88 restores FECS PLM
or link policy, a pure UEFI driver cannot keep the Linux result; that case needs
a Windows kernel-side change or a fully proved firmware handoff, not more blind
UEFI register writes.

Build, one-shot test, recovery, and Shell command instructions are in
`ReBarUEFI/Cmp50Pkg/README.md`. RT core count 56 is intentionally outside this
package. The first read-only F54 image and its extraction proof are in
`artifacts/cmp50-uefi-f54-20260819/`.
