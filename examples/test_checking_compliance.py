#Copyright (c) 2024 Samsung Electronics Corporation
#SPDX-License-Identifier: BSD-3-Clause

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from lib.redfish_api import RedfishApi
from lib.generate_report import Report
import os
import logger as logging

logger = logging.get_logger(__name__)
ob = RedfishApi()
gr = Report()
local_path = os.path.dirname(os.path.realpath(__file__))


def test_hardware_management():
    bool_resp, result = ob.get_power_state()
    logger.info(result)
    if bool_resp == True:
        gr.generate_report(ob.html_results)
