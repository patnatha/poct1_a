import requests
import json
import sys
from datetime import datetime

postUrl = "https://redcap.wakehealth.edu/redcap/api/"
token_file = "/home/pi/Documents/poct1_a/token.auth"
labs_token = None
chem8_token = None
cg4_token = None
cbc_token = None

def load_tokens():
    global labs_token
    global chem8_token
    global cg4_token
    global cbc_token
    f = open(token_file)
    for line in f:
        parsed = (line.strip("\n").split(":"))
        if(len(parsed) == 2):
            #print(parsed)
            if(parsed[0] == 'labs'):
                labs_token = parsed[1]
            elif(parsed[0] == 'chem8'):
                chem8_token = parsed[1]
            elif(parsed[0] == 'cg4'):
                cg4_token = parsed[1]
            elif(parsed[0] == "cbc"):
                cbc_token = parsed[1]
    f.close()
load_tokens()

def convert_int(theVal):
    if(theVal == None):
        return(None)
    else:
        try:
            return(str(int(theVal)))
        except Exception as err:
            print(err)
            return(None)

def convert_one_decimal(theVal):
    if(theVal == None):
        return(None)
    else:
        try:
            return(str("{:.1f}".format(theVal)))
        except Exception as err:
            print("convert_one_decimal:",err)
            return(None)

def convert_two_decimal(theVal):
    if(theVal == None):
        return(None)
    else:
        try:
            return(str("{:.2f}".format(theVal)))
        except Exception as err:
            print("convert_two_decimal:", err)
            return(None)

def convert_three_decimal(theVal):
    if(theVal == None):
        return(None)
    else:
        try:
            return(str("{:.3f}".format(theVal)))
        except Exception as err:
            print("convert_three_decimal:", err)
            return(None)

def convert_colname(theVal):
    theVal = theVal.lower()
    theVal = theVal.replace("*", "")
    theVal = theVal.replace(",", "_")
    return(theVal)

def parse_value(theCol, theVal):
    try:
        theCol = convert_colname(theCol)
        if(theCol == "angap" or theCol == "bun" or theCol == "cl" or \
            theCol == "glu" or theCol == "hct" or theCol == "na" or theCol == "tco2"):
            return convert_int(theVal)
        elif(theCol == "crea" or theCol == "k" or theCol == "hb"):
            return convert_one_decimal(float(theVal))
        elif(theCol == "ica"):
            return convert_two_decimal(float(theVal))
        elif(theCol == "lac"):
            return convert_two_decimal(float(theVal))
        elif(theCol == "be_ecf" or theCol == "tco2" or theCol == "temp_po2" or 
                theCol == "po2" or theCol == "so2"):
            return convert_int(theVal)
        elif(theCol == "pco2" or 
                theCol == "temp_pco2" or theCol == "hco3"):
            return convert_one_decimal(float(theVal))
        elif(theCol == "ph" or theCol == "temp_ph"):
            return convert_three_decimal(float(theVal))
        elif(theCol == "datetime"):
            datetime_object = datetime.strptime(theVal, "%Y-%m-%dT%H:%M:%S.%f")
            return datetime_object.strftime("%Y-%m-%d %H:%M:%S")
        elif(theCol == "upload_datetime"):
            return theVal.strftime("%Y-%m-%d %H:%M:%S")
        elif(theCol == "name" or theCol == "temp"):
            return(theVal)
    except Exception as err:
        print("parse_value:", err)
    return None

def post_redcap(theDatas, which_token):
    try:
        data = {
            'token': which_token,
            'content': 'record',
            'action': 'import',
            'format': 'json',
            'type': 'flat',
            'overwriteBehavior': 'normal',
            'forceAutoNumber': 'true',
            'data': '',
            'returnContent': 'count',
            'returnFormat': 'json'
        }

        theSendStruct = {'record_id': 0}
        for key in theDatas:
            theSendStruct[key] = theDatas[key]
        data['data'] = json.dumps([theSendStruct])

        r = requests.post(postUrl, data=data)

        if(r.status_code != 200):
            print(r.json())
            return(-2)
        elif(r.status_code == 200 and r.json()['count'] != 1):
            print(r.json())
            return(-1)
        else:
            return(1)
    except Exception as err:
        print("post_redcap:", err)
        log_later(theDatas)
        return(-3)

def which_table(test_name):
    if("CHEM8" in test_name):
        return chem8_token
    elif("CG4" in test_name):
        return cg4_token
    elif("TEST_INFO" in test_name):
        return labs_token
    elif("CBC" in test_name):
        return cbc_token
    else:
        print("which_table (" + test_name + "): Doesn't exists")
        #sys.exit(1)

    return None
