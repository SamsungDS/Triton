# Triton: Redfish Tool

## About
Triton: Redfish Tool is a python3 tool which helps to perform the hardware management, power management through Redfish API's and verify the Redfish Specification by DMTF standard.

## Requirements
Ensure the machine running the tool has python3 installed.

You may install the external modules by running:

`pip3 install -r requirements.txt`

## Usage

- User needs to provide the required arguments such as hostIP, username, password and path of the tool into the configuration file “config_redfish.json”
- `python3 power_data.py`   or run any script in the example directory.
The tool will login into the service specified by the login_host argument using the credentials provided by the “username” and “password” arguments in the configuration file.

An HTML report is constructed and saved in the same directory as the tool.




