import serial
import time
from datetime import datetime
from lcdbackpack import LcdBackpack
from serial.tools import list_ports
import socket
import json
import threading

theWBC = None
redcapRes = None
msgRecv = None
msgLock = threading.Lock()

def listen_msg():
    global theWBC 
    global redcapRes
    global msgRecv

    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.bind(('localhost', 34567))
    serversocket.listen(1)

    while True:
        try:
            #Recieve the socket
            (clientsocket, address) = serversocket.accept()
            
            try:
                #Recieve the message
                theMsg = ""
                while True:
                    byte = clientsocket.recv(1).decode("utf-8", errors='ignore')
                    if(byte == "\n"):
                        break
                    else:
                        theMsg = theMsg + byte
                
                #Parse the message
                parsedMsg = json.loads(theMsg)

                msgLock.acquire()

                #Parse the WBC
                theWBC = parsedMsg["WBC"]
                if(theWBC != None):
                    try:
                        theWBC = float(theWBC)
                    except Exception as err:
                        theWBC = None
                
                #Parse the redcap upload message
                redcapRes = parsedMsg["redcap"]
                if(redcapRes == 1):
                    redcapRes = "Yes"
                elif(redcapRes == 0):
                    redcapRes = "No"
                msgRecv = datetime.now()
                msgLock.release()
            except Exception as err:
                clientsocket.close()
                print("Recv/Parse error:", err)
        except Exception as err:
            print("socketaccept error", err)
    
        time.sleep(10)

#start the background client
listenClient = threading.Thread(target=listen_msg, args=(), daemon=True)
listenClient.start()

def find_port():
    for port in list_ports.comports():
        if(port.description == "Adafruit Industries"):
            return(port.device)
    return(None)

while True:
    device_port = find_port()
    if(device_port != None):
        print("Connecting LCD")
        try:
            lcd = LcdBackpack(device_port, 9600)
            lcd.connect()
            try:
                lcd.clear()
                lcd.display_on()
                lcd.set_brightness(255)
                lcd.set_contrast(225)
                lcd.set_autoscroll(False)
                lcd.set_backlight_rgb(255,0,0)
                time.sleep(0.3)
                lcd.set_backlight_rgb(0,255,0)
                time.sleep(0.3)
                lcd.set_backlight_rgb(0,0,255)
                time.sleep(0.3)
                lcd.set_backlight_rgb(255,255,255)
                time.sleep(0.3)

                while True:
                    lcd.clear()
                    lcd.set_cursor_home()
                    
                    msgLock.acquire()
                    theMsg = None
                    if(theWBC != None and 
                        (datetime.now() - msgRecv).total_seconds() <= 60):
                        theMsg = "New WBC: " + str(theWBC) + ""
                        while(len(theMsg) < 16): theMsg += " " #Pad out the line
                        theMsg = theMsg + "RedCp Upload:" + redcapRes
                        if(theWBC != None):
                            if(theWBC > 25):
                                lcd.set_backlight_rgb(255,0,0)
                            else:
                                lcd.set_backlight_rgb(0,255,0)
                    else:
                        theMsg = "Waiting For CBCs"
                        theMsg = theMsg + datetime.strftime(datetime.now(), "%m/%d/%y %H:%M")
                        lcd.set_backlight_rgb(255,255,255)
                    msgLock.release()

                    lcd.write(theMsg)
                    time.sleep(1)
            except Exception as err:
                print("ERROR with lcd calls", err)
            lcd.disconnect()
        except Exception as err:
            print("ERROR: LcdBackpack init", err)
    else:
        print("Did not find LCD")
        time.sleep(5)

