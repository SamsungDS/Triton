#Copyright (c) 2024 Samsung Electronics Corporation
#SPDX-License-Identifier: BSD-3-Clause

import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from lib.redfish_api import RedfishApi
from lib.generate_report import Report
import os

ob = RedfishApi()
ob.redfishapi()
gr = Report()
import logger as logging

logger = logging.get_logger(__name__)

local_path = os.path.dirname(os.path.realpath(__file__))


def test_hardware_management():
    """
            Method to get power State.
            :return: power state.
            usage : pytest test_hardware_management.py::test_hardware_management
    """
    bool_resp, result = ob.get_power_state()
    if bool_resp == True:
        logger.info(json.dumps(result, indent=2))


def test_get_psu_inventry():
    """
            Method to get PSU inventry.
            :return: PSU inventry.
            usage : pytest test_hardware_management.py::test_get_psu_inventry
    """
    bool_resp, result = ob.get_psu_inventory()
    if bool_resp == True:
        print(json.dumps(result, indent=2))


def test_get_power_usage():
    """
            Method to get power usage.
            :return: power usage.
            usage : pytest test_hardware_management.py::test_get_power_usage
    """
    bool_resp, result = ob.power_usage()
    print(f'{result[0]} Watts')


def test_get_multi_power_usage():
    """
            Method to get power usage for multiple system.
            :return: power usage.
            usage : pytest test_hardware_management.py::test_get_multi_power_usage
    """
    power = ob.multi_power_usage()
    headers = ['System IP', 'System Name and Model', 'Current Power (watts)', 'Average (Watts)', 'Max Power (Watts)',
               'Min Power (Watts)', 'Power State']
    html_tb = gr.create_html_table(power, headers)
    file_name= gr.generate_hardware_report(html_tb)
def test_set_power_usage_value():
    """
            Method to set power usage.
            :return: power usage.
            usage : pytest test_hardware_management.py::test_set_power_usage
    """
    bool_resp, result = ob.set_power_limit(power_limit=540)
    print(result)

def test_execute_power_exceptions():
    result = ob.execute_power_exceptions()
    print(result)

def test_power_actions():
    power = ob.multi_power_usage()
    headers = ['System IP', 'System Name and Model', 'Current Power (watts)', 'Average (Watts)', 'Max Power (Watts)',
               'Min Power (Watts)', 'Power State']
    html_tb = gr.create_html_table(power, headers)
    file_name_before = gr.generate_hardware_report(html_tb)

    results = ob.actions_on_power_over_consumed_systems()
    time.sleep(60)
    power = ob.multi_power_usage()
    for system in results:
        for power_system in power:
            if system[0] in power_system:
               if power_system[-1] == "Power Off":
                  power_system.pop(); power_system.append("Power Off (By Triton) || " + "Last Recorded Power: " + str(system[2]) +"W || " + "Power Threshold : " + str(system[1])  + "W")
    print(power)
    html_tb = gr.create_html_table(power, headers)
    file_name_after = gr.generate_hardware_report(html_tb)
    print(f'Before power actions power report file name is {file_name_before}')
    print(f'After power actions power report file name is {file_name_after}')


def test_set_power_limit_correction():
    """
            Method to set power limit correction.
            :return: power limit status
            usage : pytest test_hardware_management.py::test_set_power_limit_correction
    """
    bool_resp, result = ob.set_power_limit_correction_time(power_limit_correction_time=300)
    print(result)

def test_set_power_limit_exception():
    """
            Method to set limit exception.
            :return: power limit correction status.
            usage : pytest test_hardware_management.py::test_set_power_limit_exception
    """
    bool_resp, result = ob.set_power_limit_exception(power_limit_exception="NoAction")
    print(result)


def test_power_on():
    """
            Method to test the power on server
            :return: power on server status.
            usage : pytest test_hardware_management.py::test_power_on
    """
    bool_resp = ob.system_power_on()

def test_power_off():
    """
            Method to test the power off server
            :return: power off server status.
            usage : pytest test_hardware_management.py::test_power_off
    """
    bool_resp = ob.system_Forceoff()

def test_GracefulShutdown():
    """
            Method to test the graceful shutdonw server
            :return: server graceful shutdown status.
            usage : pytest test_hardware_management.py::test_GracefulShutdown
    """
    bool_resp = ob.system_GracefulShutdown()

def test_ForceRestart():
    """
            Method to test the server force restart
            :return: server force restart status.
            usage : pytest test_hardware_management.py::test_ForceRestart
    """
    bool_resp = ob.system_ForceRestart()

def test_graceful_restart():
    """
            Method to test the graceful restart of server
            :return: graceful restart server status.
            usage : pytest test_hardware_management.py::test_graceful_restart
    """
    bool_resp = ob.system_graceful_restart()

