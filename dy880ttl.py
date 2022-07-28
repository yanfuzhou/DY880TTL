#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Yanfu Zhou
Email: yanfu.zhou@outlook.com
Project Page: https://yanfuzhou.github.io/
Created on: 04/20/2022
Updated on: 07/26/2022
"""
import os
import json
import time
import serial
import pynmea2
import raspy_qmc5883l
import pandas as pd
from datetime import datetime, timezone

# record interval
time_interval = 0.1

# user flag to choose whether streaming output to a csv file - data.csv
write_to_csv = True

# maximum allowed file size in bytes
max_file_size = 200000000

# filename and data path
filename = 'data_' + str(datetime.now()).replace(' ', '_') + '.csv'
csv_data_path = '/home/pi/data'

# clean output csv file output path
csv_path = os.path.join(csv_data_path, filename)
if os.path.exists(csv_path):
    os.remove(csv_path)

# maximum allowed number of csv files
max_num_log_csv = 5
dir_list = os.listdir(csv_data_path)
dir_list = list(f for f in dir_list if f.endswith('.csv'))
if len(dir_list) > max_num_log_csv:
    dir_list.sort()
    deleted_list = dir_list[0:-max_num_log_csv]
    for f in deleted_list:
        fp = os.path.join(csv_data_path, f)
        os.remove(fp)

# create output csv file schema
columns = ['datetime', 'latitude', 'longitude', 'altitude', 'altitude_units', 'num_sats', 'heading']
df = pd.DataFrame(columns=columns)
df.to_csv(csv_path, sep=',', quotechar='"', header=True, index=False)

# serial port connection config
port, baud, timeout = '/dev/ttyS0', 9600, 3.0

# create i2c qmc5883l sensor object
sensor = raspy_qmc5883l.QMC5883L()
# magnetic declination and calibration
sensor.declination = -1.6
sensor.calibration = [[1.1069994299342611, -0.031912765287706035, 3166.9264804707445],
                      [-0.031912765287706035, 1.0095180375160309, 2428.332136046326],
                      [0.0, 0.0, 1.0]]

# create dy880tl gps sensor i/o buffer
ser = serial.Serial(port, baudrate=baud, timeout=timeout)


def parse_gps(d, h):
    if d.find('GGA') > 0:
        msg = pynmea2.parse(d)
        gps_data = dict(datetime=datetime.now(timezone.utc).timestamp(),
                        latitude=msg.latitude,
                        longitude=msg.longitude,
                        altitude=msg.altitude,
                        altitude_units=msg.altitude_units,
                        num_sats=msg.num_sats,
                        heading=h)
        if write_to_csv:
            adf = pd.DataFrame(gps_data, index=[0])
            adf.to_csv(csv_path, sep=',', quotechar='"', mode='a', header=False, index=False)
        else:
            # todo: post to rest api for streaming
            print(json.dumps(gps_data))


def main():
    while True:
        time.sleep(time_interval)
        try:
            line = ser.readline().decode()
            parse_gps(line, 360.0-sensor.get_bearing())
        except serial.SerialException as e:
            print('Device error: {}'.format(e))
            continue
        except pynmea2.ParseError as e:
            print('Parse error: {}'.format(e))
            continue
        file_size = os.stat(csv_path)
        if file_size.st_size > max_file_size:
            break


if __name__ == "__main__":
    main()

