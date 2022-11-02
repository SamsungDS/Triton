# Redfish Compliance Tool

## About
Redfish Compliance Tool (RCT) is a python3 tool which serves as 2 in 1 purpose with its capability to perform the hardware management or getting the server information along with validating the Redfish URL’s and JSON schema of the output with Redfish Specification mentioned by DMTF.

##Requirements
Ensure the machine running the tool has python3 installed.

External modules:
•	DMTF’s python redfish library
•	Python modules  requests, argparse, yaml, json, jsonschema, traceback, os, re, sys, time, datetime
You may install the external modules by running:
pip3 install <module_name>

## Usage
Example: python3 redfish_api.py

The tool will login into the service specified by the login_host argument using the credentials provided by the “username” and “password” arguments in the configuration file.
It then reads all resources on the specified service, either will fetch the information or will manage the server. Once done will fetch the Redfish specification documents from DMTF website and validates the Redfish URL and JSON schema against the server in test.

User needs to provide the required arguments such as hostIP, username, password and path of the tool into the configuration file  “config_redfish.json”

An HTML report is constructed and saved in the same directory as the tool.




