import Queue
import datetime
import logging
import os
import threading

from database import DatabaseHandler

__version__ = "0.0.7"

logger = logging.getLogger('hh')


class DataReportingThread(threading.Thread):
    def __init__(self, run_event, queue, lcd, version_msg, fadeout_time, db_name):
        threading.Thread.__init__(self)

        self.run_event = run_event
        self.queue = queue

        self.fadeout_time = fadeout_time

        self.lcd = lcd

        self.backlight_status = False
        self.message_list = list()
        self.current_message_num = 0

        self.loop_sleep = 0.10
        self.timeout_counter = 0

        self.version_msg = version_msg

        # LCD messages
        self.lcd.message(self.version_msg)

        self.display_msg = 0
        self.display_wx = 1
        self.display_wheel = 2
        self.display_clock = 3
        self.display_version = 4
        self.last_message = 4
        self.first_message = 0

        self.db = DatabaseHandler(db_name)

        if os.path.exists(db_name) is False:
            logger.info("Database file {0} not found, creating".format(db_name))
            self.db.create_database()

    def run(self):
        """
        Run handler for the data reporting subprocess.  This checks for data coming over a queue; if there is any,
        it'll pull the data, save it to the database, and update the LCD.
        :return:
        """
        last_datetime = None
        while self.run_event.is_set():
            try:
                self.timeout_counter += self.loop_sleep

                # If the backlight is on, check to see if it's been on longer than the "fadeout" time.  If so
                # shut it off
                if self.timeout_counter >= self.fadeout_time:
                    if self.backlight_status is True:
                        self.lcd.set_backlight(1)
                        self.backlight_status = False
                    self.timeout_counter = 0

                # If we're showing the clock, update it.  We need to do it here before we wait on the queue,
                # otherwise we'll essentially block behind the queue.get() call
                if self.current_message_num == self.display_clock:
                    current_time = datetime.datetime.now().strftime("%H:%M")
                    if current_time != last_datetime:
                        self.update_time()
                        last_datetime = current_time

                # Wait here for something to show up on the queue.  If the timeout expires with nothing, it'll
                # throw a Queue.Empty exception
                data = self.queue.get(True, self.loop_sleep)

#                logger.info("LCD_HANDLER: {0}".format(data))
                # If we have some data, and it's what we're expecting...
                if 'data_type' in data:
                    self.handle_update(data)

            except Queue.Empty:
                # The queue.get with a timeout throws a Queue.Empty exception. Just continue if that happens
                pass

        logger.info("Thread {0} closing".format(threading.currentThread().name))

    def handle_update(self, data):
        """
        :param self:
        :param data: Dictionary which holds the sensor data
        :return:
        """
        data_type = data['data_type']

        if data_type == 'temperature':
            if self.current_message_num == self.display_wx:
                self.update_environment()

        elif data_type == 'light':
            if self.current_message_num == self.display_wx:
                self.update_environment()
        elif data_type == 'wheel':
            if self.current_message_num == self.display_wheel:
                self.update_wheel()
        elif data_type == 'button':
            self.update_lcd()
            self.timeout_counter = 0

        self.db.save_to_database(data)

    def update_lcd(self):
        """

        :return:
        """
        if self.backlight_status is False:
            self.backlight_status = True
            self.lcd.set_backlight(0)
        else:
            self.current_message_num += 1
            if self.current_message_num > self.last_message:
                self.current_message_num = self.first_message

            logger.info("Current screen: {0}".format(self.current_message_num))

            if self.current_message_num == self.display_version:
                self.update_version()
            elif self.current_message_num == self.display_wx:
                self.update_environment()
            elif self.current_message_num == self.display_clock:
                self.update_time()
            elif self.current_message_num == self.display_wheel:
                self.update_wheel()
            elif self.current_message_num == self.display_msg:
                self.update_message()


    def update_message(self):
        hour = datetime.datetime.now().hour
        if hour < 12:
            greeting = "Good Morning"
        elif 12 <= hour < 18:
            greeting = "Good Afternoon"
        else:
            greeting = "Good Evening"

        message = "S'more Monitor\n{0}".format(greeting)
        self.lcd.clear()
        self.lcd.message(message)

    def update_version(self):
        message = self.version_msg
        self.lcd.clear()
        self.lcd.message(message)

    def update_wheel(self):
        """
        Retrieves data aon the wheel and displays it
        :return:
        """

        # Get the database info - last 24 hours of data
        wheel_data = self.db.get_wheel_data()
        if wheel_data is not None:
            distance = wheel_data[0] if wheel_data[0] is not None else 0
            revs = wheel_data[1] if wheel_data[1] is not None else 0
            moving_time = wheel_data[2] if wheel_data[2] is not None else 0

            #  Watch for a divide by zero error - should only happen if we have no data
            try:
                speed = distance / moving_time * 3600
            except ZeroDivisionError:
                speed = 0

            # Format the display.  We're showing revolutions and distance on one line,
            # elapsed time and average speed on the second line
            turns_display = "{revs:.0f}t".format(revs=revs)
            distance_display = "{dist:>{just}.3f}mi".format(dist=distance, just=16-len(turns_display) - 1 - 2)
            time_display = "{time:,.0f}s".format(time=moving_time)
            speed_display = "{speed:{just}.2f}mph".format(speed=speed, just=16-len(time_display) - 1 - 2)

            message = "{0} {1}\n{2}{3}".format(turns_display, distance_display, time_display, speed_display)
        else:
            message = "Not Available"

        self.lcd.clear()
        self.lcd.message(message)

    def update_environment(self):
        """

        :return:
        """

        # Get the latest environment data from the database
        data = self.db.get_environment_data()
        if data is not None:
            temp_f = data[0]
            humidity = data[1]
            lux = data[2]

            temp_display = "{0}{1}{2}".format(temp_f, chr(223), 'F')
            humidity_display = "{0:.1f}%".format(humidity)
            lux_display = "{0} lux".format(lux)

            temp_len = len(temp_display)
            message = "{0} {1:>{just}}\n{lux:^16}".format(temp_display,
                                                          humidity_display,
                                                          just=16-temp_len-1,
                                                          lux=lux_display)
        else:
            message = "Not Available"
        self.lcd.clear()
        self.lcd.message(message)

    def update_time(self):
        time_now = datetime.datetime.now()
        display_time = time_now.strftime("%a %m/%d/%Y\n%I:%M %p")
        message = display_time
        self.lcd.clear()
        self.lcd.message(message)



