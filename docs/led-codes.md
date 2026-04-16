# Status LED overview

This page describes **NeoPixel status LED behavior as implemented in the current firmware**. Colors are RGB tuples (not sRGB-accurate on hardware). For the German BLE protocol notes, see [`firmware/readme.md`](../firmware/readme.md) (section 3 there is older prose; prefer this file for LED semantics vs code).

## Hardware and code references

| Topic | Location |
| --- | --- |
| Pin | `board.IO8` — single-pixel devices use **1** LED; **Air Cube** uses **5** pixels on the same pin. |
| Color constants | [`firmware/enums.py`](../firmware/enums.py) — class `Color` |
| Pattern engine | [`firmware/led_controller.py`](../firmware/led_controller.py) — `LedController`, `RepeatMode` |

### `RepeatMode` (patterns passed to `show_led`)

| Mode | Value | Meaning |
| --- | ---: | --- |
| `FOREVER` | 0 | Sets the **default** pattern for that LED index; it loops until replaced. |
| `TIMES` | 1 | One-shot sequence; requires `repeat_times` and `elements` with `color` + `duration` per step. |
| `PERMANENT` | 2 | Solid color; uses top-level `color` (converted internally to a single element). |

---

## Boot and global behavior

### Early boot (`main.py`)

Before the product model is constructed, the first NeoPixel is set to **`Color.YELLOW`** — early startup / config load phase.

### Battery splash (`main.py`)

If a battery monitor is present, after sensors start:

| Condition | Behavior |
| --- | --- |
| State of charge **&lt; 10%** | **Red** flash (~0.2 s), then **off**. |
| SOC **≥ 10%** | Up to three **green** flashes (0.5 s on / 0.5 s off) for crossing thresholds **25%, 50%, 75%** (e.g. two flashes if SOC is between 50% and 75%). |

Then a short pause before the main BLE loop continues.

### Firmware install (OTA / ugm)

While a USB-bundle upgrade is applied:

| Context | LED |
| --- | --- |
| [`firmware/main.py`](../firmware/main.py) (ugm2) | First pixel **`(200, 0, 80)`** — magenta / purple tint during `Ugm.install_update`. |
| [`firmware/code.py`](../firmware/code.py) (legacy ugm path) | Same **`(200, 0, 80)`** on `board.IO8` during install. |

Skipped for **Air Station wifiless** mode when WiFi-driven update checks are disabled.

---

## Air Station

Source: [`firmware/models/air_station.py`](../firmware/models/air_station.py).

### After power-up (until patterns change)

| Pattern | Meaning |
| --- | --- |
| **Blue / red** 0.5 s each, forever | Station is up but **not** in the “happy” API path (WiFi down, RTC not set, or missing lat/lon/height). |

### BLE link (`connection_update`)

| BLE | Pattern |
| --- | --- |
| **Connected** | **Green / off** 0.5 s each, forever. |
| **Not connected** | **Cyan / off** 0.5 s each, forever. |

**Wifiless:** when **not** BLE-connected, `connection_update` does **not** change the LED (so SD/RTC status from `_tick_wifiless` is not overwritten every main-loop iteration). When BLE **is** connected, the same **green / off** pattern as above applies.

### Normal (WiFi API) measurement path

When WiFi is up, `rtc_is_set`, and latitude, longitude, and height are all set:

| State | Pattern |
| --- | --- |
| Preconditions OK | **Solid `GREEN_LOW`** while the transmit path is active. |
| Preconditions fail | **Blue / red** 0.5 s alternating (same as startup “blocked” look). |

### Wifiless mode (`WIFILESS_MODE` + Air Station model)

| Condition | Pattern |
| --- | --- |
| SD log write OK and RTC set | **Solid `GREEN_LOW`**. |
| SD write OK, RTC **not** set from DS3231 | **Solid yellow** (timestamps may be wrong). |
| SD mount or write fails | **Red / yellow** 0.5 s alternating. |

---

## Air aRound and Air Bike

Both models use [`firmware/models/air_around.py`](../firmware/models/air_around.py) (`AirAround`).

| Situation | Pattern |
| --- | --- |
| **BLE connected** | **Solid `GREEN_LOW`**. |
| **BLE disconnected** | **Solid cyan**. |
| **BLE read** (sensor data and optionally battery) | Short **blue** flash (~0.1 s, one-shot `TIMES`). |

---

## Air Badge

Source: [`firmware/models/air_badge.py`](../firmware/models/air_badge.py).

`AirBadge` does **not** override `connection_update`; the base [`LdProductModel.connection_update`](../firmware/models/ld_product_model.py) is a no-op. **BLE connected / disconnected does not change the status LED** in the current firmware. BLE read commands still update sensor/battery data like other portable models, but without the short blue flash unless added later (Badge does not call `show_led` on read in its `receive_command`).

---

## Air Cube

Source: [`firmware/models/air_cube.py`](../firmware/models/air_cube.py). Five NeoPixels; `LedController` is constructed with `n=5`.

### BLE (`connection_update`)

| BLE | Pattern |
| --- | --- |
| **Connected** | One **green** pulse, **1 s** (`TIMES`, single repeat). |
| **Disconnected** | **Cyan / off** 0.5 s forever. |

### Button (toggles `ble_on`)

| `ble_on` | Effect |
| --- | --- |
| **On** | **Solid blue** on the LED strip (via `show_led` / default pattern for the controller). |
| **Off** | Calls `turn_off_led()` — intended to turn status lighting off (see `LedController` / BLE commands for related hooks). |

### BLE read (sensor / battery)

Short **blue** flash (~0.1 s), same idea as Air aRound.

### Per-pixel sensor strip (indices **1–4** after each measurement)

Values are averaged across sensors contributing that dimension (code prefers **HIGH** quality samples where applicable). Thresholds are **exactly as in code** — not a standardized air-quality index label.

| LED index | Quantity | Thresholds (°C, µg/m³, index, ppm) | Color order (low → high value) |
| ---: | --- | --- | --- |
| **1** | Temperature | **18**, **24** | blue → green → red |
| **2** | PM2.5 | **5**, **15** | green → yellow → red |
| **3** | TVOC | **220**, **1430** | green → yellow → red |
| **4** | CO2 | **800**, **1000**, **1400** | green → yellow → orange → red |

Pixel **0** is not assigned by this measurement block; it may still reflect BLE connection patterns or other state.

---

## Further reading

- **BLE service and commands**: [`firmware/readme.md`](../firmware/readme.md) — section 2 (protocol).
- **USB / CIRCUITPY upgrade manager**: [`docs/ugm.md`](ugm.md).
