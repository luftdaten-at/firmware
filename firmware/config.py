


MAX_SENSOR_ERRORS_BEFORE_REBOOT = 10
NO_SLEEP_MEM=not bool(sleep_memory)
try:
    sleep_memory[SLEEP_MEMORY_ERROR] = 0x00
    sleep_memory[SLEEP_MEMORY_ERROR_SIZE:SLEEP_MEMORY_ERROR_SIZE+2] = bytearray([0x00,0x00])
except Exception as e:
    traceback.print_exception(e.__class__, e, e.__traceback__)
    print("Setting sleep Error: ",e)
    time.sleep(2)
    NO_SLEEP_MEM=True
    pass