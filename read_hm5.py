import socket 
import pprint
import json
import re
from datetime import datetime
import redcap as rc

def get_msg(cs):
    wholeMsg = ""

    while True:
        #Read one byte at a time
        byte = cs.recv(1).decode("utf-8", errors='ignore')
        wholeMsg = wholeMsg + byte
        if(wholeMsg[len(wholeMsg) - 1] == '\r'):
            wholeMsg = wholeMsg.strip('/r') + '\n'
            print(wholeMsg)

        if("OBX|40" in wholeMsg):
            while True:
                byte = cs.recv(1).decode("utf-8", errors='ignore')
                wholeMsg = wholeMsg + byte
                if(byte == '\r'):
                    wholeMsg = wholeMsg.strip('\r') + '\n'
                    try:
                        cs.recv(1)
                    except:
                        print("MESSAGE RECIEVED")

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

    print(test_info)
    print(datas)

    return(datas, test_info)

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.bind(('0.0.0.0', 8080))
serversocket.listen(1)

while True:
    #accept connections from outside
    (clientsocket, address) = serversocket.accept()
    clientsocket.settimeout(5)

    #Parse the hello message
    msg = get_msg(clientsocket)
    test_info, data = parse_obs(msg)

    #Close the socket connection
    clientsocket.sendall(b'THANKS')
    #clientsocket.close()

