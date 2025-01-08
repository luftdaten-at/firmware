from sensors.sensor import Sensor
from enums import SensorModel, Dimension


class VirtualSensor(Sensor):
    def __init__(self, required_sensor_dict: dict[SensorModel, Sensor], calculated_dimension_set: set[Dimension]) -> None:
        '''
        sensors: list of sensors requierd to calculate requested dimensions
        dimensions: dimensions that should be calculated
        '''
        super().__init__()

        self.model_id = SensorModel.VIRTUAL_SENSOR
        self.required_sensor_dict = required_sensor_dict
        self.calculated_dimension_set = calculated_dimension_set        
        self.current_values: dict[Dimension, float] = {}

    def read(self) -> None:
        '''
        recalculate all current_values
        '''

        # update all sensors
        for sen in self.required_sensor_dict.values():
            sen.read()
        
        def mean(l: list):
            return sum(l) / len(l)

        if Dimension.ADJUSTED_TEMP_CUBE in self.calculated_dimension_set:
            # check if we have all required sensor
            # this is the case if required_sensors ⊆ sensors_that_we_have
            need = Dimension.get_required_sensors(Dimension.ADJUSTED_TEMP_CUBE)
            if need <= set(self.required_sensor_dict.keys()):
                # by default return the mean tempreature
                self.current_values[Dimension.ADJUSTED_TEMP_CUBE] = mean([ 
                    sen.current_values[Dimension.TEMPERATURE]
                    for model_id, sen in self.required_sensor_dict.items()
                        if model_id in need
                ])
            else:
                # set value to None indication that we haven't found all sensors
                self.current_values[Dimension.ADJUSTED_TEMP_CUBE] = None
