
#
# lambda_temp_measure.py
# Measures current temperature from an I2C interface (assumed to be on a Ras pi) from an 
# LM75A Temp sensor and reports to AWS Iot Core.
#
# Post temperature measured on edge device to Topic: gg-edge-kit/temp every 5 seconds.
#
# Note: Must run as Greengrass Lambda as in no container mode root to access sysbus successfully, 
# see below link for required config settings
# https://docs.aws.amazon.com/greengrass/latest/developerguide/lambda-group-config.html#lambda-running-as-root
# TODO: working on a way to run as non-root.
# 
# 
# Greengrass Container Parameters:
# Another user ID/group ID: 0
# Containerization: No Container (Always)
# Lambda lifecycle: Make this function long-lived and keep it running indefinitely
# All else to default
#
#
import logging
import sys
import smbus
from threading import Timer
import greengrasssdk

# Config the logger.
log = logging.getLogger(__name__)
logging.basicConfig(
format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s", stream=sys.stdout, level=logging.INFO)

# Creating a greengrass core sdk client
client = greengrasssdk.client("iot-data")

# Initialise the LM75A Temp sensor.
# Get default the address of LM75A is set to 0x48
# aka A0, A1, and A2 are set to GND (0v).
address = 0x48

# (for standalone script only - could take event item from triggered lambda)
# Check if another address has been specified
#if 1 < len(sys.argv):
#    address = int(sys.argv[1], 16)

# Init the bus object.
bus = smbus.SMBus(1)

def post_log(message, log_callback, mqtt_topic):
    """
    Simple method to both log to local and post a message to MQTT
    """
    
    log_callback(message)
    
    client.publish(
        topic=mqtt_topic,
        queueFullPolicy="AllOrException",
        payload=message
    )

# looped (pinned) lambda function to read and report the temperature.
def greengrass_measure_temp():
    try:
        temp = get_temp()
        
        msg = "temp: {}".format(temp)
        post_log(msg, log.info, "gg-edge-kit/temp")

    except Exception as e:
        post_log(repr(e), log.error, "gg-edge-kit/temp/error")
    
    finally:
        # Asynchronously schedule this function to be run again in 5 seconds
        Timer(5, greengrass_measure_temp).start()

def get_temp():

    # Read I2C data and calculate temperature
    raw = bus.read_word_data(address, 0) & 0xFFFF
    raw = ((raw << 8) & 0xFF00) + (raw >> 8)
    temperature = (raw / 32.0) / 8.0
    return temperature

# Start get temp as thread
Timer(0, greengrass_measure_temp).start()

# This is a dummy handler for AWS lambda and will not be invoked
# Instead the code above will be executed in an infinite loop for our example
def lambda_handler(event, context):
    return
