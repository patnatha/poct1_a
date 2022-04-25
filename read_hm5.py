import socket 
import pprint
import json
import re
from datetime import datetime
import redcap as rc
import sys

def display_msg(wbc, upload_res):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("localhost", 34567))
        theMsg = {"WBC":wbc, "redcap":upload_res}
        s.sendall(str.encode(json.dumps(theMsg) + "\n"))
        s.close()
    except Exception as err:
        print("display_msg error:", err)

def get_msg(cs):
    wholeMsg = ""

    while True:
        #Read one byte at a time
        byte = cs.recv(1)
        byte = byte.decode("utf-8", errors='ignore')
        wholeMsg = wholeMsg + byte
        if(len(wholeMsg) > 0 and wholeMsg[len(wholeMsg) - 1] == '\n'):
            wholeMsg = wholeMsg.strip('\n').strip('\r') + '\n'
            print(wholeMsg)

        if("OBX|40" in wholeMsg):
            while True:
                byte = cs.recv(1).decode("utf-8", errors='ignore')
                wholeMsg = wholeMsg + byte
                if(byte == '\n'):
                    wholeMsg = wholeMsg.strip('\n').strip('\r') + '\n'
                    try:
                        cs.recv(1)
                    except:
                        print("MESSAGE RECIEVED")
                    print(wholeMsg)
                    return(wholeMsg)

def parse_obs(theMsg):
    patientID = None
    testID = None
    testDate = None
    version = None
    datas = {}
    for line in theMsg.split("\n"):
        if(re.search("OBX\|\d+\|TX\|", line) != None):
            parsedLine = (line.split("|"))
            if(len(parsedLine) > 6):
                datas[parsedLine[3]] = parsedLine[5]
        elif(re.search("PID\|\d+\|", line) != None):
            parsedLine = (line.split("|"))
            if(len(parsedLine) > 4):
                patientID = parsedLine[3]
        elif(re.search("MSH\|\^\~\\\&\|HM5", line) != None):
            parsedLine = line.split("|")
            if(len(parsedLine) > 12):
                version = parsedLine[11]
        elif(re.search("OBR\|1\|\|\|", line) != None):
            parsedLine = line.split("|")
            if(len(parsedLine) > 8):
                testID = parsedLine[4]
                testDate = datetime.strptime(parsedLine[7], "%Y%m%d%H%M%S")
    
    test_info = {}
    test_info["name"] = patientID
    test_info["test"] = testID
    test_info["datetime"] = testDate.strftime("%Y-%m-%d %H:%M:%S")
    test_info["version"] = version

    return(test_info, datas)

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.bind(('0.0.0.0', 8080))
serversocket.listen(1)

while True:
    try:
        #accept connections from outside
        (clientsocket, address) = serversocket.accept()
        clientsocket.settimeout(5)

        #Parse the hello message
        msg = get_msg(clientsocket)
        test_info, data = parse_obs(msg)

        #print(test_info)
        #print(data)

        #Build the test_info post data structure
        post_test_info = {"vendor": "abaxis", "model": "hm5", "serial": "360011240"}
        post_test_info["device"] = test_info["version"]
        post_test_info["name"] = test_info["test"]
        post_test_info["lot_number"] = None
        post_test_info["expiration_date"] = None
        data["datetime"] = test_info["datetime"]
        data["name"] = test_info["name"]
        post_test_info["json_data"] = json.dumps(data)

        post_test_table = rc.post_redcap(post_test_info, rc.which_table("TEST_INFO"))

        #Build the cbc post data structure
        datalist = ["name", "datetime", "wbc","lym","mon", "neu","eos","bas","lym%","mon%","neu%","eos%","bas%","rbc","hgb","hct","mcv","mch","mchc","rdwc","rdws","plt","mpv","pct","pdwc","pdws"]
        data_post = {}
        data_post["upload_datetime"] = rc.parse_value("upload_datetime", 
                                                         datetime.now())
        theWBC = None
        for item in data:
            if(item.lower() in datalist):
                data_post[item.lower().replace("%", "_percent")] = data[item]
            if(item.lower() == "wbc"):
                theWBC = data[item]
        #print(data_post)

        post_cbc = rc.post_redcap(data_post, rc.which_table("CBC"))

        #Print post results
        print("Posted Msg:", post_test_table, post_cbc)

        #Send a display message
        display_msg(theWBC, post_cbc)

        #Close the socket connection
        clientsocket.sendall(b'0')
        clientsocket.close()
    except Exception as err:
        print("ERROR:", err)

