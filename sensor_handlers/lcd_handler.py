import threading
import Queue
import logging
import datetime
import sqlite3
import os

__version__ = "0.0.6"

logger = logging.getLogger('hh')


class DataReportingThread(threading.Thread):
    def __init__(self, run_event, queue, lcd, version_msg, fadeout_time):
        threading.Thread.__init__(self)

        self.run_event = run_event
        self.queue = queue

        self.fadeout_time = fadeout_time

        self.lcd = lcd

        self.backlight_status = False
        self.message_list = list()
        self.current_message_num = 0

#        self.timeout_length = 6
        self.loop_sleep = 0.10

        self.version_msg = version_msg
        self.lcd.message(self.version_msg)

        self.display_version = 0
        self.display_wx = 1
        self.display_wheel = 2
        self.display_clock = 3
        self.display_msg = 4
        self.timeout_counter = 0

        self.db = DatabaseHandler()

        if os.path.exists("hedgehog.db") is False:
            logger.info("Database file {0} not found, creating".format("hedgehog.db"))
            self.db.create_database()

    def run(self):
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

    def toggle_backlight(self):
        backlight_set = 0 if self.backlight_status is True else 1
        self.lcd.set_backlight(backlight_set)
        self.backlight_status = not self.backlight_status

    def update_lcd(self):

        if self.backlight_status is False:
            self.backlight_status = True
            self.lcd.set_backlight(0)
        else:
            self.current_message_num += 1
            if self.current_message_num > self.display_msg:
                self.current_message_num = self.display_version

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
            message = "Good Morning"
        elif 12 <= hour < 18:
            message = "Good Afternoon"
        else:
            message = "Good Evening"

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

    def get_wheel_data(self):
        conn = sqlite3.connect('hedgehog.db')
        c = conn.cursor()

        sql = "select sum(distance),sum(revolutions), sum(moving_time) " \
              "from wheel_tbl where timestamp > datetime('now', '-24 hours')"

        result = c.execute(sql).fetchone()
        conn.close()
        return result


class DatabaseHandler:
    def __init__(self):
        self.db_name = 'hedgehog.db'


    def get_data(self, sql):
        try:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()

            result = c.execute(sql).fetchone()
            conn.close()

            data = tuple(result)
        except sqlite3.OperationalError as ex:
            logger.error("Database error retrieving data: {0}".format(ex))
            data = None

        return data

    def get_environment_data(self):
        wx = self.get_last_wx_data()
        lux = self.get_last_light_data()

        if wx is not None and lux is not None:
            data = (wx[0], wx[1], lux[0])
        else:
            data = None

        return data

    def get_wheel_data(self):
        sql = "select sum(distance),sum(revolutions), sum(moving_time) " \
              "from wheel_tbl where timestamp > datetime('now', '-24 hours')"

        return self.get_data(sql)

    def get_last_light_data(self):
        sql = "select lux, timestamp from light_tbl order by timestamp DESC"
        data = self.get_data(sql)
        return data

    def get_last_wx_data(self):
        """
        Retrieves the most recent value from the temperature/humidity table
        :param self:
        :return:
        """
        sql = "select temp, humidity, timestamp from temp_tbl order by timestamp DESC"
        data = self.get_data(sql)
        return data


    def create_database(self):
        """
        Creates the database and tables
        :return:
        """
        conn = sqlite3.connect(self.db_name)

        c = conn.cursor()
        c.execute("CREATE TABLE temp_tbl (timestamp DATETIME, temp REAL, humidity REAL, remote INTEGER)")
        c.execute("CREATE TABLE light_tbl (timestamp DATETIME, lux INTEGER, remote INTEGER)")
        c.execute("CREATE TABLE wheel_tbl(timestamp DATETIME, revolutions REAL, distance REAL, "
                  "moving_time REAL, avg_speed REAL, active INTEGER, remote INTEGER)")
        conn.commit()
        conn.close()

    def save_to_database(self, data):
        """

        :param data:
        :return:
        """
        data_type = data['data_type']
        if data_type == 'temperature':
            sql = ("INSERT INTO temp_tbl (timestamp, temp, humidity) values ('{0}', {1}, {2})".format(
                data['datetime'],
                data['temp_f'],
                data['humidity']))
        elif data_type == "wheel":
            active = 1 if data['active'] is True else 0
            sql = ("INSERT INTO wheel_tbl (timestamp, revolutions, distance, moving_time, avg_speed, active)"
                   "values ('{0}', {1}, {2}, {3}, {4}, {5})".format(
                data['datetime'],
                data['revolutions'],
                data['distance'],
                data['moving_time'],
                data['avg_speed'],
                active))
        elif data_type == 'light':
            sql = ("INSERT INTO light_tbl (timestamp, lux) values ('{0}', {1})".format(
                data['datetime'],
                data['lux']))
        else:
            return

        conn = sqlite3.connect("hedgehog.db")
        c = conn.cursor()
        try:
            c.execute(sql)
            conn.commit()
            conn.close()
        except Exception as ex:
            logger.error("Error inserting data into table:  {0}".format(ex))
