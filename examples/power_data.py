import csv
import json
import os
import schedule
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from lib.redfish_api import RedfishApi
from lib.generate_report import Report
import os
import lib.logger as logging

logger = logging.get_logger(__name__)
ob = RedfishApi()
gr = Report()
local_path = os.path.dirname(os.path.realpath(__file__))

with open("../config/config_redfish.json") as config_json:
    config_dict = json.load(config_json)

time_interval = config_dict["time_interval"]
time_type = config_dict["time_type"]
num_system = len(config_dict["systems"])

fields = ['date_time']

for host in range(num_system):
    server = (config_dict["systems"][host]["login_host"])
    hostip = 'server_power(w): {}'.format(server)
    fields.append(hostip)

global csv_file, csv_writer
csv_file = open('records.csv', 'a')
csvwriter = csv.writer(csv_file)
csvwriter.writerow(fields)
csv_file.close()


def test_inventory():
    """
        Method to fetch power of multiple servers and generate a csv file and log file
        :return: None
    """
    power_list = ob.multi_power_usage()
    power_threshold = config_dict["power_threshold"]
    for server in power_list:
        if server[2] >= power_threshold:
            server_ip = server[0]
            line = "server: {} power is {} exceeded the threshold value".format(server_ip, server[2])
            s = str(datetime.now())
            with open('power_threshold.txt', 'a') as f:
                f.write(s + '\t')
                f.writelines(line + '\n')

    rows = []
    for i in power_list:
        rows.append(i[2])

    filename = "records.csv"
    with open(filename, 'a') as csv_file:
        csvwriter = csv.writer(csv_file)
        current_date_time = datetime.now()
        row1 = [str(current_date_time)]
        print("what is row", row1)
        row2 = row1 + rows
        print("what is row2", row2)
        csvwriter.writerow(row2)
        #for val in row2:
        #    csvwriter.writerow(row2)


if time_type == "seconds":
    schedule.every(time_interval).seconds.do(test_inventory)
elif time_type == "minutes":
    schedule.every(time_interval).minutes.do(test_inventory)
else:
    schedule.every(time_interval).hours.do(test_inventory)

while True:
    schedule.run_pending()
    time.sleep(1)
