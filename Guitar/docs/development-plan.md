# Guitar Auto-Tuner — Architecture and Development Plan

ESP32-S3 / ESP-IDF project for an automatic guitar tuner using a microphone,
a piezoelectric contact sensor, and a stepper motor.

## Assessment of the current test

- `main/mi_proyecto.c` is a good FFT smoke test, but it is not a viable tuner
  core yet. At 16 kHz / 1024 points, each bin is 15.6 Hz. At low E (82.41 Hz)
  that is roughly **300 cents per bin**, and even with interpolation it will
  not reach ±1–3 cents.
- The Hann window is generated but never applied, and there is no DC removal,
  overlap, RMS gate, confidence metric, or handling of weak/missing
  fundamentals.
- A guitar's strongest FFT peak is often a harmonic, not the fundamental, so
  "largest magnitude bin" will jump octaves. Keep this program as a
  bench/example, not the production path.

## Recommended project structure

Use ESP-IDF components now; retrofitting them later is painful. Keep pure
logic (`pitch`, `music`) free of IDF dependencies so it can be unit-tested on
the host.

```text
guitarTuner_ESP32/
├── CMakeLists.txt                  # project(guitar_tuner)
├── sdkconfig.defaults              # target, CPU 240 MHz, FreeRTOS 1 kHz, DSP size
├── main/
│   ├── main.c                      # app_main(): board/NVS init -> tuner_app_start()
│   └── CMakeLists.txt
├── components/
│   ├── board/                      # single pin map, board_init(), e-stop/limits
│   │   ├── include/board.h
│   │   └── board.c
│   ├── audio/                      # source abstraction + I2S mic + piezo ADC
│   │   ├── include/audio.h
│   │   ├── audio_i2s.c
│   │   ├── audio_piezo.c
│   │   └── audio_synth.c           # sine/WAV source for tests without hardware
│   ├── pitch/                      # pure C: YIN/MPM + optional FFT spectrum
│   │   ├── include/pitch.h
│   │   ├── pitch_yin.c
│   │   └── test/
│   ├── music/                      # pure C: note table, target Hz, cents, string map
│   ├── actuator/                   # stepper: move/home/stop, limits, e-stop
│   ├── storage/                    # NVS calibration per string
│   ├── tuner/                      # FSM + closed-loop tuning controller
│   ├── ui/                         # LED/button/display
│   └── console/                    # esp_console dev commands
└── test/                           # pytest-embedded integration tests
```

Keep `main` tiny: initialize NVS/board, start tasks, return. Each component
exposes a small `esp_err_t` API in `include/`, uses opaque structs/config
structs, and logs with its own `TAG`.

## Runtime architecture

```text
I2S mic ──┐
piezo ────┼─► audio task ─► ring buffer ─► pitch task ─► latest estimate ─► tuner FSM ─► cmd queue ─► motor task
synth ────┘                                  (DSP)          queue          (control)                  (RMT)
                                                                                │
                                                                          status/events ─► UI / console
```

Suggested tasks:

| Task | Priority | Blocks on | Responsibility |
|---|---:|---|---|
| audio | 10 | I2S DMA | read frames, DC block, RMS |
| pitch | 8 | ring buffer | estimate Hz + confidence, median filter |
| actuator | 7 | command queue | step pulses, ramps, homing, abort |
| tuner | 5 | queues/timers | state machine, decision logic |
| ui/console | 2 | events/REPL | status, string selection, manual commands |

Use `xQueueOverwrite` for the latest pitch estimate and a normal queue for
motor commands. Avoid polling loops. Pin audio/DSP to core 1 and control/UI to
core 0 if needed.

## DSP plan

1. I2S microphone at **16 kHz, 32-bit slots, mono** (INMP441/ICS-43434),
   4–8 DMA buffers. Apply a DC blocker and an RMS gate.
2. Analyze **2048-sample frames with 50% overlap** (128 ms window, 64 ms hop).
   At low E that is ~10 periods, enough for periodicity methods.
3. Use **YIN or McLeod (MPM) pitch detection** with parabolic interpolation,
   not raw FFT peak picking. Search roughly **60–500 Hz**. Return
   `{hz, confidence, rms}`.
4. Median-filter 3–5 estimates, reject jumps > ~50 cents, and require a
   confidence threshold for at least 2–3 consecutive frames.
5. Keep FFT available for spectrum/harmonic checks and debugging (Hann window,
   log-magnitude parabolic interpolation). It is useful as a sanity check but
   should not be the sole pitch estimator.
6. Validate offline against synthetic sines (with harmonics/noise) and
   recordings of all six strings. Target **< 1 cent error at ≥ 20 dB SNR**
   before touching the motor.

An FFT of 2048 at 16 kHz still has 7.8 Hz bins (~160 cents at E2), so
zero-padding is not a solution; it only interpolates the display.
YIN/autocorrelation is the right tool here.

## Music/note layer

- Standard tuning: E2 82.407, A2 110.000, D3 146.832, G3 195.998,
  B3 246.942, E4 329.628 Hz.
- `cents = 1200 * log2(f / f_target)`.
- Require **explicit string selection** (button/console/app). Auto-selecting
  the nearest note makes the motor unsafe and causes wrong-string tuning.
- Reject the measurement if the detected pitch is not plausibly near the
  selected string (for example, more than 2–3 semitones away), or if it looks
  like an octave error.

## Motor and closed-loop tuning

- Abstract the actuator so you can support one motor per string or a carriage
  with string selection later. Design a per-string calibration record in NVS:
  direction sign, steps-per-cent, backlash, min/max travel, target offset.
- Generate step pulses with **RMT, MCPWM, or esp_timer**. Do not use
  `vTaskDelay` per step. Include acceleration ramps, driver enable, and
  microstepping.
- Add homing/limit switches, a travel limit, a total-steps limit, a timeout,
  and an **e-stop input**. Motor current limit is mandatory; a stepper can
  snap a string easily.
- Tune one string with a discrete closed loop:

```text
measure stable pitch
error_cents = cents(measured, target)
if |error| <= deadband (2-3 cents): done
steps = clamp(K * error / cents_per_step, min_step, max_step)
move; wait for mechanical settle (100-300 ms); measure again
```

- Learn `cents_per_step` online from previous moves, compensate backlash, and
  abort if two consecutive moves do not improve the error (likely
  slipping/stuck). Keep full travel within a conservative per-string limit.
- **Never step the motor while sampling**, and disable the driver during
  measurement if its hold current creates noise. Motor current chopping will
  otherwise dominate the microphone signal.
- Tuning while the string decays is a timing constraint: measure, move
  quickly, settle, re-measure. If you have no automatic plucker, the firmware
  should prompt for a pluck or operate in short bursts.

## Development milestones

| Phase | Deliverable | Acceptance criterion |
|---|---|---|
| 0 | Rename/restructure, pin map, console, LED | Builds and console responds |
| 1 | I2S mic capture, levels, CSV logging | Stable 16 kHz, no clipping, sane RMS |
| 2 | YIN pitch estimator + host tests | < 1 cent error on test vectors, robust to harmonics/noise |
| 3 | Note/cents/string layer | Unit tests cover table and edge cases |
| 4 | Stepper moves, homing, limits, e-stop | Repeatable moves; abort always works |
| 5 | Closed loop on one string | ±3 cents in a bounded number of iterations, no oscillation |
| 6 | All six strings, UI, NVS calibration | End-to-end tune from cold boot |
| 7 | Hardening | Watchdog, brownout, driver fault, 30-minute soak |

## Development workflow

- Build **vertical slices**: audio → pitch → serial output first; then motor
  standalone; only then close the loop.
- Add `esp_console` commands early: `audio level`, `pitch`, `tuner status`,
  `tuner string 4`, `motor move 100`, `motor home`, `tune start`,
  `tune abort`. This will save days of flashing.
- Add an `audio_synth` source so the DSP and tuner FSM can run without the
  microphone. Let tests inject a 110 Hz sine or a stored WAV.
- Keep `pitch`/`music` pure C and compile them with host CMake + Unity/CTest.
  Use on-target pytest-embedded only for integration/hardware behavior.
- In `sdkconfig.defaults`, set `CONFIG_FREERTOS_HZ=1000`,
  `CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ_240`,
  `CONFIG_COMPILER_OPTIMIZATION_PERF`, stack sizes, and
  `CONFIG_DSP_MAX_FFT_SIZE_4096` if you keep FFT. Commit
  `sdkconfig.defaults` and `dependencies.lock`; keep ignoring `sdkconfig`,
  `build/`, and `managed_components/`.
- Put a **piezo conditioning circuit** on the schematic before writing the
  driver: high-impedance buffer/charge amp, bias to mid-rail, clamp, and a
  low-pass around 7 kHz if sampling at 16 kHz. The ESP32-S3 ADC is convenient
  but noisy; an external I2S ADC is worth considering.
- No motor driver shares the ESP32 5 V rail. Use a separate motor supply,
  common ground, bulk capacitance, and shielded/separated motor wiring to
  avoid brownouts and microphone noise.

## Questions that affect the design

1. How does one motor reach six pegs: one motor per string, or a motorized
   carriage that selects pegs? This determines the actuator API and homing
   strategy.
2. Which microphone, piezo conditioning circuit, and motor driver
   (A4988/DRV8825/TMC2209) are you using?
3. Do you pluck manually, or is there a plucker actuator?
4. What UI do you want: LEDs only, OLED, phone/BLE?
