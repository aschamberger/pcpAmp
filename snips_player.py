#!/usr/bin/python

import argparse
import time
import paho.mqtt.client as mqtt
import sounddevice
import soundfile
from LMSTools import LMSDiscovery, LMSServer, LMSPlayer
import subprocess
import io

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('siteid', help='snips siteId')
args = parser.parse_args()
siteId = args.siteid

mqttHost = "hassio"
mqttPort = 1883
lmsHost = "tower"
lmsPort = 9000
volumeWeight=0.1

# dictionary key is siteId from snips
config = {
    'kueche': {
        'macId': '02:00:00:00:00:00',
        'gpioMute': '18',
        'alsaDevice': 'fronta'
    },
    'wohnzimmer': {
        'macId': '02:00:00:00:00:01',
        'gpioMute': '8',
        'alsaDevice': 'reara'
    },
    'wc': {
        'macId': '02:00:00:00:00:02',
        'gpioMute': '12',
        'alsaDevice': 'centera'
    },
    'schlafzimmer': {
        'macId': '02:00:00:00:00:03',
        'gpioMute': '26',
        'alsaDevice': 'fronta'
    },
    'badog': {
        'macId': '02:00:00:00:00:04',
        'gpioMute': '20',
        'alsaDevice': 'rearb'
    },
    'baddg': {
        'macId': '02:00:00:00:00:05',
        'gpioMute': '21',
        'alsaDevice': 'centerb'
    },
}

_RUNNING = True

def onConnect(client, userdata, flags, rc):
    print("Connected to mqtt server with result code " + str(rc))

    client.subscribe("hermes/audioServer/{}/playBytes/#".format(siteId))
#  client.subscribe("hermes/audioServer/{}/playFinished/#".format(siteId))

def playBytes(client, userdata, msg):
    print(msg.topic)

    _unpause = False
    _unpower = False
    if lmsPlayer.power and not lmsPlayer.muted and lmsPlayer.mode == 'play':
        print("LMS player pause")
        lmsPlayer.pause()
        _unpause = True
    elif not lmsPlayer.power:
        print("Power on amp via GPIO")
        subprocess.call(["/home/tc/power_mute_{}.sh".format(config[siteId]["gpioMute"]), 1])
        _unpower = True

    print("Play sound")
    data, fs = soundfile.read(io.BytesIO(msg.payload), dtype='float32')
    sounddevice.play(data*volumeWeight, fs, device=config[siteId]["alsaDevice"])
    status = sounddevice.wait()
    if status:
        print('Error during playback: ' + str(status))

    # snips command could have unpaused the player, so check first
    if _unpause and lmsPlayer.mode == 'pause':
        print("LMS player unpause")
        lmsPlayer.unpause()

    # snips command could have powered the player, so check first
    if _unpower and not lmsPlayer.power:
        print("Power off amp via GPIO")
        subprocess.call(["/home/tc/power_mute_{}.sh".format(config[siteId]["gpioMute"]), 0])

#def playFinished(client, userdata, msg):
#    print(msg.topic)

def stop():
    global _RUNNING
    _RUNNING = False

if __name__ == '__main__':
    print('Starting snips audio player')

    # load empty wave file to prevent lag on playing first message
    data, fs = soundfile.read('void.wav', dtype='float32')
    sounddevice.play(data, fs, device=config[siteId]["alsaDevice"])
    status = sounddevice.wait()
    if status:
        print('Error during playback: ' + str(status))

    lmsServer = LMSServer(lmsHost, lmsPort)
    lmsPlayer = LMSPlayer(config[siteId]["macId"], lmsServer)

    mqttClient = mqtt.Client()
    mqttClient.on_connect = onConnect
    mqttClient.message_callback_add("hermes/audioServer/{}/playBytes/#".format(siteId), playBytes)
#    mqttClient.message_callback_add("hermes/audioServer/{}/playFinished/#".format(siteId), playFinished)
    mqttClient.connect(mqttHost, mqttPort)
    mqttClient.loop_start()

    try:
        while _RUNNING:
            time.sleep(0.1)
        raise KeyboardInterrupt
    except KeyboardInterrupt:
        pass
    finally:
        mqttClient.loop_stop()