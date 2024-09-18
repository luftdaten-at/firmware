import time
from enums import BleCommands

class LedController:
    BRIGHTNESS_LEVELS = [1/5, 2/5, 3/5, 4/5, 1]

    def __init__(self, status_led, num_leds):
        self.num_leds = num_leds
        self.status_led = status_led
        self.current_patterns = [None for _ in range(num_leds)]
        self.time_in_patterns = [0 for _ in range(num_leds)]
        self.repetitons_of_current_patterns = [0 for _ in range(num_leds)]
        self.patterns_started_at = [0 for _ in range(num_leds)]
                
    def tick(self):
        for i, pattern in enumerate(self.current_patterns):
            if pattern is None:
                continue
            self.time_in_patterns[i] = (time.monotonic() - self.patterns_started_at[i])
            if pattern['repeat_mode'] == RepeatMode.FOREVER or pattern['repeat_mode'] == RepeatMode.TIMES:
                total_duration = sum(item['duration'] for item in pattern['elements'])
                while self.time_in_patterns[i] >= total_duration:
                    self.time_in_patterns[i] -= total_duration
                    if pattern['repeat_mode'] == RepeatMode.TIMES:
                        if self.repetitons_of_current_patterns[i] == pattern['repeat_times']:
                            self.current_patterns[i] = None
                            self.turn_off_led()
                            continue
                        self.repetitons_of_current_patterns[i] += 1
                t = 0
                for item in pattern['elements']:
                    t += item['duration']
                    if self.time_in_patterns[i] < t:
                        self._show_led(item['color'])
                        break
            elif pattern['repeat_mode'] == RepeatMode.PERMANENT:
                pass # Led would already have been set in show_led
    
    def show_led(self, pattern, led_id = 0):
        # LED ID -1 is for setting all LEDs
        if led_id == -1:
            for i in range(self.num_leds):
                self.show_led(pattern, i)
            return
        print('Set LED', led_id, 'to pattern:', pattern)
        if pattern == self.current_patterns[led_id]:
            print('Pattern already set')
            return
        self.patterns_started_at[led_id] = time.monotonic()
        self.current_patterns[led_id] = pattern
        self.time_in_patterns[led_id] = 0
        self.repetitons_of_current_patterns[led_id] = 0
        if pattern['repeat_mode'] == RepeatMode.PERMANENT:
            self._show_led(pattern['color'], led_id=led_id)
            
    def turn_off_led(self, led_id = 0):
        self.current_patterns[led_id] = None
        self._show_led((0, 0, 0), led_id=led_id)
            
    def _show_led(self, color, led_id = 0):
        if led_id == -1:
            self.status_led.fill(color)
        else:
            self.status_led[led_id] = color
        self.status_led.show()
    
    def receive_command(self, command):
        if not command:
            return
        cmd = command[0]
        if cmd == BleCommands.UPDATE_BRIGHTNESS:
            level = command[1]
            self.status_led.brightness = LedController.BRIGHTNESS_LEVELS[level]
    
class RepeatMode:
    FOREVER = 0
    TIMES = 1
    PERMANENT = 2