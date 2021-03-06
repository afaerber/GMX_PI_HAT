import RPi.GPIO as GPIO
import time
import serial
import re

#
#               GPIO PINOUT
#
# GMX               SLOT #0             SLOT# 1
# GMX_Reset         GPIO 5              GPIO 6
# GMX_GPIO_1        GPIO 23             GPIO 21
# GMX_GPIO_2        GPIO 24             GPIO 16
# GMX_GPIO_3        GPIO 25             GPIO 12
# GMX_GPIO_4        GPIO 18             GPIO 19
# GMX_GPIO_5        GPIO 22             GPIO 26
# GMX_GPIO_6/BOOT0  GPIO 13             GPIO 13
# GMX_I2C_SCL       SCL1 (GPIO 02)      SCL1 (GPIO 02)
# GMX_I2C_SDA       SDA1 (GPIO 03)      SDA1 (GPIO 03)
# GMX_SPI_MISO      SPI_MISO (GPIO 09)  SPI_MISO (GPIO 09)
# GMX_SPI_MOSI      SPI_MOSI (GPIO10)   SPI_MOSI (GPIO10)
# GMX_SPI_CLK       SPI_CLK (GPIO11)    SPI_CLK (GPIO11)
# GMX_SPI_CS        SPI_CE0_N (GPIO 08) SPI_CE1_N (GPIO 07)
# GMX_gmxINT        GPIO 20             GPIO 27
#
#


print "Booting GMX-CATM1..."


# GPIO pins are for Slot 1

#Init GPIO's
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Setup LED's on Module

GPIO.setup(23, GPIO.OUT)   # LED_1
GPIO.setup(24, GPIO.OUT)   # LED_2
GPIO.setup(25, GPIO.OUT)   # LED_3


# Turn on the BG96 Module
GPIO.setup(18, GPIO.OUT)   # SLOT 1

# PowerOn
GPIO.output(18,1)
time.sleep( .5 )
GPIO.output(18,0)
time.sleep( .5 )
GPIO.output(18,1)


# Reset PIN for GMX Slot #1
GPIO.setup(6, GPIO.OUT)   # SLOT 1

# Cycle the Reset
GPIO.output(6,0)
time.sleep( .1 )
GPIO.output(6,1)

#wait for reboot
time.sleep(2)

# GMX STATUS Defines
GMX_OK = 0
GMX_ERROR = -1
GMX_UKNOWN_ERROR = -2

print "Ready."

# Use /dev/ttySC0 o /dev/ttySC1
port = serial.Serial("/dev/ttySC1",  baudrate=115200)  # => SLOT 1

def _sendCmd(command):
    port.reset_input_buffer()  # flush any pending data
    port.write(command)
    return

def _parseResponse():
    time.sleep(0.2)
    response = ""

    response = port.read(1)  # start reading
    while (port.in_waiting > 0):
        response += port.read(port.in_waiting)

    matchOk = re.match(r"((.|\n)*)\r\nOK",response)

    if matchOk:
        response = matchOk.group(1)
        # not very eleganto
        matchOk2 = re.match(r"((.|\n)*)\r\n",response)
        if matchOk2:
            response = matchOk2.group(1)
        return GMX_OK,response

    matchError = re.match("((.|\n)*)\r\n(.*)ERRROR", response);
    if matchOk:
        print matchError.group()
        return GMX_ERROR,response

    return GMX_UKNOWN_ERROR,response



# Query the Module

_sendCmd("AT+CGMR\r\n")
status,response = _parseResponse()
print "Version:"+response

_sendCmd("AT+CGSN\r\n")
status,response = _parseResponse()
print "IMEI:"+response

_sendCmd("AT+CIMI\r\n")
status,response = _parseResponse()
print "IMSI:"+response


#Activate CAT-M1
_sendCmd("AT+QCFG=\"nwscanseq\",02,1\r");
status,response = _parseResponse();
print "DEBUG:"+response

_sendCmd("AT+QCFG=\"iotopmode\",0,1\r");
status,response = _parseResponse();
print "DEBUG:"+response

_sendCmd("AT+QICSGP=1,1,\"gprs.swisscom.ch\",\"\",\"\",1\r");
status,response = _parseResponse();
print "DEBUG:"+response

_sendCmd("AT+QIACT=1\r");
status,response = _parseResponse();
print "DEBUG:"+response

_sendCmd("AT+CREG=2\r");
status,response = _parseResponse();
print "DEBUG:"+response


print "\nWaiting to attach..."

# Now we try to Join
join_status = 0
join_wait = 0
while join_status == 0:

    print "Attach Attempt:"+str(join_wait)
    join_wait+=1
    time.sleep(5)

    #check id Network Joined
    _sendCmd("AT+CREG?\r")
    status, response = _parseResponse()

    # check response
    index = response.find(":")
    print "INDEX:"+str(index)
    if (index!=-1):
        data = response[index:]  
        join_status = int(data[4:5])
        print "JOIN STATUS:"+str(join_status)

# Joined - we start application

print "Attached!!!"

last_tx_time = time.time()
time_interval_tx = 20

# main loop testing
print "Starting  TX Loop - TX every "+str(time_interval_tx)+" seconds"
while True:
    delta_tx = time.time() - last_tx_time

    if ( delta_tx > time_interval_tx ):
        print "TX!"
        # TX Data

        # PUT YOUR DATA HERE
        _udp_port = "9200"
        _upd_socket_ip = "1.1.1.1"

        data_to_send = '010203'

        _sendCmd("AT+QIOPEN=1,0,\"UDP\",\""+_udp_port+"\","+_udp_port+",0,1\r")
        status,response = _parseResponse(dummyResponse);
        
        _sendCmd("AT+QISEND=0\r");

        # wait for > character
        send_data = false
        while (port.in_waiting > 0):
            response = port.read(1)
            if response == '>':
                send_data = true

        if send_data:
             count = len( data_to_send )
             for x in range(0,count):
                port.write(data_to_send[x])
             port.write(0x26)

             _sendCmd("AT+QICLOSE=0\r");
             status,response = _parseResponse(dummyResponse);      
        else:
            print "Didn't receive '>'"

        last_tx_time = time.time()
