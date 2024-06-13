#
#   BSD LICENSE
#   Copyright (c) 2022 Samsung Electronics Corporation
#   All rights reserved.
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions
#   are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in
#       the documentation and/or other materials provided with the
#       distribution.
#     * Neither the name of Samsung Electronics Corporation nor the names of
#       its contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#   A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#   OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#   SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#   LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#   OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
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
            Method to get power usage.
            :return: power usage.
            usage : pytest test_hardware_management.py::test_get_power_usage
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

'''
def test_set_power_usage_value_1():
    """
            Method to get power usage.
            :return: power usage.
            usage : pytest test_hardware_management.py::test_get_power_usage
    """
    bool_resp, result = ob.set_power_limit_correction_time(power_limit_correction_time=300)
    print(result)

def test_set_power_usage_value_2():
    """
            Method to get power usage.
            :return: power usage.
            usage : pytest test_hardware_management.py::test_get_power_usage
    """
    bool_resp, result = ob.set_power_limit_exception(power_limit_exception="NoAction")
    print(result)

'''

