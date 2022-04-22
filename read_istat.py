import socket 
import pprint
import json
import re
import redcap as rc
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import board
import digitalio
from datetime import datetime

#Output LED for if currently uploading
uploadLed = digitalio.DigitalInOut(board.D21)
uploadLed.direction = digitalio.Direction.OUTPUT
uploadLed.value = False

pp = pprint.PrettyPrinter(indent=4)

def pretty_print(xmlDoc):
    print(BeautifulSoup(ET.tostring(xmlDoc), 'xml').prettify())

def get_msg(cs):
    #Define parsing variables
    curInd = -1
    startInd = None
    startTag = None
    endTag = None
    wholeMsg = ""

    while True:
        #REad one byte at a time
        byte = cs.recv(1).decode("utf-8", errors='ignore')
        curInd = curInd + 1
        wholeMsg = wholeMsg + byte
        
        #Find start of first tag
        if(startTag == None and startInd == None and byte == "<"):
            startInd = curInd
        #Find end of first tag
        if(startTag == None and startInd != None and byte == ">"):
            startTag = wholeMsg[startInd:curInd+1]
            endTag = startTag[:1] + '/' + startTag[1:]
        
        #End of message when close tag found
        if(startTag != None and endTag != None and wholeMsg.find(endTag) > -1):
            parsedMsg = ET.fromstring(wholeMsg)
            return(parsedMsg)

def get_hdr(parMsg):
    for child in parMsg:
        if(child.tag == "HDR"):
            return(ET.tostring(child))
    return None

def get_device(parMsg):
    device_id = None
    vendor_id = None
    model_id = None
    serial_id = None
    for child in parMsg:
        if(child.tag == "DEV"):
            for children in child:
                if(children.tag == "DEV.device_id"):
                    device_id = children.get("V")
                if(children.tag == "DEV.vendor_id"):
                    vendor_id = children.get("V")
                if(children.tag == "DEV.model_id"):
                    model_id = children.get("V")
                if(children.tag == "DEV.serial_id"):
                    serial_id = children.get("V")

    return(vendor_id, model_id, device_id, serial_id)

def get_obs(cs, hdr):
    msg = "<REQ.R01>"
    msg = msg + hdr.decode("utf-8")
    msg = msg + "<REQ><REQ.request_cd V=\"ROBS\"/></REQ>"
    msg = msg + "</REQ.R01>"
    if(cs.sendall(msg.encode("utf-8")) == None):
        robs = get_msg(cs)
        return(robs)
    else: 
        print("REQ.R01 error")
        return None

def extract_obs(observation):
    data = []
    rgt_data = {}
    patient_id = None
    obs_date = None
    temp_correct = False
    pt_temp = None
    for child in observation[1]:
        if(child.tag == "SVC.observation_dttm"):
            obs_date = child.get("V")
        elif(child.tag == "PT"):
            for children in child:
                if(children.tag == "PT.patient_id"):
                    patient_id = children.get("V")
                elif(children.tag == "OBS"):
                    obs_type = None
                    obs_value = None
                    obs_unit = None
                    obs_nte = None
                    for childrens in children:
                        if(childrens.tag == "OBS.observation_id"):
                            obs_type = childrens.get("V")
                        elif(childrens.tag == "OBS.value"):
                            obs_value = childrens.get("V")
                            obs_unit = childrens.get("U")
                        elif(childrens.tag == "NTE"):
                            for childrenss in childrens:
                                if(childrenss.tag == "NTE.text"):
                                    if(re.match('^\d+(\.\d+)?$',childrenss.get("V")) is not None):
                                        obs_nte = float(childrenss.get("V"))
                    data.append([obs_type, obs_value, obs_unit, obs_nte])
        elif(child.tag == "RSN"):
            for children in child:
                if(children.tag == "RSN.apoc_prompt"):
                    if(children.get("V") == "PT Temp F"):
                        temp_correct = True
                elif(children.tag == "RSN.apoc_content"):
                    pt_temp = children.get("V")
        elif(child.tag == "RGT"):
            for children in child:
                if(children.tag == "RGT.name"):
                    rgt_data["name"] = children.get("V")
                elif(children.tag == "RGT.lot_number"):
                    rgt_data["lot_number"] = children.get("V")
                elif(children.tag == "RGT.expiration_date"):
                    rgt_data["expiration_date"] = children.get("V")

    dataout = []
    temp_append = None
    for datum in data:
        dataout.append({"name": patient_id, "datetime": obs_date, 
            "type": datum[0], "value": datum[1], "units": datum[2], 
            "note": datum[3]})

        #Get temp corrected values for CG4
        if(("CG8" in rgt_data["name"] or 
                "CG4" in rgt_data["name"]) and datum[3] != None):
            dataout[len(dataout) - 1]["type"] = "temp_" + dataout[len(dataout) - 1]["type"] 

    if(temp_correct):
        dataout.append({"name": patient_id, "datetime": obs_date, 
            "type": "temp", "value": pt_temp, 
            "units": "fahrenheit", "note": None})

    return ET.tostring(observation[0]), dataout, rgt_data

def parse_device_status(themsg):
    #Get the number of observations to sent
    unsentObs = None
    try:
        for child in themsg:
            if(child.tag == "DST"):
                for children in child:
                    if(children.tag == "DST.new_observations_qty"):
                        unsentObs = int(children.get("V"))
    except:
        unsentObs = 0

    return(unsentObs)

def ack(cs, hdr):
    #Extract the ctrl id from the header
    ctrlid = None
    parsedHDR = ET.fromstring(hdr)
    for child in parsedHDR:
        if(child.tag == "HDR.control_id"):
            ctrlid = child.get("V")
            break

    #Build the ack message
    msg = '<ACK.R01>'
    msg = msg + hdr.decode("utf-8")
    msg = msg+'<ACK>'
    msg = msg+'<ACK.type_cd V="AA" /><ACK.ack_control_id V="' + ctrlid + '" />'
    msg = msg+'</ACK>'
    msg = msg+'</ACK.R01>'

    if(cs.sendall(msg.encode('utf-8')) != None):
        print("ACK error")

def is_terminated(themsg):
    if(themsg.tag == "END.R01"):
        print(ET.tostring(themsg))
        reason = None
        for child in themsg:
            if(child.tag == "TRM"):
                for children in child:
                    if(children.tag == "TRM.reason_cd"):
                        reason = children.get("V")
        print("Terminated Connection, " + str(reason))
        return True
    return False

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.bind(('0.0.0.0', 8080))
serversocket.listen(1)

while True:
    try:
        #accept connections from outside
        (clientsocket, address) = serversocket.accept()
        uploadLed.value = True

        #Parse the hello message
        msg = get_msg(clientsocket)
        if(is_terminated(msg)): continue
        hdr = get_hdr(msg)
        vendor, model, device, serial = get_device(msg)
        ack(clientsocket, hdr)
        print("Ready to send results from:", vendor, model, device, serial)

        #Parse device status message
        msg = get_msg(clientsocket)
        if(is_terminated(msg)): continue
        hdr = get_hdr(msg) 
        ack(clientsocket, hdr)
        obs_to_send = parse_device_status(msg)
        print("Number of unsent records:", obs_to_send)

        #Get unsent observations
        for get_it in range(obs_to_send):
            #Request the next object
            obs = get_obs(clientsocket, hdr)
            if(is_terminated(obs)): break
            hdr, data, test_info = extract_obs(obs)

            #Build the test info struct yo post
            test_info["vendor"] = vendor
            test_info["model"] = model
            test_info["device"] = device
            test_info["serial"] = serial
            test_info["json_data"] = json.dumps(data)
            #pp.pprint(data)
         
            #Build the record for a given test type for posting
            dataoutput = {"name": data[0]["name"]}
            dataoutput["datetime"] = rc.parse_value("datetime", 
                                                        data[0]["datetime"])
            dataoutput["upload_datetime"] = rc.parse_value("upload_datetime", 
                                                        datetime.now())
            for item in data:
                dataoutput[rc.convert_colname(item["type"])] = rc.parse_value(item["type"],item["value"])
            pp.pprint(dataoutput)

            #Post the records to the appropiate table
            post_test_table = rc.post_redcap(dataoutput, 
                    rc.which_table(test_info["name"]))
            
            #Post the test metadata
            post_test_info = rc.post_redcap(test_info, 
                    rc.which_table("TEST_INFO"))
           
            #Print the results
            print("Sucessful Posting:", post_test_info, post_test_table)

            #Acknowlege the sucessfull posting
            if(post_test_info == 1 or post_test_table == 1):
                ack(clientsocket, hdr)

        #Close the socket connection
        clientsocket.close()
    except Exception as err:
        print("ERROR:", err)

    uploadLed.value = False

