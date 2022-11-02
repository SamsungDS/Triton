import pytest,sys,os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from lib.redfish_api import RedfishApi
from lib.generate_report import Report
import os
import logger as logging
logger = logging.get_logger(__name__)

local_path = os.path.dirname(os.path.realpath(__file__))

def test_hardware_management():
    ob=RedfishApi()
    gr = Report()
    bool_resp,result=ob.get_power_state()
    print(bool)
    if bool_resp==True:
        gr.generate_report()
