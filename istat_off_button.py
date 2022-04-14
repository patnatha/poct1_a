import board
import digitalio
import time
import os
import psutil
import subprocess

onLed = digitalio.DigitalInOut(board.D20)
onLed.direction = digitalio.Direction.OUTPUT
onLed.value = False

offButton = digitalio.DigitalInOut(board.D10)
offButton.direction = digitalio.Direction.INPUT
offButton.pull = digitalio.Pull.DOWN

def running_istat():
    isAlive = False
    try:
        for p in psutil.process_iter():
            if("python3" in p.name()):
                cmd = "ps -fp " + str(p.pid)
                theData = subprocess.run(cmd.split(), capture_output=True, text=True)
                for line in theData.stdout.split("\n"):
                    if("read_istat.py" in line):
                        isAlive = True
    except Exception as err:
        print(err)

    return(isAlive)

onLed.value = running_istat()

while True:
    if(offButton.value):
        onLed.value = False
        time.sleep(0.5)
        os.system("sudo shutdown -h now")
        onLed.value = True
        time.sleep(0.5)
        onLed.value = False

    time.sleep(1)
    onLed.value = running_istat()
