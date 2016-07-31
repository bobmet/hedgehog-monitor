from tsl2561 import TSL2561


class TSLSensor:
    def __init__(self, led_gpio_pin=None):
        self.sensor = TSL2561(debug=1)

        self.led_gpio_pin = led_gpio_pin

#        if self.led_gpio_pin is not None:
#            GPIO.setup(self.led_gpio_pin, GPIO.OUT)

    def get_data(self):
#        GPIO.output(self.led_gpio_pin, 1)
        lux = self.sensor.lux()
#        GPIO.output(self.led_gpio_pin, 0)
        return lux
