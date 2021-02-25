
import configparser
import os
import sys
import argparse
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
import time
import logging
import json
from xfinity_usage.xfinity_usage import XfinityUsage

import paho.mqtt.client as mqtt
import paho.mqtt.publish as mqttpublish
from datetime import datetime, timedelta
import time


class configManager():

    def __init__(self, config, path):
        #print('Loading Configuration File {}'.format(config))
        self.test_server = []
        #config_file = os.path.join(os.getcwd(), config)
        config_file = os.path.join(path, config)
        if os.path.isfile(config_file):
            self.config = configparser.ConfigParser()
            self.config.read(config_file)
        else:
            print('Unable To Load Config File: {}'.format(config_file))
            sys.exit(1)

        self._load_config_values()

        if self.log_enabled:
          loglevel = logging.WARNING
          if self.verbose:
              loglevel = logging.INFO
          if self.debug:
              loglevel = logging.DEBUG

          logger = logging.getLogger()
          filehandler = logging.FileHandler(self.log_file,'a')
          formatter = logging.Formatter('%(asctime)-15s::%(levelname)s::%(filename)s::%(funcName)s::%(lineno)d::%(message)s')
          filehandler.setFormatter(formatter)
          for hdlr in logger.handlers[:]:
              if isinstance(hdlr,logging.FileHandler):
                  log.removeHandler(hdlr)
          logger.addHandler(filehandler)
          logger.setLevel(loglevel)

          # Below is a 3.8.5 and beyond better/easier solution
          #logging.basicConfig(filename=self.log_file,
          #                    encoding='utf-8',
          #                    level=loglevel,
          #                    force=True)  # Force valid for python >=3.8, otherwise you
                                           #  have ordering issues for importing of logging

        logging.info('Configuration Successfully Loaded')

    def _load_config_values(self):

        # General
        self.interval = self.config['GENERAL'].getint('Interval', fallback=14400)
        self.iterations = self.config['GENERAL'].getint('Iterations', fallback=1)
        self.attempts = self.config['GENERAL'].getint('Attempts',fallback=1)
        self.verbose = self.config['GENERAL'].getboolean('Verbose', fallback=False)
        self.debug = self.config['GENERAL'].getboolean('Debug', fallback=False)
        intstart = self.config['GENERAL'].get('IntervalStart', fallback=None)

        # Figure out when the interval should start, i.e, anchor the interval to a
        # time in the day for predictable scrape times

        if intstart:
            now = datetime.now()
            targettime = datetime.strptime(intstart,"%H:%M:%S")
            starttime = now.replace(hour=targettime.hour,
                                    minute=targettime.minute,
                                    second=targettime.second)

            # Set the sync up to the next sync time, if it has already passed, shoot for the
            #  next day
            if starttime < now:
                self.firstrunoftheday = (starttime+timedelta(days=1)).timestamp()
            else:
                self.firstrunoftheday = starttime.timestamp()
        else:
            self.firstrunoftheday = 0

        # Log
        self.log_enabled = self.config['LOG'].getboolean('Enabled', fallback=False)
        self.log_file = self.config['LOG'].get('Filename', fallback='xfinity_usage.log')

        # File
        self.file_enabled = self.config['FILE'].getboolean('Enabled', fallback=False)
        self.file_filename = self.config['FILE'].get('Filename', fallback='output.json')

        # InfluxDB
        self.influx_enabled = self.config['INFLUXDB'].getboolean('Enabled', fallback=False)
        self.influx_address = self.config['INFLUXDB']['Address']
        self.influx_port = self.config['INFLUXDB'].getint('Port', fallback=8086)
        self.influx_database = self.config['INFLUXDB'].get('Database', fallback='xfinity')
        self.influx_user = self.config['INFLUXDB'].get('Username', fallback='')
        self.influx_password = self.config['INFLUXDB'].get('Password', fallback='')
        self.influx_ssl = self.config['INFLUXDB'].getboolean('SSL', fallback=False)
        self.influx_verify_ssl = self.config['INFLUXDB'].getboolean('Verify_SSL', fallback=True)

        # MQTT
        self.mqtt_enabled = self.config['MQTT'].getboolean('Enabled', fallback=False)
        self.mqtt_user = self.config['MQTT'].get('Username', fallback='mqtt')
        self.mqtt_password = self.config['MQTT'].get('Password', fallback='')
        self.mqtt_host = self.config['MQTT'].get('Address', fallback='localhost')
        self.mqtt_port = self.config['MQTT'].getint('Port', fallback=1883)
        self.mqtt_topic = self.config['MQTT'].get('Topic', fallback='xfinity')
        self.mqtt_retain = self.config['MQTT'].getboolean('Retain', fallback=False)

        # Comcast
        self.comcast_user = self.config['XFINITY'].get('Username', fallback='')
        self.comcast_password = self.config['XFINITY'].get('Password', fallback='')



class XfinityUsageScrap():

    def __init__(self, config=None):

        self.config = configManager(config=config,path='/app')

        self.iterations = self.config.iterations
        self.log_enabled = self.config.log_enabled
        self.file_enabled = self.config.file_enabled
        self.file_filename = self.config.file_filename
        self.influx_enabled = self.config.influx_enabled
        self.mqtt_enabled = self.config.mqtt_enabled
        self.firstrunoftheday = self.config.firstrunoftheday

        self.used = 0
        self.total = 0
        self.unit = None

        self

    def send_results(self):

        input_points = [
            {
                'measurement': 'comcast_data_usage',
                'fields': {
                    'used': self.used,
                    'total': self.total,
                    'unit': self.unit
                }
            }
        ]

        if self.log_enabled:
            logging.info('Used: {}'.format(self.used))
            logging.info('Total: {}'.format(self.total))

        res_payload = json.dumps(self.res,indent=4, sort_keys=True)

        if self.file_enabled:
#FIXME __ DONE ???E
            #f = open('/usr/src/app/' + self.file_filename,'w')
            f = open(self.file_filename,'w')
            f.write(res_payload + '\n')
            f.close()

        if self.influx_enabled:
            self.write_influx_data(input_points)

        if self.mqtt_enabled:

            auth= {'username': self.config.mqtt_user,
                   'password': self.config.mqtt_password
                  }

            try:
              mqttpublish.single(self.config.mqtt_topic,
                     payload=res_payload,
                     qos=0,
                     retain=self.config.mqtt_retain,
                     hostname=self.config.mqtt_host,
                     port=self.config.mqtt_port,
                     auth=auth,
                     client_id="xfinity_usage_reporter")
            except Exception as e:
                if self.log_enabled:
                    logging.error("Failed to publish to MQTT, exception {}".format(e))


    def run(self):

        xfinity = XfinityUsage(username=self.config.comcast_user, password=self.config.comcast_password, debug=self.config.verbose, attempts=self.config.attempts)
        #xfinity = XfinityUsage(username=self.config.comcast_user, password=self.config.comcast_password, debug=False)
        count = 0
        if (self.iterations == 0):
            # Run forever, since no increment when set to zero
            total = 1
        else:
            total = self.iterations
        while (count < total):
            if self.iterations > 0:
               count+=1
            if self.config.debug:
                try:
                  with open(self.file_filename) as f:
                      res = json.loads(f.read())
                except Exception as e:
                    logging.debug("Error opening {}, exception={}".format(self.file_filename,e))
                    res = {
                      'used': -1,
                      'total': -1,
                      'units': "None"
                    }

            else:
                res = xfinity.run()
            # print("Used %d of %d %s this month." % (
            #     res['used'], res['total'], res['units']
            # ))
            self.used = int(res['used'])
            self.total = int(res['total'])
            self.unit = res['units']
            self.res = res

            self.send_results()

            if (count < total):

                # Attempt to sync up our interval sleep to the next interval start time
                # until then we just sleep the normal interval.  When we are within
                # an interval of the sync time, just sleep till then, that is, if our
                # sync time is 00:00:00 we'll be sure to wake up at midnight and start
                # counting our intervals from there.  That only happens the first day we
                # are running, after that, the interval should be an even multiple of a day

                sleep = self.config.interval
                now = datetime.now()
                if self.firstrunoftheday:
                    if (now.timestamp()+self.config.interval) > self.firstrunoftheday:
                        # Sleep a shorter interval to sync up to the start time
                        sleep = self.firstrunoftheday - now.timestamp()
                        # stop checking from here on out as we are sync'd
                        self.firstrunoftheday = 0
                        logging.info("Syncing next interval to IntervalStart")

                nextwakeup = (now + timedelta(seconds=sleep)).strftime("%b %d, %Y at %I:%M:%S %p")
                logging.info("Next iteration at {}".format(nextwakeup))
                time.sleep(sleep)


def main():

    parser = argparse.ArgumentParser(description="A tool to collect xFinity internet usage metrics")
    parser.add_argument('--config', default='config.ini', dest='config', help='Specify a custom location for the config file')
    args = parser.parse_args()

    collector = XfinityUsageScrap(config=args.config)
    collector.run()


if __name__ == '__main__':
    main()
