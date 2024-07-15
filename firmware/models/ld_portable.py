from models.ld_product_model import LdProductModel
from led_controller import RepeatMode
from enums import Color

class LdPortable(LdProductModel): 
    def __init__(self, model, ble_service, sensors, battery_monitor, status_led):
        super().__init__(ble_service, sensors, battery_monitor, status_led)
        self.polling_interval = 0.01
        self.model_id = model
        self.ble_on = True
        
    def receive_command(self, command):
        if(len(command) == 0):
            return
        cmd = command[0]
        if cmd == 0x01 or cmd == 0x02:
            self.update_ble_sensor_data()
            print("Sensor values updated")
            self.status_led.show_led({
                'repeat_mode': RepeatMode.TIMES,
                'repeat_times': 1,
                'elements': [
                    {'color': Color.BLUE, 'duration': 0.1},
                ],
            })
        if cmd == 0x02:
            self.update_ble_battery_status()
            print("Battery status updated")
    
    def receive_button_press(self):
        pass
    
    def tick(self):
        pass

    def connection_update(self, connected):
        if connected:
            self.status_led.show_led({
                'repeat_mode': RepeatMode.TIMES,
                'repeat_times': 1,
                'elements': [
                    {'color': Color.GREEN, 'duration': 1},
                ],
            })
        else:
            self.status_led.show_led({
                'repeat_mode': RepeatMode.FOREVER,
                'elements': [
                    {'color': Color.CYAN, 'duration': 0.5},
                    {'color': Color.OFF, 'duration': 0.5},
                ],
            })