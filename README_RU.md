# CMP50 Unlock (с поддержкой Multi-GPU)

[English version](README.md) | [Пошаговое руководство (AGENT_INSTALL_RU.md)](AGENT_INSTALL_RU.md) | [Страница Готовых Драйверов (Releases)](https://github.com/alexxttss/cmp50-unlock/releases/tag/v610.43.03-multigpu) | [Оригинальный проект](https://github.com/xrip/cmp50hx-unlock)

Обновленный репозиторий исследований и патчей открытых модулей ядра NVIDIA для видеокарт **NVIDIA CMP 50HX**. Оригинальное исследование и патчи созданы разработчиком **[xrip](https://github.com/xrip)** в **[xrip/cmp50hx-unlock](https://github.com/xrip/cmp50hx-unlock)**.

Данная версия содержит важное исправление для **Multi-GPU систем и ригов из нескольких карт** (например, материнские платы Intel X79 / X99 с 2+ картами CMP 50HX в слотах PCIe x16), исправляющее динамическую ошибку выделения WPR2-памяти второй и последующих карт (`REFWSEC_STATE_MISMATCH`).

---

## Быстрая установка готовых драйверов (без компиляции)

Если вы используете **Ubuntu 24.04** с ядром **Linux 6.8.x** и драйвером NVIDIA 610.43.03, вы можете установить уже собранные и протестированные модули ядра в 1 клик:

```bash
# 1. Скачать готовый архив драйверов из Релиза
wget https://github.com/alexxttss/cmp50-unlock/releases/download/v610.43.03-multigpu/cmp50-unlock-prebuilt-610.43.03-ubuntu24.04-kernel6.8.tar.gz

# 2. Распаковать в директорию обновлений модулей ядра
sudo mkdir -p /lib/modules/$(uname -r)/updates/cmp50-unlock
sudo tar -xzvf cmp50-unlock-prebuilt-610.43.03-ubuntu24.04-kernel6.8.tar.gz -C /lib/modules/$(uname -r)/updates/cmp50-unlock/

# 3. Обновить зависимости модулей и образ загрузки initramfs
sudo depmod -a $(uname -r)
sudo update-initramfs -u -k $(uname -r)

# 4. Перезагрузить сервер
sudo reboot
```

После перезагрузки проверьте статус обеих карт:
```bash
nvidia-smi -L
nvidia-smi
```

---

## Технические характеристики патча

| Поле | Значение |
| --- | --- |
| GPU | NVIDIA CMP 50HX / TU102 |
| PCI vendor/device | `10de:1e09` |
| Субсистема NVIDIA | `10de:1554` |
| Субсистема MSI | `1462:371f` |
| Исходники драйвера | NVIDIA open-gpu-kernel-modules `610.43.03` |

### Состав патчей

1. `01-cmp50-stockflow.patch` — разблокировка темпа SM-ядер, GSP/RM stockflow и **динамическая поддержка Multi-GPU**.
2. `02-cmp50-rt-core-count.patch` — отчёт о 56 RT-ядрах на стороне host/RM.
3. `03-cmp50-rebar.patch` — настройка Resizable BAR под CMP50.
4. `04-cmp50-pcie-gen2.patch` — переобучение PCIe endpoint и upstream bridge на скорость Gen2/Gen3.

---

## Сборка из исходников на своем сервере

```bash
# Клонировать репозиторий
git clone https://github.com/alexxttss/cmp50-unlock.git
cd cmp50-unlock

# Запустить скрипт сборки (автоматически скачивает 610.43.03, проверяет SHA256 и накладывает патчи)
bash ./build.sh

# Установить собранные модули
kernel_release="$(uname -r)"
sudo mkdir -p "/lib/modules/${kernel_release}/updates/cmp50-unlock"
sudo cp -a artifacts/610.43.03-${kernel_release}/*.ko "/lib/modules/${kernel_release}/updates/cmp50-unlock/"
sudo depmod -a "${kernel_release}"
sudo update-initramfs -u -k "${kernel_release}"
sudo reboot
```

---

## Оптимизация для работы с нейросетями (llama.cpp)

Для достижения скорости **500+ токенов/сек на Prompt Processing** и 2-кратного ускорения генерации токенов в `llama.cpp` на CMP 50HX:

Используйте патч эмуляции `DISABLE_DP4A` (PR #24616) при сборке `llama.cpp`:

```bash
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_FLAGS="-DDISABLE_DP4A --fmad=false"
cmake --build build -j --config Release
```

---

## Инструкция по откату (Rollback)

Для удаления разблокированных модулей и возврата к стандартному драйверу NVIDIA:

```bash
sudo rm -rf /lib/modules/$(uname -r)/updates/cmp50-unlock
sudo depmod -a $(uname -r)
sudo update-initramfs -u -k $(uname -r)
sudo reboot
```

---

## Авторство

Исходный проект и автор оригинальных исследований:
- Автор: [xrip](https://github.com/xrip)
- Оригинальный репозиторий: [github.com/xrip/cmp50hx-unlock](https://github.com/xrip/cmp50hx-unlock)
