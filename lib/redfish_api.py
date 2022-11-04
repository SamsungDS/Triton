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

import redfish #DMTF's python-redfish-library, you can install it by using "pip3 install redfish"-command in your system. Python3 library to interact with devices that supports redfish service.
import sys
import requests
import argparse
import traceback
import yaml #pyyaml version>=5.1
import json
import jsonschema
from jsonschema import validate
import re
import time
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../lib")))
import logger as logging
from datetime import datetime
logger=logging.get_logger(__name__)
class RedfishApi:
    def __init__(self):
        try:
            try:
                with open("../config/config_redfish_2.json") as config_json:
                    self.config_dict=json.load(config_json)
            except Exception as e:
                logger.error("error msg: {}".format(e))
                sys.exit(1)
            self.login_host=self.config_dict["login_host"]
            self.html_results = ""
            try:
                if "https" in self.login_host:
                    self.REDFISH_OBJ =redfish.redfish_client(base_url=self.login_host, username=self.config_dict["username"], password=self.config_dict["password"],                           default_prefix='/redfish/v1')
                    self.REDFISH_OBJ.login(auth="basic")
                else:  
                    self.REDFISH_OBJ =redfish.redfish_client(base_url=self.login_host,default_prefix='/redfish/v1')
            except:
                #traceback.print_exc()
                print("Error in making redfish object with given configurations")
                sys.exit(1)
            print("Fetching openAPI schema file from web........")
            self.get_openapi_from_redfish_org()
            print("Fetched!")
            self.redfish_version=(self.REDFISH_OBJ.get(self.config_dict["base_url"],None)).dict["RedfishVersion"]
            self.system_manufacturer=(self.REDFISH_OBJ.get(self.config_dict["system_url"],None)).dict["Manufacturer"]
            self.system_model=(self.REDFISH_OBJ.get(self.config_dict["system_url"],None)).dict["Model"]
        except Exception as e:
            logger.error("error msg: {}".format(e))
            sys.exit(1)
            
    def get_extended_error_msg(self,response_body):
        """
        Method to get extended error message from response body
        :param response_body: JSON response body
        :return: error message from @Message.ExtendedInfo or will return whole error response body if any exception occurs.
        """
        try:
            msg_dict=response_body.dict["error"]["@Message.ExtendedInfo"][0]
            if "Message" in msg_dict:
                msg=str(msg_dict["Message"])
            else:
                msg=str(msg_dict["MessageId"])
            return msg
        except:
            #traceback.print_exc()
            msg=response_body
            return msg
            
    def redfish_response(self,method,url,body=None,headers=None):
        """
        Method to get json response from given request( i.e. get,post,patch etc)
        :param method: method refers to the 'get','post','patch','delete' here
        :param url: url from which response is required 
        :param body: request body for certain requests(i.e. patch,post etc), default value is None
        :param headers: request headers, default value is None
        :return: Bool,json response
        """
        try:
            #Validating uri against openApi specified uris:
            self.validate_uri(url)
            #Adding data for json schema validation report:
            if method != "get":
                self.html_results=self.html_results + "<td class=\"notvalid center\" width=\"30%\">N/A</td></tr>"
            #Getting HTTP responses:
            if method=="get":
                response=self.REDFISH_OBJ.get(url,None)
                if response.status in self.config_dict["response_codes"]["success"]:
                    #Validating Json Schema for "GET" response bodies:
                    self.validate_json(url,response)
                    return True,response
                else: 
                    raise Exception("Failed")
            elif method=="patch":
                response=self.REDFISH_OBJ.patch(url,body=body,headers=headers)
                if response.status in self.config_dict["response_codes"]["success"]:
                    task=response.monitor(self.REDFISH_OBJ)
                    while task.is_processing:
                        retry_time=task.retry_after
                        task_status=task.dict["TaskState"]
                        time.sleep(retry_time if retry_time else 5)
                        task=response.monitor(self.REDFISH_OBJ)
                    #print(self.redfish_response("get",url)[1].dict[list(body.keys())[0]])
                    return True,response
                else:
                    raise Exception("Failed")
            elif method=="post":
                response=self.REDFISH_OBJ.post(url,body=body,headers=headers)
                if response.status in self.config_dict["response_codes"]["success"]:
                    task=response.monitor(self.REDFISH_OBJ)
                    while task.is_processing:
                        retry_time=task.retry_after
                        task_status=task.dict["TaskState"]
                        time.sleep(retry_time if retry_time else 5)
                        task=response.monitor(self.REDFISH_OBJ)
                    return True,response
                else:
                    raise Exception("Failed")
            elif method=="delete":
                response=self.REDFISH_OBJ.delete(url,headers=headers)
                if response.status in self.config_dict["response_codes"]["success"]:
                    return True,response
                else:
                    raise Exception("Failed") 
        except Exception:
            #traceback.print_exc()
            logger.error("'{}' for url : '{}' failed with response code : {} and error msg : {}".format(method,url,response.status,self.get_extended_error_msg(response)))
            return False,response
    
    def parseOdataType(self,json_response):
        """
        Method to parse '@odata.type' to get schema name
        :param json_response: JSON response body
        :return: Bool,schema name 
        """
        try:
            schema_name=""
            dict_response=json_response.dict
            if "@odata.type" not in dict_response:
                return False,schema_name
            else:
                resourceOdataType=dict_response["@odata.type"]
                odataTypeMatch = re.compile('^#([a-zA-Z0-9]*)\.([a-zA-Z0-9\._]*)\.([a-zA-Z0-9]*)$')  
                resourceMatch = re.match(odataTypeMatch, resourceOdataType)
                if resourceMatch is None:
                    # with no version component
                    odataTypeMatch = re.compile('^#([a-zA-Z0-9]*)\.([a-zA-Z0-9]*)$')
                    resourceMatch = re.match(odataTypeMatch, resourceOdataType)
                    if (resourceMatch is None):
                        return False,schema_name  
                    else:
                        namespace = resourceMatch.group(1)
                        version = None
                else:
                    namespace=resourceMatch.group(1)
                    version=resourceMatch.group(2)
                if version is not None:
                    schema_name = '.'.join([namespace,version])
                else:
                    schema_name = namespace 
                schema_name += '.json'
                return True,schema_name
        except Exception as e:
            logger.error("error msg: {}".format(e)) 
    
    def get_schema_from_redfish_org(self,schema_name):
        """
        Method to get particular json schema for passed schema name from schema url of redfish organisation
        :param schema_name: Schema name got from '@odata.type'
        :return: Bool,string output for json schema 
        """
        try:
            result=requests.get(self.config_dict["schema_url"]+schema_name)
            if result.status_code!=200:
                raise Exception("Failed")
            return True,result.text #string result is returned
        except:
            logger.error("{}-not found with response code as:{}".format(schema_name,result.status_code))
            return False,None  
    
    def validate_json(self,url,json_response):
        """
        Method to validate json response body with standard json schema( acc. to redfish specification)
        :param url: url of which response to be validated
        :param json_response: JSON response body
        :return: None 
        """
        try:
            bool_resp1,schema_name=self.parseOdataType(json_response)
            if bool_resp1==True:
                print(schema_name)
            else:
                logger.error("@odata.type is not present in response")
                return
            bool_resp2,schema=self.get_schema_from_redfish_org(schema_name)
            if bool_resp2==True:
                schema_dict=json.loads(schema)#string is converted into python dict object.
            else:
                return
            validate(instance=json_response.dict, schema=schema_dict)
            logger.info("JSON schema validated for url '{}'".format(url))
            #HTML report data for passed validation
            msg="PASS"
            result_class = "class=\"pass center\""
            self.html_results = self.html_results + "<td " + result_class + " width=\"30%\">" + msg + "</td></tr>"
            
        except Exception as e:
            #traceback.print_exc()
            logger.error("JSON schema doesn't match for url '{}'".format(url))
            logger.error("EXACT MISMATCH MSG OF RESPONSE BODY WITH JSON SCHEMA :\n{}\n\nRESPONSE BODY PARAMETERS:\n{},\nPRESENT AT: '{}' \nDOESN'T MATCHES WITH\nJSON SCHEMA PARAMETERS:\n{},\nPRESENT AT: '{}'"\
            .format(e.message,e.instance,e.path,e.schema,e.schema_path)) #if you want exact reason for schema mismatch.
            #HTML report data for failed validation
            msg="FAIL: JSON schema doesn't matches for this URI because of the reason : {}".format(e.message)
            result_class = "class=\"fail center\""
            self.html_results = self.html_results + "<td " + result_class + " width=\"30%\">" + msg + "</td></tr>"
    
    def get_openapi_from_redfish_org(self):
        """
        Method to get openapi.yaml schema file from openapi url of redfish organisation
        :return: Bool,string output for openapi schema file 
        """
        try:
            result=requests.get(self.config_dict["openapi_url"])
            if result.status_code!=200:
                raise Exception("Failed")
            try:    
                self.openapi_dict=yaml.load(result.text,Loader=yaml.FullLoader)
            except Exception as e:
                logger.error("error msg: {}".format(e))
                sys.exit(1)
        except:
            logger.error("Resource not found at {} with response code as:{}".format(self.config_dict["openapi_url"],result.status_code))
            sys.exit(1)
    
    def validate_uri(self,uri):
        """
        Method to validate passed URI with standard URIs present in openapi schema file
        :param uri: URI that to be validated
        :return: None
        """
        try:
            uri_match=False
            if len(self.openapi_dict) == 0:
                return
            self.html_results = self.html_results + "<tr>"
            self.html_results = self.html_results + "<td>" + uri + "</td>"
            for openapi_uri in self.openapi_dict["paths"]:
                # Check if the pattern in the path object matches the uri
                uri_pattern = "^" + re.sub( "{[A-Za-z0-9]+}", "[^/]+", openapi_uri ) + "$"
                if re.match( uri_pattern, uri ) is not None:
                    print("OpenApi specified uri:- "+uri_pattern)
                    uri_match=True
                    break
            if uri_match==False:
                logger.error("{} was not found in the openApi specification".format(uri))
                #HTML report data for failed validation
                msg="FAIL: URI is not present in schema"
                result_class = "class=\"fail center\""
                self.html_results = self.html_results + "<td " + result_class + " width=\"30%\">" + msg + "</td>"
                return
            logger.info("{}- This uri is validated against openApi specification".format(uri))
            #HTML report data for passed validation
            msg="PASS"
            result_class = "class=\"pass center\""
            self.html_results = self.html_results + "<td " + result_class + " width=\"30%\">" + msg + "</td>"
        except Exception as e:
            #traceback.print_exc()
            logger.error("error msg : {}".format(e))
          
    def get_base_url_response(self):
        """
        Method to get base url(/redfish/v1) response
        :return: Bool, JSON response body
        """
        try:
            base_url=self.config_dict["base_url"]
            bool_resp,response_base_url=self.redfish_response("get",base_url)
            if bool_resp==True:
                return True,response_base_url
            else:
                raise Exception("Failed")
        except:
            return False,None 
            
    def get_system_url(self,system_coll_url,system_id=None):
        """
        Method to get system_urls of passed system id
        :param system_coll_url: System collection url(/Systems)
        :param system_id: System id can be a particular id, or can be 'all'(to get all system urls),or None(in that case system url for 1st system is returned)
        :return: Bool,list of system urls
        """
        try:
            system=[]
            bool_resp1,response_system_url=self.redfish_response("get",system_coll_url)
            if bool_resp1==True:
                count=response_system_url.dict["Members@odata.count"]
                Members=response_system_url.dict["Members"]
                if not Members: #if Members value is empty
                    raise Exception("No members in response of system url")
                if system_id==None:
                    system_url=response_system_url.dict["Members"][0]["@odata.id"] #if system_id is not provided then 1st instance of system url is returned
                    system.append(system_url)
                    return True,system
                elif system_id=="all":
                    for i in range(count):
                        system_url=response_system_url.dict["Members"][i]["@odata.id"]
                        system.append(system_url)
                    return True,system
                else:
                    for system_x_url in Members:
                        system_url=system_x_url["@odata.id"]
                        if system_id in system_url:
                            system.append(system_url)
                            return True,system
                        else:
                            raise Exception("Failed")
            else:
                raise Exception("Failed")
        except Exception as e:
            logger.error("error msg: {}".format(e))
            return False,system
            
            
    def add_data(self,fxn_name):
        """
        Method to add heading in HTML report before every API start its functions.
        :param fxn_name: function name for the API called.
        :return: None 
        """
        self.html_results=self.html_results+"<tr><th class=\"titlerow\" colspan=3><b>{}</b></th></tr>".format(fxn_name)
        self.html_results=self.html_results+"<tr><th>URIs</th><th>URI validation</th><th>JSON schema validation</th></tr>"
        
 ############################################################################
    def get_all_bios_attributes(self)->(bool,list):
        """
        Method to get all bios attributes.
        :param system_id: System id can be a particular id, or can be "all"(to get all system urls),or None(in that case system url for 1st system is returned)
        :param bios_get: specifies "current" setting or "pending" setting for BIOS.
        :return: Bool,List of all BIOS attributes.
        """
        try:
            system_id=self.config_dict["system_id"]
            bios_get=self.config_dict["bios_get"]
            self.add_data(self.get_all_bios_attributes.__name__)
            attributes=[]
            bool_resp,response_base_url=self.get_base_url_response()
            if bool_resp==False:
                raise Exception("Failed")        
            system_url=response_base_url.dict["Systems"]["@odata.id"]
            bool_resp1,system=self.get_system_url(system_url,system_id)
            if bool_resp1==True:
                for i in range(len(system)):
                    system_x_url=system[i]
                    bool_respx,response_system_x_url=self.redfish_response("get",system_x_url)
                    if bool_respx==False:
                        raise Exception("Failed")  
                    bios_url=response_system_x_url.dict["Bios"]["@odata.id"]
                    bool_resp2,response_bios_url=self.redfish_response("get",bios_url)
                    if bool_resp2==True:   
                        if bios_get=="current":
                            attribute=response_bios_url.dict["Attributes"]
                            attributes.append(attribute)
                        elif bios_get=="pending":
                            pending_url=response_bios_url.dict["@Redfish.Settings"]["SettingsObject"]["@odata.id"]
                            bool_resp3,response_pending_url=self.redfish_response("get",pending_url)
                            if bool_resp3==True:
                                if "Attributes" in response_pending_url.dict:
                                    pending_attribute=response_pending_url.dict["Attributes"]
                                else:
                                    pending_attribute={}
                                current_attribute=response_bios_url.dict["Attributes"]
                                changed_attribute={}
                                for key in pending_attribute:
                                    if pending_attribute[key]!=current_attribute[key]:
                                        changed_attribute[key]=pending_attribute[key]
                                attributes.append(changed_attribute)
                            else:
                                raise Exception("Failed")
                        else:
                            raise Exception("Please input 'bios_get' as current or pending")
                    else:
                        raise Exception("Failed")
                return True,attributes
            else:
                raise Exception("System url list is empty.")
        except Exception as e:
            #traceback.print_exc()
            logger.error("error msg: {}".format(e))
            return False,attributes
                
    def get_power_state(self)->(bool,list):
        """
        Method to get power state of the system.
        :param system_id: System id can be a particular id, or can be "all"(to get all system urls),or None(in that case system url for 1st system is returned)
        :return: Bool,List of power states of the systems required.
        """
        try:
            system_id=self.config_dict["system_id"]
            self.add_data(self.get_power_state.__name__)
            power_details=[]
            bool_resp,response_base_url=self.get_base_url_response()
            if bool_resp==False:
                raise Exception("Failed")            
            system_url=response_base_url.dict["Systems"]["@odata.id"]
            bool_resp1,system=self.get_system_url(system_url,system_id)
            if bool_resp1==True:
                for i in range(len(system)):
                    system_x_url=system[i]
                    bool_resp2,response_system_x_url=self.redfish_response("get",system_x_url)
                    if bool_resp2==True:
                        power_state={}
                        power_state["SystemUrl"]=system_x_url
                        power_state["PowerState"]=response_system_x_url.dict["PowerState"]
                        power_details.append(power_state)
                    else:
                        raise Exception("Failed")
                return True,power_details
            else:
                raise Exception("System url list is empty.")
        except Exception as e:
            #traceback.print_exc()
            logger.error("error msg: {}".format(e))
            return False,power_details
    def get_chassis_inventory(self)->(bool,list):
        """
        Method to get chassis inventory.
        :return: List of Chassis inventory. 
        """
        try:
            self.add_data(self.get_chassis_inventory.__name__)
            chassis_inv=[]
            bool_resp,response_base_url=self.get_base_url_response()
            if bool_resp==False:
                raise Exception("Failed")
            chassis_url=response_base_url.dict["Chassis"]["@odata.id"]
            bool_resp1,response_chassis_url=self.redfish_response("get",chassis_url)
            if bool_resp1==True:    
                count=response_chassis_url.dict["Members@odata.count"]
                for i in range(count):
                    chassis_x_url=response_chassis_url.dict["Members"][i]["@odata.id"]
                    bool_resp2,response_chassis_x_url=self.redfish_response("get",chassis_x_url)
                    if bool_resp2==True:   
                        chassis_x_inv=response_chassis_x_url.dict
                        for attr in ["@odata.type","ThermalSubsystem","PowerSubsystem","EnvironmentMetrics","Sensors","Controls","Thermal",\
                                "Thermal@Redfish.Deprecated","Thermal","Power@Redfish.Deprecated","Power","Links","@odata.id"]:
                            if attr in chassis_x_inv.keys():
                                del chassis_x_inv[attr]
                        chassis_inv.append(chassis_x_inv)
                    else:
                        raise Exception("Failed")
                return True,chassis_inv
            else:
                raise Exception("Failed")
        except Exception as e:
            #traceback.print_exc()
            logger.error("error msg: {}".format(e))
            return False,chassis_inv
            
    def get_bios_attribute(self)->(bool,list):
        """
        Method to get particular attribute of BIOS.
        :param system_id: System id can be a particular id, or can be "all"(to get all system urls),or None(in that case system url for 1st system is returned).
        :param attr_name: User specified BIOS attribute name.
        :return: Bool,Bios Attribute value.
        """
        try:
            system_id=self.config_dict["system_id"]
            attr_name=self.config_dict["attr_name"]
            self.add_data(self.get_bios_attribute.__name__)
            attr_list=[]
            bool_resp,response_base_url=self.get_base_url_response()
            if bool_resp==False:
                raise Exception("Failed")
            system_url=response_base_url.dict["Systems"]["@odata.id"]
            bool_resp1,system=self.get_system_url(system_url,system_id)
            if bool_resp1==True:
                for i in range(len(system)):
                    system_x_url=system[i]
                    bool_respx,response_system_x_url=self.redfish_response("get",system_x_url)
                    if bool_respx==False:
                        raise Exception("Failed")
                    bios_url=response_system_x_url.dict["Bios"]["@odata.id"]
                    bool_resp2,response_bios_url=self.redfish_response("get",bios_url)
                    if bool_resp2==True:   
                        attributes=response_bios_url.dict["Attributes"]
                        if attr_name in attributes.keys():
                            attr_dict={}
                            attr_dict[attr_name]=attributes[attr_name]
                            attr_list.append(attr_dict)
                        else:
                            raise Exception("attribute name not found in bios resource")
                    else:
                        raise Exception("Failed")
                return True,attr_list
            else:
                raise Exception("System url list is empty.")
        except Exception as e:
            #traceback.print_exc()
            logger.error("error msg: {}".format(e))
            return False,attr_list
    def get_temperatures_inventory(self)->(bool,list):
        """
        Method to get temperature inventory.
        :return: Bool,Temperature inventory.
        """
        try: 
            self.add_data(self.get_temperatures_inventory.__name__)
            bool_resp,response_base_url=self.get_base_url_response()
            if bool_resp==False:
                raise Exception("Failed")
            chassis_url=response_base_url.dict["Chassis"]["@odata.id"]
            bool_resp,response_chassis_url=self.redfish_response("get",chassis_url)
            if bool_resp==True:
                temp_inv=[]
                for members in response_chassis_url.dict["Members"]:
                    member_url=members["@odata.id"]
                    bool_resp2,member_response=self.redfish_response("get",member_url)
                    if bool_resp2==True:
                        #if chassis is not normal skip it
                        if "Thermal" not in member_response.dict:
                            continue 
                        if len(response_chassis_url.dict["Members"])>1 and ("Links" not in member_response.dict or "ComputerSystems" not in member_response.dict["Links"]):
                            continue
                        thermal_url=member_response.dict["Thermal"]["@odata.id"]
                        bool_resp3,response_thermal_url=self.redfish_response("get",thermal_url)
                        if bool_resp3==True:
                            temp_list=response_thermal_url.dict["Temperatures"]
                            for dic_item in temp_list:
                                temp_dic={}
                                for key in dic_item:
                                    if key not in ["@odata.id","RelatedItem"]:
                                        temp_dic[key]=dic_item[key]
                                temp_inv.append(temp_dic)
                        else:
                            raise Exception("Failed")
                    else:
                        raise Exception("Failed")
                return True,temp_inv
            else:
                raise Exception("Failed")
        except Exception as e:
            #traceback.print_exc()
            logger.error("error_msg: {}".format(e))
            return False,None
        
    def get_storage_inventory(self)->(bool,list):
        """
        Method to get storage inventory
        :param system_id: System id can be a particular id, or can be "all"(to get all system urls),or None(in that case system url for 1st system is returned).
        :return: Bool,list of storage controllers, drives and volumes.
        """
        try:
            system_id=self.config_dict["system_id"]
            self.add_data(self.get_storage_inventory.__name__)
            storage_details=[]
            bool_resp,response_base_url=self.get_base_url_response()
            if bool_resp==False:
                raise Exception("Failed")
            system_url=response_base_url.dict["Systems"]["@odata.id"]
            bool_resp1,system=self.get_system_url(system_url,system_id)
            if bool_resp1==True:
                for i in range(len(system)):
                    system_x_url=system[i]
                    bool_resp2,response_system_x_url=self.redfish_response("get",system_x_url)
                    if bool_resp2==True:
                        if "Storage" in response_system_x_url.dict:
                            storage_url=response_system_x_url.dict["Storage"]["@odata.id"]
                        else:
                            storage_url=response_system_x_url.dict["SimpleStorage"]["@odata.id"]
                        bool_resp3,response_storage_url=self.redfish_response("get",storage_url)
                        if bool_resp3==True:
                            for i in range(0,len(response_storage_url.dict["Members"])):
                                storage_i_url=response_storage_url.dict["Members"][i]["@odata.id"]
                                bool_resp4,response_storage_i_url=self.redfish_response("get",storage_i_url)
                                if bool_resp4==True:
                                    storage={}
                                    storage["Id"]=response_storage_i_url.dict["Id"]
                                    storage["Name"]=response_storage_i_url.dict["Name"]
                                    drives_list=[]
                                    if "Drives" in response_storage_i_url.dict:
                                        for member in response_storage_i_url.dict["Drives"]:
                                            drive_inv={}
                                            drive_url=member["@odata.id"]
                                            bool_resp5,response_drive_url=self.redfish_response("get",drive_url)
                                            if bool_resp5==True:
                                                for key in response_drive_url.dict:
                                                    if key not in ["Description","@odata.context","@odata.id","@odata.id","@odata.type","Links","Actions","RelatedItem"]:
                                                        drive_inv[key]=response_drive_url.dict[key]
                                                drives_list.append(drive_inv)
                                            else:
                                                raise Exception("Failed")    
                                    storage["Devices"]=drives_list
                                    volumes_list=[]
                                    if "Volumes" in response_storage_i_url.dict:
                                        volumes_url=response_storage_i_url.dict["Volumes"]["@odata.id"]
                                        bool_resp6,response_volumes_url=self.redfish_response("get",volumes_url)
                                        if bool_resp6==True:
                                            for member in response_volumes_url.dict["Members"]:
                                                vol_inv={}
                                                vol_url=member["@odata.id"]
                                                bool_resp7,response_vol_url=self.redfish_response("get",vol_url)
                                                if bool_resp7==True:
                                                    for key in response_vol_url.dict:
                                                        if key not in ["Description","@odata.context","@odata.id","@odata.id","@odata.type","Links",\
                                                        "Actions","RelatedItem"]:
                                                            vol_inv[key]=response_vol_url.dict[key]
                                                    volumes_list.append(vol_inv)
                                                else:
                                                    raise Exception("Failed")
                                        else:
                                            raise Exception("Failed")
                                    storage["Volumes"]=volumes_list
                                    storageControllerCount=response_storage_i_url.dict["StorageControllers@odata.count"]
                                    stoConList=[]
                                    for i in range(0,storageControllerCount):
                                        con_dict={}
                                        for key in response_storage_i_url.dict["StorageControllers"][i]:
                                            if key not in ["Description","@odata.context","@odata.id","@odata.id","@odata.type","Links","Actions","RelatedItem"]:
                                                con_dict[key]=response_storage_i_url.dict["StorageControllers"][i][key]
                                        stoConList.append(con_dict)
                                    storage["Storage Controllers"]=stoConList                                    
                                    storage_details.append(storage)
                                else:
                                    raise Exception("Failed")
                        else:
                            raise Exception("Failed")
                    else:
                        raise Exception("Failed")
                return True,storage_details
            else:
                raise Exception("System url list is empty.")
        except Exception as e:
            ##traceback.print_exc()
            logger.error("error_msg: {}".format(e))
            return False,storage_details
        
    '''def set_power_limit(self,isenable,power_limit):
        isenable=bool(isenable)
        try:
            power_url=self.config_dict["power_url"]
            bool_resp1,response_power_url=self.redfish_response("get",power_url)
            if bool_resp1==True:
                #validating json schema
                if not self.validate_json(power_url,response_power_url):
                    raise Exception("Failed")
                if "@odata.etag" in response_power_url.dict:
                    etag=response_power_url.dict["@odata.etag"]
                else:
                    etag=""
                headers={"If-Match":etag}
                limit_attr=response_power_url.dict["PowerControl"][0]["PowerLimit"]#will check if power limit attribute is present or not
                if isenable is True:
                    body_parameter={"PowerControl":[{"PowerLimit":{"LimitInWatts":power_limit}}]}
                else:
                    body_parameter={"PowerControl":[{"PowerLimit":{"LimitInWatts":None}}]}
                bool_resp2,response_patch_url=self.redfish_response("patch",power_url,body_parameter,headers)
                if bool_resp2==True:
                    return True,response_patch_url
                else:
                    raise Exception("Failed")
            else:
                raise Exception("Failed")
        except Exception as e:
            #traceback.print_exc()
            logger.error("error msg: {}".format(e))
            return False,None'''
        
    def set_reset_type(self):
        """
        Method to set reset type of specified system.
        :param system_id: System id can be a particular id, or can be "all"(to get all system urls),or None(in that case system url for 1st system is returned).
        :param reset_typ: Power state of system( i.e. can be from system reset allowable values- ForceOff,On etc.)
        :return: Bool,response body for post request.
        """
        try:
            system_id=self.config_dict["system_id"]
            reset_typ=self.config_dict["reset_typ"]
            self.add_data(self.set_reset_type.__name__)
            bool_resp,response_base_url=self.get_base_url_response()
            if bool_resp==False:
                raise Exception("Failed")            
            system_url=response_base_url.dict["Systems"]["@odata.id"]
            bool_resp1,system=self.get_system_url(system_url,system_id)
            if bool_resp1==True:
                for i in range(len(system)):
                    system_x_url=system[i]
                    bool_respx,response_system_x_url=self.redfish_response("get",system_x_url)
                    if bool_respx==False:
                        raise Exception("Failed")
                    # Find the Reset Action target URL
                    target_url=response_system_x_url.dict["Actions"]["#ComputerSystem.Reset"]["target"]
                    # Prepare POST body
                    post_body = {"ResetType": reset_typ}
                    # POST Reset Action
                    bool_resp2,result=self.redfish_response("post",target_url,post_body)
                    if bool_resp2!=True:
                        raise Exception("Failed")
                return True,result
            else:
                raise Exception("System url list is empty.")
        except Exception as e:
            #traceback.print_exc()
            logger.error("error msg: {}".format(e))
            return False,None
        
    def set_network_protocol(self):
        """
        Method to set network protocol(i.e to enable or disable a BMC service and also to change port numbers of those services).
        :param service: service name supported by BMC(ex:- "HTTPS","SSH","Telnet","SNMP" etc.)
        :param prot_enabled: either "0" for disable, or "1" for enabling.
        :param port: port number to be assigned for protocol passed.
        :return: Bool, response body for post request.
        """
        try:
            service=self.config_dict["service"]
            prot_enabled=self.config_dict["prot_enabled"]
            port=self.config_dict["port"]
            self.add_data(self.set_network_protocol.__name__)
            bool_resp,response_base_url=self.get_base_url_response()
            if bool_resp==False:
                raise Exception("Failed") 
            managers_url=response_base_url.dict["Managers"]["@odata.id"]
            bool_respx,response_managers_url=self.redfish_response("get",managers_url)
            if bool_respx==False:
                raise Exception("Failed")
            for bmc in response_managers_url.dict["Members"]:
                bmc_url=bmc["@odata.id"]
                bool_respy,response_bmc_url=self.redfish_response("get",bmc_url)
                if bool_respy==False:
                    raise Exception("Failed")
                network_protocol_url=response_bmc_url["NetworkProtocol"]["@odata.id"]
                bool_resp1,response_prot_url=self.redfish_response("get",network_protocol_url)
                if bool_resp1==True:
                    if "@odata.etag" in response_prot_url.dict:
                        etag=response_prot_url.dict["@odata.etag"]
                    else:
                        etag=""
                    headers={"If-Match":etag,'Content-Type': 'application/json'}
                    if service in ["IPMI","SSDP","VirtualMedia"]:
                        body_parameter=json.dumps({service:{"ProtocolEnabled":bool(prot_enabled)}})
                    elif service in ["HTTP","HTTPS","KVMIP","SNMP","SSH","Telnet"]:
                        body_parameter={service:{"ProtocolEnabled":bool(prot_enabled),"Port":int(port)}}
                    else:
                        raise Exception("Please check BMC service name.")
                    bool_resp2,result=self.redfish_response("patch",network_protocol_url,body=body_parameter,headers=headers)
                    if bool_resp2==True:
                        print(self.redfish_response("get",network_protocol_url)[1].dict[service])
                    else:
                        raise Exception("Failed")
                else:
                    raise Exception("Failed")
            return True,result
        except Exception as e:
            #traceback.print_exc()
            logger.error("error msg= {}".format(e))
            return False,None
    
    def add_event_subscription(self,dest,subs_type="Event",context="",protocol="Redfish"):
        """
        Method to create subscription for Redfish service to sen event to subscriber.
        :param dest: URI to the destination where events will be sent.
        :param subs_type: subscriber event format type.
        :param context: client suppplied context for event.
        :param protocol: protocol of destination.
        :return: Bool, response body for post request for adding subscriptions.
        """
        try:
            dest=self.config_dict["dest"]
            subs_type=self.config_dict["subs_type"]
            context=self.config_dict["context"]
            protocol=self.config_dict["protocol"]
            self.add_data(self.add_event_subscription.__name__)
            bool_resp,response_base_url=self.get_base_url_response()
            if bool_resp==False:
                raise Exception("Failed")
            event_url=response_base_url.dict["EventService"]["@odata.id"]
            bool_resp1,response_event_url=self.redfish_response("get",event_url)
            if bool_resp1==True:
                event_service_version = 130 #default version v1_3_0
                event_service_type = response_event_url.dict["@odata.type"]
                event_service_type = event_service_type.split('.')[-2]
                if event_service_type.startswith('v'):
                    event_service_version = int(event_service_type.replace('v','').replace('_',''))
            #print(event_service_version)
            subs_url=response_event_url.dict["Subscriptions"]["@odata.id"]
            bool_resp2,response_subs_url=self.redfish_response("get",subs_url)
            if bool_resp2==True:
                headers={"Content-Type":"application/json"}
                if event_service_version >= 160 and protocol == 'SMTP':
                    if '@' not in dest:
                        raise Exception("Mail address {} is incorrect, please correct it first".format(dest))
                    parameter = {
                                "Destination": "mailto:{}".format(dest),
                                "Protocol": protocol
                                }
                elif event_service_version >= 160 and protocol == 'SNMPv1':
                    parameter = {
                                "Destination": "snmp://{}".format(dest),
                                "Protocol": protocol
                                }
                elif event_service_version >= 160 and protocol == 'SNMPv3':
                    if '@' not in dest:
                        raise Exception("SNMPv3 address {} is invalid, please correct it first".format(dest))
                    parameter = {
                                "Destination": "snmp://{}".format(dest),
                                "Protocol": protocol
                                }
                elif event_service_version >= 160 and protocol == 'Redfish':
                    if subs_type == 'MetricReport':
                        parameter = {
                                 "Destination": dest,
                                 "Protocol": "Redfish",
                                 "SubscriptionType": "RedfishEvent",
                                 "EventFormatType": "MetricReport",
                                }
                    else:
                        parameter = {
                                 "Destination": dest,
                                 "Protocol": "Redfish",
                                 "SubscriptionType": "RedfishEvent",
                                 "EventFormatType": "Event",
                                }
                    if context is not None and context != '':
                        parameter['Context'] = context

                elif event_service_version < 160 and protocol != "Redfish":
                    raise Exception("Target server only supports redfish protocol.")

                elif event_service_version >= 130:
                    if "@Redfish.CollectionCapabilities" in response_subs_url.dict:
                        parameter = {
                                 "Destination":dest,
                                 "Protocol":"Redfish"
                                }
                    else:
                        parameter = {
                                 "Destination":dest,
                                 "Protocol":"Redfish"
                                }
                    if context is not None and context != '':
                        parameter['Context'] = context
                else:
                    parameter = {
                             "Destination":dest,
                             "Protocol":"Redfish"
                            }
                    if context is not None and context != '':
                        parameter['Context'] = context
                    if subs_type == 'Event':
                        eventtypes = ['StatusChange', 'ResourceUpdated', 'ResourceAdded', 'ResourceRemoved', 'Alert']
                    else:
                        eventtypes = ['MetricReport']
                    parameter['EventTypes'] = eventtypes
                bool_resp3,result=self.redfish_response("post",subs_url,body=parameter,headers=headers)
                if bool_resp3==True:
                    #printing updated subscriptions details:-
                    print(self.redfish_response("get",subs_url)[1])
                    for member in response_subs_url.dict["Members"]:
                        subs_member_url=member["@odata.id"]
                        bool_resp,response_subs_member_url=self.redfish_response("get",subs_member_url)
                        if bool_resp==True:
                            print(response_subs_member_url.text)
                    return True,result
                else:
                    raise Exception("Failed")
            else:
                raise Exception("Failed")
        except Exception as e:
            #traceback.print_exc()
            logger.error("error msg:{}".format(e))
            return False,None
        
    def delete_event_subscription(self):
        """
        Method to delete first found event subscription for passed destination.
        :param dest: destination for a subscribed event.
        :return: Bool, response body for delete request. 
        """
        try:
            dest=self.config_dict["ddest"]
            self.add_data(self.delete_event_subscription.__name__)
            bool_resp,response_base_url=self.get_base_url_response()
            if bool_resp==False:
                raise Exception("Failed")
            event_url=response_base_url.dict["EventService"]["@odata.id"]
            bool_respx,response_event_url=self.redfish_response("get",event_url)
            if bool_respx==False:
                raise Exception("Failed")
            subs_url=response_event_url.dict["Subscriptions"]["@odata.id"]
            bool_resp1,response_subs_url=self.redfish_response("get",subs_url)
            if bool_resp1==True:
                headers={"Content-Type":"application/json"}
                delete_url=""
                for item in response_subs_url.dict["Members"]:
                    tmp_url=item["@odata.id"]
                    bool_resp2,response_tmp_url=self.redfish_response("get",tmp_url)
                    if bool_resp2==True:
                        if dest in response_tmp_url.dict["Destination"]:
                            delete_url=tmp_url
                            break #delete first found destination
                if delete_url=="":
                    raise Exception("destination provided is not present")
                else:
                    bool_resp3,result=self.redfish_response("delete",delete_url)
                    if bool_resp3==True:
                        print(self.redfish_response("get",subs_url)[1])
                        return True,result
                    else:
                        raise Exception("Failed")
            else:
                raise Exception("Failed")
        except Exception as e:
            #traceback.print_exc()
            logger.error("error msg:{}".format(e))
            return False,None 
                     
    def post_test_event(self):
        """
        Method to send test event to subscribers.
        :param event_id: ID of event to be added.
        :param msg: event message text of event to be added.
        :param severity: severity of event.
        :return: Bool, response body for post request for sending test events
        """
        try:
            event_id=self.config_dict["event_id"]
            msg=self.config_dict["msg"]
            severity=self.config_dict["severity"]
            self.add_data(self.post_test_event.__name__)
            sev_list=["OK","Warning","Critical"]
            if severity not in sev_list:
                raise Exception("Please check as severity input as its scope is in 'OK,Warning,Critical' only.")
            bool_resp,response_base_url=self.get_base_url_response()
            if bool_resp==False:
                raise Exception("Failed")
            event_url=response_base_url.dict["EventService"]["@odata.id"]
            bool_resp1,response_event_url=self.redfish_response("get",event_url)
            if bool_resp1==True:
                event_service_version = 130 #default version v1_3_0
                event_service_type = response_event_url.dict["@odata.type"]
                event_service_type = event_service_type.split('.')[-2]
                if event_service_type.startswith('v'):
                    event_service_version = int(event_service_type.replace('v','').replace('_',''))
                event_target_url=response_event_url.dict["Actions"]["#EventService.SubmitTestEvent"]["target"]
                timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00')
                headers = {"Content-Type": "application/json"}
                payload = {}
                action_info_url=response_event_url.dict["Actions"]["#EventService.SubmitTestEvent"]["@Redfish.ActionInfo"]     ##############This parameter is not present in dell's server thus this API will skip this part for dell's server and will go into elif condition.
                bool_resp2,response_action_info_url=self.redfish_response("get",action_info_url)
                if bool_resp2==True and ("Parameters" in response_action_info_url.dict):
                    for parameter in response_action_info_url.dict["Parameters"]:
                        if ("Required" in parameter) and parameter["Required"]:
                            if parameter["Name"] == "EventId":
                                payload["EventId"] = event_id
                            elif parameter["Name"] == "EventType":
                                payload["EventType"] = "Alert"
                            elif parameter["Name"] == "EventTimestamp":
                                payload["EventTimestamp"] = timestamp
                            elif parameter["Name"] == "Message":
                                payload["Message"] = msg
                            elif parameter["Name"] == "MessageArgs":
                                payload["MessageArgs"] = []
                            elif parameter["Name"] == "MessageId":
                                payload["MessageId"] = "Created"
                            elif parameter["Name"] == "Severity":
                                payload["Severity"] = severity
                            elif parameter["Name"] == "OriginOfCondition":
                                payload["OriginOfCondition"] = event_url
                elif event_service_version >= 160:
                    payload["EventId"] = event_id
                    payload["EventTimestamp"] = timestamp
                    payload["Message"] = msg
                    payload["MessageArgs"] = []
                    payload["MessageId"] = "Created"
                    payload["OriginOfCondition"] = event_url
                elif event_service_version >= 130:
                    payload["EventId"] = event_id
                    payload["EventTimestamp"] = timestamp
                    payload["Message"] = msg
                    payload["MessageArgs"] = []
                    payload["MessageId"] = "Created"
                    payload["Severity"] = severity
                    payload["OriginOfCondition"] = event_url
                elif event_service_version >= 106:
                    payload["EventId"] = event_id
                    payload["EventType"] = "Alert"
                    payload["EventTimestamp"] = timestamp
                    payload["Message"] = msg
                    payload["MessageArgs"] = []
                    payload["MessageId"] = "Created"
                    payload["Severity"] = severity
                    payload["OriginOfCondition"] = event_url
                else:
                    payload["EventId"] = event_id
                    payload["EventType"] = "Alert"
                    payload["EventTimestamp"] = timestamp
                    payload["Message"] = msg
                    payload["MessageArgs"] = []
                    payload["MessageId"] = "Created"
                    payload["Severity"] = severity
                print(payload)
                print(headers) 
                bool_resp3,result=self.redfish_response("post",event_target_url,body=payload,headers=headers)
                if bool_resp3==True:
                    return True,result
                else:
                    raise Exception("Failed")
            else:
                raise Exception("Failed")
        except Exception as e:
            traceback.print_exc()
            logger.error("error msg: {}".format(e))
            return False,None

    def get_fans_inventory(self):
        """
        Method to get fans inventory from chassis.
        :return: Bool,list of fans inventory.
        """
        try:
            self.add_data(self.get_fans_inventory.__name__)
            bool_resp,response_base_url=self.get_base_url_response()
            if bool_resp==False:
                raise Exception("Failed") 
            chassis_url=response_base_url["Chassis"]["@odata.id"]
            bool_resp1,response_chassis_url=self.redfish_response("get",chassis_url)
            if bool_resp1==True:
                fans_inv=[]
                for members in response_chassis_url.dict["Members"]:
                    member_url=members["@odata.id"]
                    bool_resp2,member_response=self.redfish_response("get",member_url)
                    if bool_resp2==True:
                        #if chassis is not normal skip it
                        if "Thermal" not in member_response.dict:
                            continue 
                        if len(response_chassis_url.dict["Members"])>1 and ("Links" not in member_response.dict or "ComputerSystems" not in member_response.dict["Links"]):
                            continue
                        thermal_url=member_response.dict["Thermal"]["@odata.id"]
                        bool_resp3,response_thermal_url=self.redfish_response("get",thermal_url)
                        if bool_resp3==True:
                            fans_list=response_thermal_url.dict["Fans"]
                            for dic_item in fans_list:
                                fans_dic={}
                                for key in dic_item:
                                    if key not in ["@odata.id","RelatedItem"]:
                                        fans_dic[key]=dic_item[key]
                                fans_inv.append(fans_dic)
                        else:
                            raise Exception("Failed")
                    else:
                        raise Exception("Failed")
                return True,fans_inv
            else:
                raise Exception("Failed")
        except Exception as e:
            #traceback.print_exc()
            logger.error("error_msg: {}".format(e))
            return False,None

    def reset_manager(self):
        """
        Method to restart BMC.
        :param manager_reset_type: reset type from redfish allowable values of BMC reset type.
        :return: Bool,response body for post request to restart BMC.
        """
        try:
            manager_reset_type=self.config_dict["manager_reset_type"]
            self.add_data(self.reset_manager.__name__)
            bool_resp,response_base_url=self.get_base_url_response()
            if bool_resp==False:
                raise Exception("Failed") 
            managers_url=response_base_url.dict["Managers"]["@odata.id"]
            bool_respx,response_managers_url=self.redfish_response("get",managers_url)
            if bool_respx==False:
                raise Exception("Failed")
            for bmc in response_managers_url.dict["Members"]:
                bmc_url=bmc["@odata.id"]
                bool_resp1,response_bmc_url=self.redfish_response("get",bmc_url)
                if bool_resp1==True:
                    reset_bmc_url=response_bmc_url.dict["Actions"]["#Manager.Reset"]["target"]
                    body={"ResetType":manager_reset_type}
                    headers={"Content-Type":"application/json"}
                    bool_resp2,response_manager_reset=self.redfish_response("post",reset_bmc_url,body,headers)
                    if bool_resp2==False:
                        raise Exception("Failed")
                else:
                    raise Exception("Failed")
            return True,response_manager_reset
        except Exception as e:
            logger.error("error msg: {}".format(e))
            return False
            
    def get_psu_inventory(self):
        """
        Method to get power supply unit inventory.
        :return: Bool, list of psu inventory.
        """
        try:
            self.add_data(self.get_psu_inventory.__name__)
            psu_inv_list=[]
            bool_resp,response_base_url=self.get_base_url_response()
            if bool_resp==False:
                raise Exception("Failed")
            chassis_url=response_base_url.dict["Chassis"]["@odata.id"]
            bool_resp1,response_chassis_url=self.redfish_response("get",chassis_url)
            if bool_resp1==True:
                for x in response_chassis_url.dict["Members"]:
                    chassis_x_url=x["@odata.id"]
                    bool_resp2,response_chassis_x_url=self.redfish_response("get",chassis_x_url)
                    if bool_resp2==True:
                        if "Power" not in response_chassis_x_url.dict:
                            continue
                        power_url=response_chassis_x_url.dict["Power"]["@odata.id"]
                        bool_respx,response_power_url=self.redfish_response("get",power_url)
                        if bool_respx==False:
                            raise Exception("Failed")
                        else:
                            if "PowerSupplies" not in response_power_url.dict:
                                continue
                            for x in response_power_url.dict["PowerSupplies"]:
                                psu_dict={}
                                for key in x:
                                    if key in ["Name","SerialNumber","PowerOutputWatts","EfficiencyPercent","LineInputVoltage","PartNumber",\
                                            "FirmwareVersion","PowerCapacityWatts","PowerInputWatts","Model","PowerSupplyType","Status","Manufacturer",\
                                            "HotPluggable","LastPowerOutputWatts","InputRanges","LineInputVoltageType","Location","SparePartNumber"]:
                                        psu_dict[key]=x[key]
                                psu_inv_list.append(psu_dict)
                    else:
                        raise Exception("Failed")
                return True,psu_inv_list
            else:
                raise Exception("Failed")
        except Exception as e:
            traceback.print_exc()
            logger.error("error msg: {}".format(e))
            return False
    
    def get_bmc_logs(self):
        """
        Method to get BMC logs(i.e system event logs, lifecycle logs etc.)
        :return: Bool, List of logs.
        """
        try:
          self.add_data(self.get_bmc_logs.__name__)
          logs_list=[]
          bool_resp,response_base_url=self.get_base_url_response()
          if bool_resp==False:
            raise Exception("Failed") 
          managers_url=response_base_url.dict["Managers"]["@odata.id"]
          bool_respx,response_managers_url=self.redfish_response("get",managers_url)
          if bool_respx==False:
            raise Exception("Failed")
          for bmc in response_managers_url.dict["Members"]:
            bmc_url=bmc["@odata.id"]
            bool_resp1,response_bmc_url=self.redfish_response("get",bmc_url)
            if bool_resp1==True:
                if "LogServices" in response_bmc_url.dict:
                    log_services_url=response_bmc_url.dict["LogServices"]["@odata.id"]
                    bool_resp2,response_log_services_url=self.redfish_response("get",log_services_url)
                    if bool_resp2==True:
                        for x in response_log_services_url.dict["Members"]:
                            log_x_url=x["@odata.id"]
                            bool_resp3,response_log_x_url=self.redfish_response("get",log_x_url)
                            if bool_resp3==True:
                                if "Entries" not in response_log_x_url.dict:
                                    continue
                                entries_url=response_log_x_url.dict["Entries"]["@odata.id"]
                                bool_resp4,response_entries_url=self.redfish_response("get",entries_url)
                                if bool_resp4==True:
                                    for log in response_entries_url.dict["Members"]:
                                        log_dict={}
                                        for key in ["Id","Name","Created","Message","MessageId","Severity","EntryCode","EntryType","EventId","SensorNumber"\
                                            ,"SensorType"]:
                                            if key in log:
                                                log_dict[key]=log[key]
                                        logs_list.append(log_dict)
                                else:
                                    raise Exception("Failed")
                            else:
                                raise Exception("Failed")
                    else:
                        raise Exception("Failed") 
                else:
                    raise Exception("Log service is not available")
            else:
                raise Exception("Failed")
          return True,logs_list
        except Exception as e:
            #traceback.print_exc()
            logger.error("error msg: {}".format(e))
            return False
'''
if __name__=="__main__":
    #Creating object:
    ob=RedfishApi()
    bool_resp,result=ob.get_all_bios_attributes()
    if bool_resp==True:
        print(json.dumps(result,indent=2))
        
    bool_resp,result=ob.get_power_state()
    if bool_resp==True:
        print(json.dumps(result,indent=2))
  
    """bool_resp,result=ob.get_chassis_inventory()
    if bool_resp==True:
        print(json.dumps(result,indent=2))
    
    bool_resp,result=ob.get_temperatures_inventory()
    if bool_resp==True:
        print(json.dumps(result,indent=2))
    
    bool_resp,result=ob.get_storage_inventory()
    if bool_resp==True:
        print(json.dumps(result,indent=2))
    
    bool_resp,result=ob.get_bmc_logs()
    if bool_resp==True:
        print(json.dumps(result,indent=2))
        
    bool_resp,result=ob.get_psu_inventory()
    if bool_resp==True:
        print(json.dumps(result,indent=2))"""  
   
    #All test cases:
    """
    bool_resp,result=ob.get_bmc_logs()
    if bool_resp==True:
        print(json.dumps(result,indent=2))
        
    bool_resp,result=ob.get_psu_inventory()
    if bool_resp==True:
        print(json.dumps(result,indent=2))
        
    bool_resp,result=ob.get_fans_inventory()
    if bool_resp==True:
        print(json.dumps(result,indent=2))
        
    bool_resp,result=ob.reset_manager()
    if bool_resp==True:
        print("Power state setted successfully with response code as {}".format(result.status))
    
    bool_resp,result=ob.delete_event_subscription()
    if bool_resp==True:
        print("Passed with status code as: {}".format(result.status))

    bool_resp,result=ob.add_event_subscription()
    if bool_resp==True:
        print(result.status)
    
    bool_resp,result=ob.set_network_protocol()
    if bool_resp==True:
        print(result.status)
    
    bool_resp,result=ob.post_test_event()
    if bool_resp==True:
        print(result.status)
    
    bool_resp,result=ob.get_all_bios_attributes()
    if bool_resp==True:
        print(json.dumps(result,indent=2))
    
    bool_resp,result=ob.get_power_state()
    if bool_resp==True:
        print(json.dumps(result,indent=2))
    
    bool_resp,result=ob.get_bios_attribute()
    if bool_resp==True:
        print(json.dumps(result,indent=2))
    
    bool_resp,result=ob.get_chassis_inventory()
    if bool_resp==True:
        print(json.dumps(result,indent=2))
    
    bool_resp,result=ob.get_temperatures_inventory()
    if bool_resp==True:
        print(json.dumps(result,indent=2))
    
    bool_resp,result=ob.get_storage_inventory()
    if bool_resp==True:
        print(json.dumps(result,indent=2))
    
    bool_resp,result=ob.set_power_limit(isenable,power_limit)
    if bool_resp==True:
        print("Power limit setted successfully with response code as {}".format(result.status))
    
    bool_resp,result=ob.set_reset_type()
    if bool_resp==True:
        print("Power state setted successfully with response code as {}".format(result.status))
    
    """
    ob.generate_report()
'''
