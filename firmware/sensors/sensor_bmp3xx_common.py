"""Shared BMP388 / BMP390 probe (same I2C address, distinct CHIP_ID at register 0x00)."""

import adafruit_bmp3xx
from adafruit_bus_device import i2c_device

from logger import logger

REGISTER_CHIP_ID = 0x00
BMP388_CHIP_ID = 0x50
BMP390_CHIP_ID = 0x60
BMP3XX_I2C_ADDRESSES = (0x77, 0x76)


def read_bmp3xx_chip_id(i2c, address):
    """Return CHIP_ID byte from register 0x00, or None on bus error."""
    buf = bytearray(1)
    try:
        with i2c_device.I2CDevice(i2c, address) as device:
            buf[0] = REGISTER_CHIP_ID
            device.write_then_readinto(buf, buf, out_end=1, in_end=1)
        return buf[0]
    except OSError:
        return None


def probe_bmp3xx(i2c):
    """Detect BMP388/BMP390 once; return (chip_id, driver, i2c_address) or None."""
    for address in BMP3XX_I2C_ADDRESSES:
        chip_id = read_bmp3xx_chip_id(i2c, address)
        if chip_id not in (BMP388_CHIP_ID, BMP390_CHIP_ID):
            continue
        try:
            bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c, address=address)
        except Exception as e:
            logger.debug(
                "Bmp3xx init failed at 0x%02x CHIP_ID=0x%02x (%s: %s)"
                % (address, chip_id, type(e).__name__, e)
            )
            continue
        logger.debug(
            "Bmp3xx probe ok at 0x%02x CHIP_ID=0x%02x" % (address, chip_id)
        )
        return chip_id, bmp, address
    return None
