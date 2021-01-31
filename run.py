from __future__ import print_function
import configparser
import os
import sys
import argparse
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
import time
import logging
from xfinity_usage.xfinity_usage import XfinityUsage



class configManager():

    def __init__(self, config, path):
        print('Loading Configuration File {}'.format(config))
        self.test_server = []
        #config_file = os.path.join(os.getcwd(), config)
        config_file = os.path.join(path, config)
        if os.path.isfile(config_file):
            self.config = configparser.ConfigParser()
            self.config.read(config_file)
        else:
            print('ERROR: Unable To Load Config File: {}'.format(config_file))
            sys.exit(1)

        self._load_config_values()
        print('Configuration Successfully Loaded')

    def _load_config_values(self):

        # General
        self.interval = self.config['GENERAL'].getint('Interval', fallback=14400)
        self.iterations = self.config['GENERAL'].getint('Iterations', fallback=1)
        self.verbose = self.config['GENERAL'].getboolean('Verbose', fallback=False)

        # Log
        self.log_enabled = self.config['LOG'].getboolean('Enabled', fallback=False)

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

        self.used = 0
        self.total = 0
        self.unit = None

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
            print('Used: {}'.format(str(self.used)))
            print('Total: {}'.format(str(self.total)))

        if self.file_enabled:
#FIXME __ DONE ???E
            #f = open('/usr/src/app/' + self.file_filename,'w')
            f = open(self.file_filename,'w')
            f.write(str(self.res) + '\n')
            f.close()

        if self.influx_enabled:
            self.write_influx_data(input_points)

    def run(self):

        xfinity = XfinityUsage(username=self.config.comcast_user, password=self.config.comcast_password, debug=self.config.verbose, attempts=1)
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
               time.sleep(self.config.interval)


def main():

    parser = argparse.ArgumentParser(description="A tool to collect xFinity internet usage metrics")
    parser.add_argument('--config', default='config.ini', dest='config', help='Specify a custom location for the config file')
    args = parser.parse_args()
    collector = XfinityUsageScrap(config=args.config)
    collector.run()


if __name__ == '__main__':
    main()
    

