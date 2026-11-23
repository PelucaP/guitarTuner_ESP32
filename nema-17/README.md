# NEMA 17 + DRV8825 + ESP32-WROOM-32 (ESP-IDF)

Plain ESP-IDF project (no PlatformIO) that spins a NEMA 17 through a DRV8825
STEP/DIR driver.

## Wiring

| ESP32-WROOM-32 | DRV8825 module | Notes |
|----------------|----------------|-------|
| GPIO18 | STEP | driven by the RMT peripheral |
| GPIO19 | DIR | set before every move |
| GND | GND | **must be common with the motor supply** |
| (optional) any free GPIO | nENBL | add it as `.en_gpio`, otherwise tie nENBL to GND |
| (optional) 3 GPIOs | M0 / M1 / M2 | only needed if you want to change microstepping at runtime |

VMOT = 8.2–45 V motor supply, with a 100 µF electrolytic close to the module.
Logic VDD of the module: 3.3 V is in spec (2.5–5.25 V). Check that the module's
**nSLEEP (SLP) and nRESET (RST) are high** — a floating SLP keeps the chip
asleep and the motor only buzzes.

## Before the first run

Set the current limit (Vref trimpot on the module) for your motor. On the common
boards (0.1 Ω sense resistors) `I_limit ≈ 2 × Vref`, so a 1.5 A motor needs
Vref ≈ 0.75 V. **Never unplug the motor while VMOT is on** — that destroys the
driver.

Microstepping (DRV8825 datasheet, "Microstepping Setting"):

| M2 | M1 | M0 | step |
|----|----|----|------|
| 0 | 0 | 0 | full |
| 0 | 0 | 1 | 1/2 |
| 0 | 1 | 0 | 1/4 |
| 0 | 1 | 1 | 1/8 |
| 1 | 0 | 0 | 1/16 |
| 1 | 0 | 1 | 1/32 |

A 1.8° NEMA 17 has 200 full steps/rev, so 1/16 => 3200 microsteps/rev
(`drv8825_steps_per_rev()`).

## Build / flash

```bash
. ~/esp/esp-idf/export.sh
idf.py set-target esp32      # sdkconfig.defaults already pins the target
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

## Usage

```c
static drv8825_t motor;

const drv8825_config_t cfg = {
    .step_gpio = GPIO_NUM_18,
    .dir_gpio  = GPIO_NUM_19,
    .en_gpio   = GPIO_NUM_NC,
    .m0_gpio = GPIO_NUM_NC, .m1_gpio = GPIO_NUM_NC, .m2_gpio = GPIO_NUM_NC,
    .microstep = DRV8825_MICROSTEP_1_16,
    .dir_cw_level = 0,
    .speed_hz = 2000,        /* microsteps per second */
    .accel_steps = 400,      /* ramp length at each end of a move */
};
ESP_ERROR_CHECK(drv8825_init(&motor, &cfg));
ESP_ERROR_CHECK(drv8825_move(&motor, 3200));   /* one rev clockwise, blocking */
ESP_ERROR_CHECK(drv8825_move(&motor, -3200));  /* one rev back */
```

`speed_hz` and `accel_steps` are baked into the ramp tables by `drv8825_init()`;
changing them needs `drv8825_deinit()` followed by `drv8825_init()` (`drv8825_init()`
does not free the previous channel). Moves shorter than `2 × accel_steps` run at
constant speed. `speed_hz` must be between 160 and 100000: below 160 Hz the ramp
start frequency no longer fits in the 15-bit RMT duration field.

## Files

- `main/drv8825.c/.h` — the driver: GPIO setup, RMT channel, accel/cruise/decel
  move, microstep pin control.
- `main/stepper_motor_encoder.c/.h` — Espressif's stepper curve encoder, copied
  from `esp-idf/examples/peripherals/rmt/stepper_motor` (Apache-2.0). Only the
  curve encoder is kept; the example's unused uniform-speed encoder was removed.

## Why not the code from esp32io.com / the ESP-IDF example?

Both use `rmt_transmit_config_t.loop_count` for the constant-speed phase. The
original ESP32 has no RMT TX loop-count hardware, so `rmt_transmit()` rejects
`loop_count > 1` with `ESP_ERR_NOT_SUPPORTED`
(`components/soc/esp32/include/soc/soc_caps.h`, `rmt_tx.c:525`); the example only
works on newer chips. This driver uses a small local encoder that emits one
symbol per step, so it works on ESP32 with no loop-count support.
