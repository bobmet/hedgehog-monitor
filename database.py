import sqlite3
import logging

__version__ = "0.0.1"

logger = logging.getLogger('hh')

class DatabaseHandler:
    """
    Class to wrap the database creation/queries
    """
    def __init__(self, database_name='hedgehog.db'):
        self.db_name = database_name

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
        """
        Retrieves the most recent temperature, humidity, and light levels from the database
        :return:
        """
        wx = self.get_last_wx_data()
        lux = self.get_last_light_data()

        if wx is not None and lux is not None:
            data = (wx[0], wx[1], lux[0])
        else:
            data = None

        return data

    def get_wheel_data(self):
        """
        Gets the most recent wheel information:  distance traveled, number of revolutions, and moving time
        over the last 24 hours
        :return:
        """
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
                   "values ('{0}', {1}, {2}, {3}, {4}, {5})".format(data['datetime'],
                                                                    data['revolutions'],
                                                                    data['distance'],
                                                                    data['moving_time'],
                                                                    data['avg_speed'],
                                                                    active))
        elif data_type == 'light':
            sql = ("INSERT INTO light_tbl (timestamp, lux) values ('{0}', {1})".format(data['datetime'],
                                                                                       data['lux']))
        else:
            return

        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        try:
            c.execute(sql)
            conn.commit()
            conn.close()
        except Exception as ex:
            logger.error("Error inserting data into table:  {0}".format(ex))
