class Sensor:
    def __init__(self):
        self.model_id = None
        """Sensor model."""

        self.measures_values = []
        """List of Dimension values that are measured by this sensor."""
    
        self.current_values = {}
        """Dictionary of current values for each Dimension measured by this sensor.
        If no value has been set yet, use None."""
        
        self.sensor_details = bytes([])
        """Optional descriptors for this sensor, such as serial number or firmware version.
        Can be left empty."""
        
        self.value_quality = {}
        """Dictionary of quality for each Dimension measured by this sensor.
        High quality values will be preferred over Low quality e.g. for Air Cube LEDs."""
    
    def read(self):
        """Read the current values from the sensor and update current_values."""
        raise NotImplementedError()
    
    def on_start_main_loop(self, device):
        """Called just before the main loop is started. Allows sensor to access device state.
        Used by SGP40 to link with SHT3X or SHT4X sensor."""
        pass
    
    # The following methods do not need to be overridden by subclasses.
    def get_device_info(self):
        """Return device information as a byte array.
        For format, see readme.md."""
        arr = bytearray([self.model_id,
                         len(self.measures_values),
                         ])
        arr.extend(self.measures_values)
        arr.append(0xff)
        arr.extend(self.sensor_details)
        arr.append(0xff)
        return arr
    
    def get_current_values(self):
        """Return current values as a byte array.
        For format, see readme.md."""
        arr = bytearray([self.model_id,
                         len(self.current_values),
                         ])
        for dim in self.current_values:
            arr.append(dim)
            if self.current_values[dim] is None or self.current_values[dim] != self.current_values[dim]:
                arr.append(0x00)
                arr.append(0x00)
            else:
                val = round(self.current_values[dim] * 10)
                # Send high byte, then low byte
                arr.append((val >> 8) & 0xff)
                arr.append(val & 0xff)
        return arr
