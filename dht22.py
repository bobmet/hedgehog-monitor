import Adafruit_DHT
import RPi.GPIO as GPIO

class DHT22():
    def __init__(self, data_gpio_pin, led_gpio_pin=None):
        self.sensor = Adafruit_DHT.DHT22
        self.data_gpio_pin = data_gpio_pin
        self.led_gpio_pin = led_gpio_pin

        if self.led_gpio_pin is not None:
            GPIO.setup(self.led_gpio_pin, GPIO.OUT)

    def get_data(self):
        GPIO.output(self.led_gpio_pin, 1)
        humidity, temperature = Adafruit_DHT.read_retry(self.sensor, self.data_gpio_pin)
        GPIO.output(self.led_gpio_pin, 0)
        return humidity, temperature
