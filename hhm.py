# -*- coding: utf-8 -*-
"""
Created on Thu Jul 14 23:20:03 2016

@author: pi
"""

import datetime
import time
import timeit

import RPi.GPIO as GPIO

import threading
import dht22
import tls_sensor
from results_writer import ResultsWriter
import logging
import math


__version__ = "0.2"

logging.basicConfig(format=('%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
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


class DataAcquisitionThread(threading.Thread):
    """
    Class to handle acquiring data from a sensor.  It's a subclass of the main threading.Thread class
    to handle getting the data in a separate thread.
    """
    def __init__(self, loop_delay, callback, sensor_module, run_event):

        threading.Thread.__init__(self)

        self.loop_delay = loop_delay
        self.callback = callback
        self.sensor_module = sensor_module
        self.run_event = run_event

    def run(self):
        time_counter = 0.0
        self.report(self.get_data())

        # This will loop while the keep running event is set.  If it gets cleared (external to the thread, e.g.
        # from a KeyboardInterrupt in the calling thread, then the loop will exit and the thread will close.

        while self.run_event.is_set():
            if time_counter >= self.loop_delay:

                start_time = timeit.default_timer()
                data = self.get_data()
                stop_time = timeit.default_timer()
                elapsed = stop_time - start_time
                self.report(data)
                time_counter = elapsed
            time.sleep(0.1)
            time_counter += 0.1

        logger.info("Thread {0} closing".format(threading.currentThread().getName()))

    def get_data(self):
        return None

    def report(self, data_points):
        self.callback(data_points)


class TemperatureThread(DataAcquisitionThread):
    def get_data(self):
        humidity, temp = self.sensor_module.get_data()

        data = {'temp_c': round(float(temp), 2),
                'temp_f': round(float(temp) * 1.8 + 32, 2),
                'humidity': round(float(humidity), 2),
                'datetime': datetime.datetime.now()}

        return data


class LuxThread(DataAcquisitionThread):
    def get_data(self):
        lux = self.sensor_module.get_data()
        data = {'lux': lux,
                'datetime': datetime.datetime.now() }
        return data

class WheelCounterThread(threading.Thread):
    def __init__(self, sensor_pin, led_pin, callback, run_event):
        threading.Thread.__init__(self)

        self.sensor_pin = sensor_pin
        self.led_pin = led_pin
        self.run_event = run_event
        self.callback = callback
        GPIO.setup(self.sensor_pin, GPIO.IN)
        GPIO.setup(self.led_pin, GPIO.OUT)

    def run(self):
        """

        :return:
        """
        detect_count = 0
        led_state = 0
        last_time = None
        diameter = 13
        current_distance = 0
        current_elapsed_time = 0
        daily_distance = 0
        circumference = diameter * math.pi * 0.0000157828283
        timeout_delay = 10
        timer_count = 0

        period_counter = 0
        total_period = 10 * 1000
        timeout_value = 100 # milliseconds
        detection_active = False

        # --------------------------------------------------------------------
        # Loop until we clear the run_event, which means the program is exiting
        # ---------------------------------------------------------------------
        while self.run_event.is_set():

            # ----------------------------------------------------
            # Check the input.
            # ----------------------------------------------------
            GPIO.wait_for_edge(self.sensor_pin, GPIO.BOTH, timeout=100)
            active = GPIO.input(self.sensor_pin)

            if active == 0:
                # ----------------------------------------------------
                # Increment the number of times a field was detected
                # ----------------------------------------------------
                if detection_active is False:
                    detect_count += 1

                    # ----------------------------------------------------
                    # Save the current time
                    # ----------------------------------------------------
                    this_time = datetime.datetime.now()

                    logger.info("Active, count: {0} time: {1}".format(detect_count, this_time))

                    # ----------------------------------------------------
                    # Turn on the LED
                    # ----------------------------------------------------
                    led_state = 1
                    GPIO.output(self.led_pin, 1)

                    detection_active = True

                    if last_time is not None:
                        time_diff = (this_time - last_time).total_seconds()

                        if time_diff > 5:
                            speed = 0
                            logger.info("---------Time Out, {0} - {1}, {2}".format(this_time, last_time, time_diff))
                            last_time = None
                        else:
                            speed = circumference / (time_diff/3600)
                            current_distance += circumference
                            current_elapsed_time += time_diff
                    last_time = this_time
            else:
                detection_active = False
                if led_state == 1:
                    GPIO.output(self.led_pin, 0)
                    led_state = 0

            period_counter += timeout_value
            if period_counter >= total_period:
                if current_elapsed_time > 0:
                    avg_speed = current_distance / (current_elapsed_time / 3600)
                else:
                    avg_speed = 0

                logger.info("Timeout, count: {0}, speed: {1}, distance = {2} "
                            "elapsed: {3}, avg-speed: {4}".format(detect_count, speed, current_distance,
                                                                  current_elapsed_time, avg_speed))
                period_counter = 0
                detect_count = 0
                speed = 0
                current_distance = 0
                current_elapsed_time = 0

#         while self.run_event.is_set():
#             timer_count += timeout_delay
#             logger.info(timer_count)
#             if timer_count >= 10.0:
#                 logger.info("10 seconds")
#                 timer_count = 0
#
#             GPIO.wait_for_edge(self.sensor_pin, GPIO.BOTH, timeout=10000)
#             active = GPIO.input(self.sensor_pin)
#             if active == 0:
#                 led_state = 1
#                 detect_count += 1
#                 this_time = datetime.datetime.now()
#                 if last_time is not None:
#                     time_diff = (this_time - last_time).total_seconds()
#                     if time_diff > 5:
#                         speed = 0
#                         logger.info("Time Out")
#                     else:
#                         speed = circumference / (time_diff/3600)
#                         distance_total += circumference
#                     data = { 'revolutions': detect_count,
#                              'speed': speed,
#                              'distance': distance_total}
#                     self.callback(data)
# #                    logger.info("Detect count: {0}, time_diff = {1}, speed = {2}, distance = {3}".format(detect_count, time_diff, speed, distance_total))
#                 last_time = this_time
#             else:
#
#                 led_state = 0
#
#             GPIO.output(self.led_pin, led_state)


class MainLoop:
    def __init__(self):
        self.gpio_setup()
        self.run_event = threading.Event()
        self.wx_file = ResultsWriter(filename='temperature.csv', fieldnames=['datetime', 'temp_c', 'temp_f', 'humidity'])
        self.lux_file = ResultsWriter(filename='lux.csv', fieldnames=['datetime', 'lux'])
        return

    def handle_wx_data(self, data):
        logger.info("WX: {0}".format(data))
        self.wx_file.writerow(data)

    def handle_data(self, data):
        logger.info(data)
        self.lux_file.writerow(data)

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
        tsl = tls_sensor.TSLSensor()

        thread_temp = TemperatureThread(60, self.handle_wx_data, dht, self.run_event)
        thread_lux = LuxThread(60, self.handle_data, tsl, self.run_event)
        thread_wheel = WheelCounterThread(18, 21, self.handle_data, self.run_event)

        thread_temp.start()
        thread_lux.start()
        thread_wheel.start()

        while True:
            try:
                time.sleep(0.01)
            except KeyboardInterrupt:
                print "Keyboard Stop"
                self.run_event.clear()
                thread_temp.join()
                thread_lux.join()
                thread_wheel.join()
                GPIO.cleanup()
                break



logger.info("Starting Hedgehog Monitor {0}".format(__version__))
mainloop = MainLoop()
mainloop.startup()


        
