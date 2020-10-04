#
# lambda_gpio_control.py
# On-Demand Greengrass lambda to trigger GPIO Pins 8 - 15 on a Raspberry Pi.
# Is assumed these pins correlate to relays 1 - 8 on the GPOIO relay board.
# see pin_map below for moe detail.
# 
# Note: Must run as root to access GPIO recourses successfully, see below link for required config settings
# https://docs.aws.amazon.com/greengrass/latest/developerguide/lambda-group-config.html#lambda-running-as-root
#
# TODO: Will be able to use AWS Greengrass RasPi GPIO connector instead of running as root ID
#
# Greengrass Container Parameters:
# Another user ID/group ID: 0
# Containerization: No Container (Always)
# Lambda lifecycle: On-demand function
# All else to default
#
# Will initialise the GPIOs and set all relays to closed when first deployed, beware of this 
# if you have anything of important running on the relays. Once deployed, you need to trigger 
# the lambda with settings as describes below to set the relays open of closed.
#
#
import logging
import sys
import json
import RPi.GPIO as GPIO
from threading import Timer
import greengrasssdk

#GPIO Pin Map - set as per your own physical connectivity if not using GPIO Pins 8 - 15.
# Maps GPIO Relay board relay number to connected Ras Pi GPIO Pins
# In this case relays 1 to 8 map sequentially to Ras Pi GPIO pins starting at 8 to 15
# GPIO pins 0 - 7 have other special purposes so we try and reserve them if possible.

pin_map = {1:8, 2:9, 3:10, 4:11, 5:12, 6:13, 7:14, 8:15}

# Config the logger.
log = logging.getLogger(__name__)
logging.basicConfig(
format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s", stream=sys.stdout, level=logging.INFO)

def post_log(message, log_callback, mqtt_topic):
    """
    Simple method to log to local and post a message to MQTT
    """
    
    log_callback(message)
    
    client.publish(
        topic=mqtt_topic,
        queueFullPolicy="AllOrException",
        payload=message
    )

####################################
## Init the Greengrass client 
# Creating a greengrass core sdk client
#
client = greengrasssdk.client("iot-data")

####################################
## Init the Rasp Pi GPIO Interface

post_log("Initilising gg-gpio-relay-control  on device: TBA", log.info, "gg-edge-kit/gpio-relay/init")

# Assumed that the GPIO relay board is connected on GPIO pins 8 - 15
# Initialise GPIO 8 - 15 as output pins and tie them low to start 
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# If using other pins for GPIO Relay board then set according below.
# Is assumed in this case that GPIO pins 8 - 15 correlate to relays 1 - 8 

for pin in pin_map:
    GPIO.setup(pin_map[pin], GPIO.OUT)
    GPIO.output(pin_map[pin], False)

post_log("Initialising COMPLETE gg-gpio-relay-control  on device: TBA", log.info, "gg-edge-kit/gpio-relay/init")

####################################
## Functions

def greengrass_set_gpio_relay(relay_settings):
    """
    Expects a dict with:
        a) Key: representing the relay number 1 - 8.
        b) Value: 0 or 1 representing setting the relay open and closed respectively
        i.e: {'1':'1', '3':'0', '6':'0', '8':'1'}
        
        Would set relay 1, 3, 6 & 8 to the respective Open/Closed values

    Note: As passing in via MQTT it is assumed all keys and 0/1 values are 
    passed in as strings, will error if not.
    """
    try:
        for relay in relay_settings:
            gpio_pin = pin_map[int(relay)]
            gpio_val = int(relay_settings[relay])
            log.info('Setting relay: {} on pin: {}  to : {}'.format(relay,gpio_pin, gpio_val))
            GPIO.output(gpio_pin, gpio_val)

        msg = 'GPIO relay pins set to: {} on device TBA'.format(relay_settings)
        post_log(msg, log.info, "gg-edge-kit/gpio-relay/set")

    except Exception as e:
        post_log(repr(e), log.error, "gg-edge-kit/gpio-relay/error")

# This will be triggered from MQTT and expects a dict in event called relay_settings 
def lambda_handler(event, context):
    """
    This method will be triggered from an on-demand Lambda function in AWS IoT Greengrass
    It expects a string representation of a python dict called 'relay_settings' to be provided in the event with:
        a) Key: representing the relay number 1 - 8.
        b) Value: 0 or 1 representing setting the relay open and closed respectively
        i.e: {'1':'1', '3':'0', '6':'0', '8':'1'}
        
        Would set relay 1, 3, 6 & 8 to the respective Open/Closed values
        
        Note: Must be in String quotes to sterilize with JSON.dumps or Lambda will throw an exception
        If testing from IoT Core MQQT publish below is an example of a valid message for AWS IoT Core MQTT publish
        { 
            "relay_settings": "{'1':'1', '5':'0'}" 
        }
        This would set relay 1 to closed and relar 5 to open
    """

    # Get the relay_settings var from the event trigger, parse to a dict and send to be actioned    
    if 'relay_settings' in event:
        relay_settings = json.loads(event['relay_settings'].replace("'", '"'))
        greengrass_set_gpio_relay(relay_settings)
    else:
        post_log('gg-gpio-relay-control Lambda triggered without a valid relay_settings variable in event', log.error, "gg-edge-kit/gpio-relay/error")
