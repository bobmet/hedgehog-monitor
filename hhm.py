# -*- coding: utf-8 -*-
"""
Created on Thu Jul 14 23:20:03 2016

@author: pi
"""

import Queue
import datetime
import logging
import math
import threading

import RPi.GPIO as GPIO

import dht22
import sensor_handlers
import tsl_sensor
from lcd_display import LCDDisplay
from results_writer import ResultsWriter
from sensor_handlers.button_handler import ButtonHandlerThread
from sensor_handlers.data_collection_thread import DataCollectionThread
from sensor_handlers.lcd_handler import LCDDisplayThread

__version__ = "0.0.9"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger('hh')

# --------- User Settings ---------
# Initial State settings
BUCKET_NAME = ":computer: DHT22 Test" 
BUCKET_KEY = "pi0709"
ACCESS_KEY = "VXwJYOQYjG20KhC37EaJgGBdiyh2Ob4f"
# Set the time between checks
MINUTES_BETWEEN_READS = 1
METRIC_UNITS = False
# ---------------------------------



class TemperatureThread(DataCollectionThread):
    def get_data(self):
        humidity, temp = self.sensor_module.get_data()

        data = {'data_type': 'temperature',
                'temp_c': round(float(temp), 2),
                'temp_f': round(float(temp) * 1.8 + 32, 2),
                'humidity': round(float(humidity), 2),
                'datetime': datetime.datetime.now()}

        return data


class LuxThread(DataCollectionThread):
    def get_data(self):
        lux = self.sensor_module.get_data()
        data = {'data_type': 'light',
                'lux': lux,
                'datetime': datetime.datetime.now()}
        return data


class WheelCounterThread(threading.Thread):
    def __init__(self, sensor_pin, led_pin, callback, run_event, queue):
        threading.Thread.__init__(self)

        self.sensor_pin = sensor_pin
        self.led_pin = led_pin
        self.run_event = run_event
        self.callback = callback
        self.queue = queue
        GPIO.setup(self.sensor_pin, GPIO.IN)
        GPIO.setup(self.led_pin, GPIO.OUT)

    def run(self):
        """

        :return:
        """
        last_time = None
        diameter = 13
        circumference = diameter * math.pi * 0.0000157828283
        period_counter = 0
        total_period = 10 * 1000
        timeout_value = 100  # milliseconds
        active = False
        led_on = False
        period_detection_count = 0
        period_distance = 0
        period_elapsed = 0

        # Loop while the run event is still set.  It'll typically be cleared on a Keyboard interrupt
        while self.run_event.is_set():

            # Wait for a change on the sensor. We'll timeout every 100 ms
            GPIO.wait_for_edge(self.sensor_pin, GPIO.BOTH, timeout=100)

            # Read the current input from the pin
            input_state = GPIO.input(self.sensor_pin)

            # Save the current time - we'll use that to calculate the speed
            this_time = datetime.datetime.now()

            # If the input state is 0, then there is a magnetic field on the Hall sensor
            if input_state == 0:

                # See if we've already detected an active state.  If so, nothing to do.
                if active is False:
                    active = True

                    # Turn on the LED to indicate that we have a detection
                    GPIO.output(self.led_pin, 1)
                    led_on = True

                    # Increment the number of detections
                    period_detection_count += 1

                    # Add to the distance
                    period_distance += circumference

                    # We're going to calculate the speed - for that, we need to know the elapsed time since the
                    # last detection
                    if last_time is not None:
                        # Get the time from the last detection to now
                        elapsed = (this_time - last_time).total_seconds()
                        period_elapsed += elapsed

                    last_time = this_time
            else:
                # No detection - the magnet has moved away from the sensor
                active = False

                # Shut the LED off - if it was on.  We do the check here so we don't keep sending unecessary 'off'
                # commands to the LED pin
                if led_on is True:
                    GPIO.output(self.led_pin, 0)
                    led_on = False

            # This is a check to see if the wheel has stopped moving for a time out period (e.g. 5 seconds).
            if last_time is not None and (this_time - last_time).total_seconds() > 5:
                logger.info("-------- Inactive for 5 seconds")
                last_time = None

            period_counter += timeout_value

            # See if we've exceeded the period, e.g. 60 seconds
            if period_counter > total_period:
                # Calculate the distance covered during this time period, as well as the average speed
                distance = period_detection_count * circumference
                if period_elapsed > 0:
                    avg_speed = distance / (period_elapsed / 3600)
                else:
                    avg_speed = 0

                wheel_active = True if period_detection_count > 0 else False

                # Report back
                data = {'datetime': datetime.datetime.now(),
                        'revolutions': period_detection_count,
                        'distance': distance,
                        'avg_speed': avg_speed,
                        'moving_time': period_elapsed,
                        'active': wheel_active}
#                self.callback(data)
                self.queue.put(data)
                period_counter = 0
                period_detection_count = 0
                period_elapsed = 0


class MainLoop:
    def __init__(self):
        self.gpio_setup()
        self.run_event = threading.Event()
        self.queue = Queue.Queue()
        self.lcd_queue = Queue.Queue()
        self.lcd = LCDDisplay()

        self.wx_file = ResultsWriter(filename='temperature.csv',
                                     fieldnames=['datetime', 'temp_c', 'temp_f', 'humidity'])
        self.lux_file = ResultsWriter(filename='lux.csv', fieldnames=['datetime', 'lux'])
        self.wheel_file = ResultsWriter(filename='wheel.csv',
                                        fieldnames=['datetime', 'distance', 'moving_time', 'revolutions',
                                                    'avg_speed', 'active'])

        # TODO
        self.lcd_message = None
        return

    def handle_wx_data(self, data):
        logger.info("WX: {0}".format(data))
        self.wx_file.writerow(data)

    def handle_data(self, data):
        logger.info(data)
        self.lux_file.writerow(data)

    def handle_wheel_data(self, data):
        logger.info(data)
        self.wheel_file.writerow(data)

    def gpio_setup(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

    def gpio_cleanup(self):
        GPIO.cleanup()

    def startup(self):
        self.run_event.set()

        dht_led_pin = 22
        dht_data_pin = 4
        GPIO.setup(dht_led_pin, GPIO.OUT)
        dht = dht22.DHT22(data_gpio_pin=dht_data_pin, led_gpio_pin=dht_led_pin)
        tsl = tsl_sensor.TSLSensor()

        thread_temp = TemperatureThread(30, self.handle_wx_data, dht, self.run_event, self.queue)
        thread_lux = LuxThread(60, self.handle_data, tsl, self.run_event, self.queue)
        thread_wheel = WheelCounterThread(18, 21, self.handle_wheel_data, self.run_event, self.queue)
        thread_lcd = LCDDisplayThread(self.run_event, self.lcd_queue, self.lcd)
        thread_button = ButtonHandlerThread(6, self.run_event, self.queue)
        thread_temp.start()
        thread_lux.start()
        thread_wheel.start()
        thread_lcd.start()
        thread_button.start()

        while True:
            try:
                # Wait for something on the queue, but only for a short time (1 ms). This will allow some
                # responsiveness on the loop (e.g. for CTRL+C shutdown) and will also act as the loop
                # delay since we're basically in a busy-wait loop
                data = self.queue.get(True, 0.001)
                logger.info("{0}: {1}".format(threading.currentThread().name, data))

                self.lcd_queue.put(data)

            except KeyboardInterrupt:
                logger.info("Keyboard Stop")
                self.run_event.clear()
                thread_temp.join()
                thread_lux.join()
                thread_wheel.join()
                GPIO.cleanup()

                # Cleanup the LCD
                self.lcd.set_backlight(1)
                self.lcd.clear()
                logger.info("Threads shutdown")
                break
            except Queue.Empty:
                # The queue.get with a timeout throws a Queue.Empty exception. Just continue if that happens
                continue
            except Exception, ex:
                logger.error("{0} exception caught".format(ex))
                continue

logger.info("Starting Hedgehog Monitor {0}, sensor_handler: v{1}".format(__version__, sensor_handlers.__version__))
mainloop = MainLoop()
mainloop.startup()
