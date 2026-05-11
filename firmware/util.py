import time

from logger import logger
from enums import SensorModel, LdProduct


def _i2c_sensor_classes_ordered():
    """
    (model_id, class) in the same order as the legacy full sensor scan.
    One entry per model id; Sht4x appears once (legacy list had two Sht4x instances).
    """
    from sensors.sensor_sen5x import Sen5xSensor
    from sensors.sensor_bme280 import BME280Sensor
    from sensors.sensor_bme680 import BME680Sensor
    from sensors.sensor_aht20 import AHT20Sensor
    from sensors.sensor_bmp280 import BMP280Sensor
    from sensors.sensor_ags02ma import AGS02MASensor
    from sensors.sensor_scd4x import Scd4xSensor
    from sensors.sensor_sht30 import Sht30Sensor
    from sensors.sensor_sht31 import Sht31Sensor
    from sensors.sensor_sht4x import Sht4xSensor
    from sensors.sensor_sgp40 import Sgp40Sensor
    from sensors.sensor_bmp388 import Bmp388Sensor
    from sensors.sensor_bmp390 import Bmp390Sensor
    from sensors.sensor_ltr390 import Ltr390Sensor
    from sensors.sensor_lsm6ds import Lsm6dsSensor
    from sensors.sensor_mlx90640 import Mlx90640Sensor
    from sensors.sensor_tsl2591 import Tsl2591Sensor

    return [
        (SensorModel.SEN5X, Sen5xSensor),
        (SensorModel.BME280, BME280Sensor),
        (SensorModel.BME680, BME680Sensor),
        (SensorModel.AHT20, AHT20Sensor),
        (SensorModel.BMP280, BMP280Sensor),
        (SensorModel.AGS02MA, AGS02MASensor),
        (SensorModel.SHT30, Sht30Sensor),
        (SensorModel.SHT31, Sht31Sensor),
        (SensorModel.SCD4X, Scd4xSensor),
        (SensorModel.SHT4X, Sht4xSensor),
        (SensorModel.SGP40, Sgp40Sensor),
        (SensorModel.BMP388, Bmp388Sensor),
        (SensorModel.BMP390, Bmp390Sensor),
        (SensorModel.LTR390, Ltr390Sensor),
        (SensorModel.LSM6DS, Lsm6dsSensor),
        (SensorModel.MLX90640, Mlx90640Sensor),
        (SensorModel.TSL2591, Tsl2591Sensor),
    ]


# Unique model ids the firmware can probe on I2C, in default scan order.
SUPPORTED_I2C_MODEL_IDS = tuple(mid for mid, _ in _i2c_sensor_classes_ordered())
_I2C_CLASS_BY_ID = {mid: cls for mid, cls in _i2c_sensor_classes_ordered()}


def get_connected_sensors(i2c, model_ids=None):
    """
    Probe I2C sensor drivers. If model_ids is None, probe all supported I2C types
    in default order. Otherwise only probe those ids (e.g. from sensors.toml);
    id 26 (PS1 UART) is ignored here. Unknown ids are logged and skipped.
    """
    id_to_cls = _I2C_CLASS_BY_ID
    if model_ids is None:
        to_try = [mid for mid, _ in _i2c_sensor_classes_ordered()]
    else:
        to_try = []
        seen = set()
        for mid in model_ids:
            if mid in seen:
                continue
            if mid == SensorModel.PS1_NO2_50_MOD:
                continue
            if mid not in id_to_cls:
                logger.warning(
                    f"Unknown I2C sensor model id in sensors.toml: {mid}; skipping"
                )
                continue
            seen.add(mid)
            to_try.append(mid)

    connected_sensors = {}
    for mid in to_try:
        cls = id_to_cls[mid]
        sensor = cls()
        if sensor.attempt_connection(i2c):
            logger.info(f"Found sensor: {sensor.model_id}")
            connected_sensors[sensor.model_id] = sensor
    return connected_sensors


def get_battery_monitor(i2c):
        # Try to connect to battery sensor, as that is part of criteria
        from sensors.max17048 import MAX17048
        battery_monitor = None
        for i in range(10):
            try:
                battery_monitor = MAX17048(i2c)
                logger.info(f'Attempt {i + 1}: Battery monitor initialized')
                break
            except:
                pass
            logger.info("Waiting 0.5 seconds before retrying battery monitor initialization")
            time.sleep(0.5)
        
        return battery_monitor


def get_model_id_from_sensors(connected_sensors: dict, battery_monitor) -> int:
        # Find correct model
        device_model = -1
        if connected_sensors.get(SensorModel.SCD4X, None):
            device_model = LdProduct.AIR_CUBE
        elif battery_monitor is None:
            device_model = LdProduct.AIR_STATION
        elif not connected_sensors.get(SensorModel.SEN5X, None):
            device_model = LdProduct.AIR_BADGE
        else:
            device_model = LdProduct.AIR_AROUND
        
        return device_model
