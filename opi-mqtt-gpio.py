#!/usr/bin/env python3

__author__ = "Sundeep Goel"
__credits__ = ["Sundeep Goel"]
__license__ = "GPL"
__version__ = "2.0"
__maintainer__ = __author__
__email__ = "sundeepgoel2@gmail.com"


import logging
import os
import signal
import socket
import sys
import time
import ssl
import configparser
import paho.mqtt.client as mqtt

PFIO_MODULE = False
GPIO_MODULE = False
GPIO_OUTPUT_PINS = []

# Script name (without extension) used for config/logfile names
APPNAME = os.path.splitext(os.path.basename(__file__))[0]
INIFILE = sys.path[0]    +'/'+APPNAME+'.ini'
LOGFILE = sys.path[0]    +'/'+APPNAME+'.log'

# Read the config file
config = configparser.ConfigParser()
config._allow_no_value=True
config.read(INIFILE)

# Use ConfigParser to pick out the settings
MODULE = config.get("global", "module")
DEBUG = config.getboolean("global", "debug")

MQTT_HOST = config.get("global", "mqtt_host")
MQTT_PORT = config.getint("global", "mqtt_port")
MQTT_USERNAME = config.get("global", "mqtt_username")
MQTT_PASSWORD = config.get("global", "mqtt_password")
MQTT_CERT_PATH = config.get("global", "mqtt_cert_path")
MQTT_TLS_INSECURE = config.get("global", "mqtt_tls_insecure")
MQTT_TLS_PROTOCOL = config.get("global", "mqtt_tls_protocol")
MQTT_CLIENT_ID = config.get("global", "mqtt_client_id")
MQTT_TOPIC = config.get("global", "mqtt_topic")
MQTT_QOS = config.getint("global", "mqtt_qos")
MQTT_RETAIN = config.getboolean("global", "mqtt_retain")
MQTT_CLEAN_SESSION = config.getboolean("global", "mqtt_clean_session")
MQTT_LWT = config.get("global", "mqtt_lwt")

MONITOR_PIN_NUMBERING = config.get("global", "monitor_pin_numbering")     # BCM or BOARD
MONITOR_OUT_INVERT = config.get("global", "monitor_out_invert")
MONITOR_POLL = config.getfloat("global", "monitor_poll")
MONITOR_REFRESH = config.get("global", "monitor_refresh")

# Initialise logging
LOGFORMAT = '%(asctime)-15s %(levelname)-5s %(message)s'

INPUT = 0 
OUTPUT = 1 
LOW = 0 
HIGH = 1 

# Check we have the necessary module
if MODULE.lower() == "opi_gpio":
    try:
        import OPi.GPIO as GPIO
        logging.info("OPi.GPIO module detected...")
        GPIO_MODULE = True
    except ImportError:
        logging.error("Module = %s in %s but OPi.GPIO module was not found" % (MODULE, INIFILE))
        sys.exit(2)
        
        
if MODULE.lower() == "opi_pya20":
    try:
        from pyA20.gpio import gpio 
        from pyA20.gpio import port 
        from pyA20.gpio import connector
        logging.info("OPi.pyA20 module detected...")
        GPIO_MODULE = True
    except ImportError:
        logging.error("Module = %s in %s but OPi.pyA20 module was not found" % (MODULE, INIFILE))
        sys.exit(2)


# pin 12 or PD14 = Plant Light"
# pin 16 or PC4 - PIR1
# pin 18 or PC7 - PIR2
# pin 29 or PA7 - Fresh Air
# pin 31 or PA8 - Exhaust Fan
# pin 33 or PA9 - Security Light

PINS = {
  3 :  port.PA12,
  5 :  port.PA11,
  7 :  port.PA6,
  8 :  port.PA13,
  10 : port.PA14,
  11 : port.PA1,
  12 : port.PD14,
  13 : port.PA0,
  15 : port.PA3,
  16 : port.PC4,
  18 : port.PC7,
  19 : port.PC0,
  21 : port.PC1,
  22 : port.PA2,
  23 : port.PC2,
  24 : port.PC3,
  26 : port.PA21,
  27 : port.PA19,
  28 : port.PA18,
  29 : port.PA7,
  31 : port.PA8,
  32 : port.PG8,
  33 : port.PA9,
  35 : port.PA10,
  36 : port.PG9,
  37 : port.PA20,
  38 : port.PG6,
  40 : port.PG7
}

if DEBUG:
    logging.basicConfig(filename=LOGFILE,
                        level=logging.DEBUG,
                        format=LOGFORMAT)
else:
    logging.basicConfig(filename=LOGFILE,
                        level=logging.INFO,
                        format=LOGFORMAT)

logging.info("Starting " + APPNAME)
logging.info("INFO MODE")
logging.debug("DEBUG MODE")
logging.debug("INIFILE = %s" % INIFILE)
logging.debug("LOGFILE = %s" % LOGFILE)



MQTT_TOPIC_IN = MQTT_TOPIC + "/in/+"
MQTT_TOPIC_OUT = MQTT_TOPIC + "/out/%d"

# Create the MQTT client
if not MQTT_CLIENT_ID:
    MQTT_CLIENT_ID = APPNAME + "_%d" % os.getpid()
    MQTT_CLEAN_SESSION = True
    
mqttc = mqtt.Client(MQTT_CLIENT_ID, clean_session=MQTT_CLEAN_SESSION)

# MQTT callbacks
def on_mqtt_connect(mosq, obj, flags, result_code):
    """
    Handle connections (or failures) to the broker.
    This is called after the client has received a CONNACK message
    from the broker in response to calling connect().
    The parameter rc is an integer giving the return code:

    0: Success
    1: Refused . unacceptable protocol version
    2: Refused . identifier rejected
    3: Refused . server unavailable
    4: Refused . bad user name or password (MQTT v3.1 broker only)
    5: Refused . not authorised (MQTT v3.1 broker only)
    """
    if result_code == 0:
        logging.info("Connected to %s:%s" % (MQTT_HOST, MQTT_PORT))

        # Subscribe to our incoming topic
        mqttc.subscribe(MQTT_TOPIC_IN, qos=MQTT_QOS)
        
        # Subscribe to the monitor refesh topic if required
        if MONITOR_REFRESH:
            mqttc.subscribe(MONITOR_REFRESH, qos=0)

        # Publish retained LWT as per http://stackoverflow.com/questions/19057835/how-to-find-connected-mqtt-client-details/19071979#19071979
        # See also the will_set function in connect() below
        mqttc.publish(MQTT_LWT, "1", qos=0, retain=True)

    elif result_code == 1:
        logging.info("Connection refused - unacceptable protocol version")
    elif result_code == 2:
        logging.info("Connection refused - identifier rejected")
    elif result_code == 3:
        logging.info("Connection refused - server unavailable")
    elif result_code == 4:
        logging.info("Connection refused - bad user name or password")
    elif result_code == 5:
        logging.info("Connection refused - not authorised")
    else:
        logging.warning("Connection failed - result code %d" % (result_code))

def on_mqtt_disconnect(mosq, obj, result_code):
    """
    Handle disconnections from the broker
    """
    if result_code == 0:
        logging.info("Clean disconnection from broker")
    else:
        logging.info("Broker connection lost. Retrying in 5s...")
        time.sleep(5)

def on_mqtt_message(mosq, obj, msg):
    """
    Handle incoming messages
    """

    
    if msg.topic == MONITOR_REFRESH:
        logging.debug("Refreshing the state of all monitored pins...")
        refresh()
        return
    
    logging.debug("Received message %s, %s" % (msg.topic, msg.payload))
        
    topicparts = msg.topic.split("/")
    pin = int(topicparts[len(topicparts) - 1])
    value = int(msg.payload)
    
    try :
        changedPort = PINS[pin]
        logging.debug("Incoming message for pin %d -> %d" % (pin, value))
        print("Incoming message for pin %d -> %d"% (pin, value))
        print("change port is %s" % (changedPort))
        if value == 1:
            gpio.setcfg(changedPort, gpio.OUTPUT)
            gpio.output(changedPort, gpio.HIGH)
        else:
            gpio.setcfg(changedPort, gpio.OUTPUT)
            gpio.output(changedPort, gpio.LOW)
    except Exception as e:
        logging.error("Error %s" % (str(e)))
  



# End of MQTT callbacks


def cleanup(signum, frame):
    """
    Signal handler to ensure we disconnect cleanly
    in the event of a SIGTERM or SIGINT.
    """
    # Cleanup our interface modules

    # Publish our LWT and cleanup the MQTT connection
    logging.info("Disconnecting from broker...")
    mqttc.publish(MQTT_LWT, "0", qos=0, retain=True)
    mqttc.disconnect()
    mqttc.loop_stop()

    # Exit from our application
    logging.info("Exiting on signal %d" % (signum))
    sys.exit(signum)


def connect_mqtt():
    """
    Connect to the broker, define the callbacks, and subscribe
    This will also set the Last Will and Testament (LWT)
    The LWT will be published in the event of an unclean or
    unexpected disconnection.
    """
    # Add the callbacks
    mqttc.on_connect = on_mqtt_connect
    mqttc.on_disconnect = on_mqtt_disconnect
    mqttc.on_message = on_mqtt_message

    # Set the login details
    if MQTT_USERNAME:
        mqttc.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    # Set the Last Will and Testament (LWT) *before* connecting
    mqttc.will_set(MQTT_LWT, payload="0", qos=0, retain=True)

    # Attempt to connect
    logging.debug("Connecting to %s:%d..." % (MQTT_HOST, MQTT_PORT))
    try:
        mqttc.connect(MQTT_HOST, MQTT_PORT, 60)
    except Exception as e:
        logging.error("Error connecting to %s:%d: %s" % (MQTT_HOST, MQTT_PORT, str(e)))
        sys.exit(2)

    # Let the connection run forever
    mqttc.loop_start()

def init_gpio():
    """
    Initialise the GPIO library
    """
    
    gpio.init()



def read_pin(pin):
    state = -1
    if PFIO_MODULE:
        state = PFIO.digital_read(pin)
        
    if GPIO_MODULE:
        state = GPIO.input(pin)

    if MONITOR_OUT_INVERT:
        if state == 0:
            state = 1
        elif state == 1:
            state = 0
    return(state)


def poll():
    """
    The main loop in which we monitor the state of the PINs
    and publish any changes.
    """
    while True:
        # ------------- mian loop -----------
        time.sleep(MONITOR_POLL)

# Use the signal module to handle signals
for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
    signal.signal(sig, cleanup)

# Initialise our pins
if GPIO_MODULE:
    init_gpio()

# Connect to broker and begin polling our GPIO pins
connect_mqtt()
poll()
