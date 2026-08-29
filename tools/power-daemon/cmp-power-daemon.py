#!/usr/bin/env python3
import ctypes
import time
import signal
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Load NVML
try:
    nvml = ctypes.CDLL("libnvidia-ml.so.1")
except Exception as e:
    logging.error(f"Failed to load libnvidia-ml.so.1: {e}")
    sys.exit(1)

class nvmlUtilization_t(ctypes.Structure):
    _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]

assert nvml.nvmlInit_v2() == 0, "nvmlInit failed"

gpu_count = ctypes.c_uint()
nvml.nvmlDeviceGetCount_v2(ctypes.byref(gpu_count))
num_gpus = gpu_count.value
logging.info(f"Found {num_gpus} NVIDIA GPUs")

handles = []
for i in range(num_gpus):
    h = ctypes.c_void_p()
    nvml.nvmlDeviceGetHandleByIndex_v2(i, ctypes.byref(h))
    handles.append(h)

def cleanup(signum=None, frame=None):
    logging.info("Shutting down cmp-power-daemon, resetting GPU clocks...")
    for i, h in enumerate(handles):
        try:
            nvml.nvmlDeviceResetGpuLockedClocks(h)
        except Exception:
            pass
    try:
        nvml.nvmlShutdown()
    except Exception:
        pass
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

IDLE_THRESHOLD_SECONDS = 1.0
CHECK_INTERVAL_SECONDS = 0.1
SAMPLES_BEFORE_IDLE = int(IDLE_THRESHOLD_SECONDS / CHECK_INTERVAL_SECONDS)

# State per GPU: is_locked, idle_samples
gpu_states = [{"is_locked": False, "idle_samples": 0} for _ in range(num_gpus)]

logging.info(f"Starting power management loop (idle threshold: {IDLE_THRESHOLD_SECONDS}s, check: {CHECK_INTERVAL_SECONDS}s)...")

util = nvmlUtilization_t()

try:
    while True:
        for i, h in enumerate(handles):
            res = nvml.nvmlDeviceGetUtilizationRates(h, ctypes.byref(util))
            if res != 0:
                continue
            
            gpu_util = util.gpu
            state = gpu_states[i]

            if gpu_util == 0:
                state["idle_samples"] += 1
                if state["idle_samples"] >= SAMPLES_BEFORE_IDLE and not state["is_locked"]:
                    # Enter low power idle mode
                    lock_res = nvml.nvmlDeviceSetGpuLockedClocks(h, ctypes.c_uint(300), ctypes.c_uint(300))
                    if lock_res == 0:
                        state["is_locked"] = True
                        logging.info(f"GPU {i}: Idle detected -> Clocks locked to 300 MHz (Power Saving)")
            else:
                state["idle_samples"] = 0
                if state["is_locked"]:
                    # Wake up to full performance immediately
                    reset_res = nvml.nvmlDeviceResetGpuLockedClocks(h)
                    if reset_res == 0:
                        state["is_locked"] = False
                        logging.info(f"GPU {i}: Activity detected (util={gpu_util}%) -> Clocks unlocked to BOOST")

        time.sleep(CHECK_INTERVAL_SECONDS)
except Exception as e:
    logging.error(f"Error in main loop: {e}")
finally:
    cleanup()
