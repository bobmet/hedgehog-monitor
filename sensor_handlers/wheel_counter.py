import threading
import datetime
import math
import RPi.GPIO as GPIO
import logging
import multiprocessing
import signal


logger = logging.getLogger('hh')


class WheelCounterThread(multiprocessing.Process):
    def __init__(self, sensor_pin, led_pin, callback, run_event, queue):
        multiprocessing.Process.__init__(self)

        GPIO.setmode(GPIO.BCM)

        self.sensor_pin = sensor_pin
        self.led_pin = led_pin
        self.run_event = run_event
        self.callback = callback
        self.queue = queue
        GPIO.setup(self.sensor_pin, GPIO.IN)
        GPIO.setup(self.led_pin, GPIO.OUT)

        signal.signal(signal.SIGINT, signal.SIG_IGN)

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
                data = {'data_type': 'wheel',
                        'datetime': datetime.datetime.now(),
                        'revolutions': period_detection_count,
                        'distance': distance,
                        'avg_speed': avg_speed,
                        'moving_time': period_elapsed,
                        'active': wheel_active}

                self.queue.put(data)
                period_counter = 0
                period_detection_count = 0
                period_elapsed = 0
