# 1. Installieren

## 1 - CircuitPython-Version herunterladen

Download-Link: https://circuitpython.org/board/espressif_esp32s3_devkitc_1_n8r8/

Für BLE auf dem ESP32-S3 wird mindestens CircuitPython 9.1.0 benötigt. Durch einen Bug in Circuitpython kann aktuell nur <= 9.1.0 oder >= 9.2.0 genutzt werden. Lade die `.bin`-Datei herunter.

## 2 - CircuitPython auf dem ESP32-S3 installieren

Verbinde Mac und ESP32 per USB C. Installiere, falls noch nicht vorhanden, esptool.py:

```bash
pip3 install esptool
```

Find den Port des ESP32:

```bash
ls /dev/tty.*
```

Der ESP32 sollte als USB-Gerät angezeigt werden, z.B. `/dev/tty.usbmodem101`.

Lösche den Flash-Speicher des ESP32:

```bash
esptool.py --port /dev/tty.usbmodem101 erase_flash
```

Flashe CircuitPython auf den ESP32:

```bash
esptool.py --port /dev/tty.usbmodem101 write_flash -z 0x0 circuitpython.bin
```

wobei `circuitpython.bin` der Pfad zur heruntergeladenen CircuitPython-Datei ist.

## 3 - CircuitPython-Bibliotheken installieren

Nach einem eventuellen Neustart des ESP32 sollte ein neues Laufwerk namens `CIRCUITPY` erscheinen. Kopiere den Inhalt dieses Ordners ohne diese Datei und `.gitignore` in den Ordner. Installiere, falls notwendig, `circup` auf dem Mac:

```bash
pip3 install circup
circup bundle-add good-enough-technology/circuitpython_goodenough_bundle
```

Führe nun Circup aus, um die benötigten Bibliotheken zu installieren:

```bash
circup install --auto
```

Drücke den Reset-Knopf am ESP32, um die Installation abzuschließen.

## 4 - Gerät konfigurieren

Öffne die `settings.toml`-Datei im `CIRCUITPY`-Laufwerk und passe die Konfiguration an. Momentan ist es nur möglich, den Gerätetypen zu ändern. Setze dafür die Variable `model` auf `1` für Air aRound, `2` für Cube, `3` für Station und `4` für Badge (vgl. Konstanten in `modules/enums.py`).

| ID | Modelname |
| --- | --- |
| -1 | Autoerkennung beim nächsten Start |
| 1 | Air aRound |
| 2 | Air Cube |
| 3 | Air Station |
| 4 | Air Badge |
| 5 | Air Bike |


## 5 - Gerät initialisieren

Starte das Gerät neu, während du den Button gedrückt hältst. Passe dabei auf, den Button über das Ende der türkisen LED-Phase hinaus gedrückt zu halten. Die LED zeigt nun Violett an und initialisiert sich. Achtung: Während der Initialisierung darf das Gerät nicht über USB verbunden sein.


# 2. BLE-Protokoll (v2)

## Service

UUID: `0931b4b5-2917-4a8d-9e72-23103c09ac29`


### Befehle / Auslesen neuer Sensordaten anfragen (neu in v2)

Characteristic UUID: `030ff8b1-1e45-4ae6-bf36-3bca4c38cdba` (write)

Schreibe `0x01` um neue Sensordaten auszulesen.
Schreibe `0x02` um neue Sensordaten auszulesen und den Batteriestatus zu aktualisieren.
Weitere Befehle hängen von Modell ab (siehe unten).

Byte | Action
--- | ---
READ_SENSOR_DATA | 0x01
READ_SENSOR_DATA_AND_BATTERY_STATUS | 0x02
UPDATE_BRIGHTNESS | 0x03
TURN_OFF_STATUS_LIGHT | 0x04
TURN_ON_STATUS_LIGHT | 0x05
SET_AIR_STATION_CONFIGURATION | 0x06

### SET_AIR_STATION_CONFIGURATION Byte Structure Overview

### Packet Breakdown

- **Command Byte**: `0x06` - This byte indicates the start of the configuration command.
- **Flag Byte**: A bitwise combination of flags indicating the specific configurations to be set. Each bit represents a different configuration option.
- **Length Byte**: Indicates the number of bytes that follow the flag for the specific configuration being set.
- **Data Bytes**: Actual configuration data corresponding to the flags set.

## Flags

The following flags are used to indicate which configurations can be set:

| Flag Bit | Configuration            | Description                               |
|----------|--------------------------|-------------------------------------------|
| 0        | AUTO_UPDATE_MODE         | Enable or disable automatic updates.      |
| 1        | BATTERY_SAVE_MODE        | Enable or disable battery-saving mode.    |
| 2        | MEASUREMENT_INTERVAL     | Set the interval for measurements.        |
| 3        | LONGITUDE                | Set the longitude (string value).         |
| 4        | LATITUDE                 | Set the latitude (string value).          |
| 5        | HEIGHT                   | Set the height (string value).            |
| 6        | SSID                     | Set the SSID (string value).              |
| 7        | PASSWORD                 | Set the password (string value).          |
| 8        | DEVICE_ID                | String: {Chip Name}-{MAC}-{ManufactureID} |

## Data Types

- **Integer Values**: Represented as a 4-byte integer in big-endian format (e.g., for measurement intervals).
- **Strings**: Represented as UTF-8 encoded byte arrays for SSID and password.

### Sensordaten auslesen (gleich wie v1)

Characteristic UUID: `4b439140-73cb-4776-b1f2-8f3711b3bb4f`

Format: `[SENSOR A][SENSOR B]...`

Wert, bevor erste Daten ausgelesen wurden: `0x00`

Für jeden Sensor:

| Byte | Inhalt |
|---|---|
| 0 | Sensor-ID |
| 1 | Anzahl Messdimensionen |
| >2 | Messdaten |

Für jede Messdimension:

| Byte | Inhalt |
|---|---|
| 0 | Messdimensions-ID |
| 1 | High byte von (Messwert * 10, gerundet) |
| 2 | Low byte von (Messwert * 10, gerundet) |

Achtung: wenn keine Werte vorhanden sind (sollte eigentlich nicht vorkommen), sende `0x00` für beide Bytes.

Aktuell unterstützte Messdimensionen:

| ID | Messdimension |
|---|---|
| 1 | PM0.1 |
| 2 | PM1.0 |
| 3 | PM2.5 |
| 4 | PM4.0 |
| 5 | PM10.0 |
| 6 | Luftfeuchtigkeit |
| 7 | Temperatur |
| 8 | VOC-Index |
| 9 | NOx-Index |
| 10 | Luftdruck |
| 11 | CO2 |
| 12 | O3 |
| 13 | AQI |
| 14 | Gaswiderstand (für Bosch AQI) |
| 15 | VOC (absolut) |
| 16 | NO2 |

Aktuell unterstützte Sensor-IDs:

| ID | Sensor | Messdimensionen |
|---|---|---|
| 1 | Sen5x | PM1, PM2.5, PM4, PM10, Temp, Hum, VOC-Index, NOX-Index |
| 2 | BMP280 | Temp, Druck |
| 3 | BME280 | Temp, Druck, Hum |
| 3 | BME680 | Temp, Druck |
| 4 | SCD4x | Temp, Hum, CO2 |
| 5 | AHT20 | Temp, Hum |
| 6 | SHT30 | Temp, Hum |
| 7 | SHT31 | Temp, Hum |
| 8 | AGS02MA | VOCs (absolut), Gaswiderstand |
| 9 | SHT4X | Temp, Hum |


### Luftdaten-Gerät-Details auslesen (geändert in v2)

UUID: `8d473240-13cb-1776-b1f2-823711b3ffff`

| Byte | Inhalt | Wert |
|---|---|---|
| 0 | Protokoll-Version | 2 |
| 1 | Firmware Major Version |  |
| 2 | Firmware Minor Version |  |
| 3 | Firmware Patch Version |  |
_Sollten hier noch andere Gerätedetails (Name, Projekt) ausgelesen werden? z.B.:_
| Byte | Inhalt | Wert |
|---|---|---|
| 4-7 | Gerätename (ASCII) | Wenn unbekannt: 0x00 0x00 0x00 0x00 | (Serverseitig noch nicht implementiert, momentan immer 0000)
| 8 | Modell-ID (Air aRound = 1, Cube = 2, Station = 3) |  |
_Status der einzelnen erkannten Sensoren_
| Byte | Inhalt | Wert |
|---|---|---|
| 9 | Anzahl konfigurierter Sensoren |  |
| 10 | Sensor 0: Sensor-ID |  |
| 11 | Sensor 0: Status | Nicht gefunden: 0x00, Gefunden: 0x01 |
_... weitere Sensoren_

### Gerätstatus auslesen (neu in v2)

UUID: `77db81d9-9773-49b4-aa17-16a2f93e95f2`

| Byte | Inhalt | Wert |
|---|---|---|
| 0 | Hat Batteriestatus | 0: nein, 1: ja |
| 1 | Batterieladestatus (in %) |  |
| 2 | Betriebsspannung (in 0.1V) |  |
| 3 | Fehlerstatus | 0: OK, ≠0: Fehler |
_Weitere Werte hängen von Gerätemodell ab (siehe unten)_

Fehlercodes:
_Hängen von Gerätemodell ab (siehe unten)_

### Sensordetails auslesen (geändert in v2)

UUID: `13fa8751-57af-4597-a0bb-b202f6111ae6`

Wenn keine Sensoren erkannt wurden: sende `0x06`

Wenn Sensoren erkannt wurden: sende `[SENSOR A]0xff[SENSOR B]0xff...` (für nur einen Sensor: `[SENSOR A]0xff`)

Für jeden Sensor:

| Byte | Inhalt |
|---|---|
| 0 | Sensor-ID |
| 1 | Anzahl Messdimensionen |
| 2-x | IDs der Messdimensionen |

Gefolgt von byte 0xff. Dann optional Sensor-Details, wenn von Sensor unterstützt.

#### SEN5x

| Byte | Inhalt | Wert |
|---|---|---|
| 0 | Firmware-Version, major |  |
| 1 | Firmware-Version, minor |  |
| 2 | Hardware-Version, major |  |
| 3 | Hardware-Version, minor |  |
| 4 | Protokoll-Version, major |  |
| 5 | Protokoll-Version, minor |  |
| >6 | Seriennummer, utf8 |  |

#### SHT4x

| Byte | Inhalt | Wert |
|---|---|---|
| 0-3 | Seriennummer (32-bit) |  |

#### SHT4x

| Byte | Inhalt | Wert |
|---|---|---|
| 0-5 | Seriennummer (6 bytes) |  |


# 3. LED-Farbcodes

| Farbe | Bedeutung |
|---|---|
| Türkis | Gerät wird gestartet |
| Blau | Gerät startet im normalen Modus |
| Grün | Gerät ist betriebsbereit |
| Violett | Gerät wird initialisiert (u. A. werden verbundene Sensoren gesucht) |
| Orange | Gerät sendet Statusdaten (passiert nach Initialisierung) |
| Rot | Fehler |

## AirStation
| Farbe | Bedeutung |
|---|---|
| Rot | Wlan ist nicht verbunden |
| Lila | Es fehlen Konfigurationen um Daten an die API zu senden |

## Fehler-LED-Codes

| Farbe | Muster (Sek an/Sek aus) | Bedeutung | Lösung |
|---|---|---|---|
| Rot | 1/1 | Gerät war bei Initialisierung über USB verbunden | Ausstecken, neu starten |
| Rot/Orange | 1/1 | Ungültige Modell-ID | Neu initialisieren oder `settings.toml` manuell bearbeiten |


# 4. Befehle und Statusdetails nach Gerätemodell

## Air aRound, Air Badge
_Keine Änderungen gegenüber oben definiertem Standard._

## Air Station
### Fehlercodes
- 0x01: Wifi-SSID oder -Passwort nicht gesetzt
- 0x02: Netzwerk mit dieser SSID nicht gefunden
- 0x03: Falsches Passwort / Verbindung fehlgeschlagen
- 0x04: Keine Verbindung zum Internet (pinge z. B. Google)
- 0x05: Keine Verbindung zum Server
- 0x06: Server hat Datenpaket abgelehnt

### Zusätzliche Status-Bytes
| Byte | Inhalt | Wert |
|---|---|---|
| 4 | Wifi-SSID gesetzt | 0: nein, 1: ja |

### Zusätzliche Befehle
- Wifi-SSID und -Passwort setzen: `0x03 [SSID] 0x00 [Passwort] 0x00`
- Messintervall setzten: `0x04 [Intervall in Sekunden]`
- Bluetooth ausschalten: `0x05`
_In Zukunft: z. B. Server-URL, Auto-Update oder Batteriesparmodus setzten._

## Air Cube
_TBD_

# Ugm Upgrade manager

When changing the following files a save upgrade cannot be garantied, because they are used in the upgrade manager code.


- code.py
- ugm: all files in this folder

packages:
- cptoml
- adafruit_requests
- socketpool
- wifi
- dirTree
