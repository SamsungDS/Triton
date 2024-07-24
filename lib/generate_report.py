#Copyright (c) 2024 Samsung Electronics Corporation
#SPDX-License-Identifier: BSD-3-Clause

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../lib")))
from redfish_api import RedfishApi
import json
import os
import sys
import logger as logging
from datetime import datetime

logger = logging.get_logger(__name__)
rd = RedfishApi()

class Report:
    def __init__(self):
        try:
            with open("config/config_redfish.json") as config_json:
                self.config_dict = json.load(config_json)

        except Exception as e:
            logger.error("Failed with error message {}".format(e))
            return False

    def generate_report(self, html_results):
        """
        Method to generate HTML report for json schema and uri validation.
        :param logdir: path where you want to store your html report
        :return: None
        """
        try:
            logdir = self.config_dict["logdir"]
            # The string template for the report
            html_string = """<html>
            <head>
            <title>Redfish Validation Test Report</title>
            <style>
              .pass {{background-color:#7FFF00}}
              .fail {{background-color:#FF0000}}
              .bluebg {{background-color:#6495ED}}
              .center {{text-align:center;}}
              .titlerow {{border: 2pt solid}}
              .notvalid {{background-color:#FFFF00}}
              body {{background-color:lightgrey; border: 1pt solid; text-align:center; margin-left:auto; margin-right:auto}}
              th {{text-align:center; background-color:beige; border: 1pt solid}}
              td {{text-align:left; background-color:white; border: 1pt solid; word-wrap:break-word;}}
              table {{width:90%; margin: 0px auto; table-layout:fixed;}}
            </style>
            </head>
            <table>
              <tr>
                <th>
                  <h2>##### Redfish Validation Test Report #####</h2>
                  {}<br/>
                </th>
              </tr>
              <tr>
                <th>
                  Host: {}<br/>
                  System Manufacturer and Model: {} : {}<br/>
                  Redfish Version: {}<br/>
                </th>
              </tr>
              <tr>
                <th class=\"titlerow bluebg\">
                  <b>Results</b>
                </th>
              </tr>
              {}
            </table>
            </html>
            """
            # Build the results section of the report
            self.html_results = "<tr><td><table>" + html_results + "</table></td></tr>"
            current_time = datetime.now()
            log_file = datetime.strftime(current_time, "RedfishTestReport_%m_%d_%Y_%H%M%S.html")
            if logdir is not None:
                if not os.path.isdir(logdir):
                    os.makedirs(logdir)
                log_file = logdir + os.path.sep + log_file
            logger.info("Generating {}...".format(log_file))
            with open(log_file, "w", encoding="utf-8") as out_file:
                out_file.write(
                    html_string.format(current_time.strftime("%c"), rd.login_host, rd.system_manufacturer,
                                       rd.system_model, rd.redfish_version, self.html_results))
        except Exception as e:
            logger.error("error msg: {}".format(e))
            sys.exit(1)

    def generate_hardware_report(self, html_results):
        """
        Method to generate HTML report for Hardware details.
        :return: file name of the report will be returned
        """
        try:
            logdir = self.config_dict["logdir"]
            # The string template for the report
            html_string = """<html>
            <head>
            <title>System Report</title>
            <style>
              .pass {{background-color:#7FFF00}}
              .fail {{background-color:#FF0000}}
              .bluebg {{background-color:#6495ED}}
              .center {{text-align:center;}}
              .titlerow {{border: 2pt solid}}
              .notvalid {{background-color:#FFFF00}}
              body {{background-color:lightgrey; border: 1pt solid; text-align:center;}}
              th {{text-align:center; background-color:beige; border: 1pt solid}}
              td {{text-align:left; background-color:white; border: 1pt solid; word-wrap:break-word;}}
              table {{width:90%; margin: 0px auto; table-layout:fixed;}}
            </style>
            </head>
            <table>
              <tr>
                <th>
                  <h2> 9th Floor *** Storage Solutions Lab *** Servers Power Report </h2>
                  {}<br/>
                </th>
              </tr>
              <tr>
                <th class=\"titlerow bluebg\">
                  <b>Details</b>
                </th>
              </tr>
              {}
            </table>
            </html>
            """
            # Build the results section of the report

            self.html_results = "<tr><td><table>" + html_results + "</table></td></tr>"
            current_time = datetime.now()
            log_file = datetime.strftime(current_time, "SystemDetails_%m_%d_%Y_%H%M%S.html")
            if logdir is not None:
                if not os.path.isdir(logdir):
                    os.makedirs(logdir)
                log_file = logdir + os.path.sep + log_file
            logger.info("Generating {}...".format(log_file))
            with open(log_file, "w", encoding="utf-8") as out_file:
                out_file.write(
                    html_string.format(current_time.strftime("%c"), self.html_results))
            return log_file
        except Exception as e:
            logger.error("error msg: {}".format(e))
            sys.exit(1)

    def create_html_table(self, data, headers):
        """
        Method to generate HTML table
        :return: HTML table
        """
        power_threshold = self.config_dict["power_threshold"]
        html = '<table>'
        html += "<tr><th>{}</th><th>{}</th><th>{}</th><th>{}</th><th>{}</th><th>{}</th><th>{}</th></tr>\n".format(headers[0],
                                                                                                       headers[1],
                                                                                                       headers[2],
                                                                                                       headers[3],
                                                                                                       headers[4],
                                                                                                       headers[5],
                                                                                                       headers[6])
        for row in data:
            html += '<tr>'
            for value in row:
                if type(value) == int and value >= power_threshold:
                    html += '<td style="background-color: red;">{}</td>'.format(value)
                elif type(value) == int and value >= (power_threshold * 0.9):
                    html += '<td style="background-color: orange;">{}</td>'.format(value)
                elif type(value) == int and value < power_threshold:
                    html += '<td style="background-color: lightgreen;">{}</td>'.format(value)
                else:
                   html += '<td>{}</td>'.format(value)
            html += '</tr>'
        html += '</table>'
        return html
