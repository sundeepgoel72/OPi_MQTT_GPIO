# OPi_MQTT_GPIO
MQTT based control of GPIO pins for OrangePi

This work is based on https://github.com/sumnerboy12/mqtt-gpio-monitor. 

Python script for sending/receiving commands to/from GPIO pins via MQTT messages for the OrangePi Board. I have attempted to keep this initial release very simple for the OrangePi board.

This was written for use on a OrangePi, with the pyA20 module installed. 

The example INI file contains the only configuration required. 

    sudo pip install pyA20
    sudo pip3 install pyA20

You will also need an MQTT client, in this case Paho. To install;

    sudo pip install paho-mqtt

You should now be ready to run the script. It will listen for incoming messages on 
{topic}/in/+ (where {topic} is specified in the INI file). 
The incoming messages need to arrive on {topic}/in/{pin} with a value of either 1 or 0.

E.g. a message arriving on {topic}/in/3 with value 1 will set pin 3 to HIGH.

To use from command prompt
    sudo python opi-mqtt-gpio.py
    
to execute on startup, add following to /etc/rc.local
    python /<path of file>/opi-mqtt-gpio.py &
    
Have fun !!!!!

