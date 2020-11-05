# Tibber Python Plugin
#
# Author: flopp
#
"""
<plugin key="Tibber" name="Tibber API" author="flopp" version="0.5" wikilink="https://github.com/flopp999/Tibber/tree/main/Domoticz" externallink="https://tibber.com/se/invite/8af85f51">
    <description>
        <h2>Tibbe API is used to fetch hourly prices from Tibber</h2><br/>
        Overview...
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Feature one...</li>
            <li>Feature two...</li>
        </ul>
        <h3>Devices</h3>
        <ul style="list-style-type:square">
            <li>Device Type - What it does...</li>
        </ul>
        <h3>Configuration</h3>
        Configuration options...
    </description>
    <params>
        <param field="Mode1" label="Tibber token" width="350px" required="true"/>
        <param field="Mode6" label="Debug" width="100px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true" />
                <option label="Logging" value="File"/>
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import requests
import json
from datetime import datetime

class BasePlugin:
    enabled = False
    def __init__(self):
        return

    def onStart(self):
        if (len(Devices) == 0):
            Domoticz.Device(Name="Price", Unit=1, TypeName="Custom", Used=1).Create()

        #check internet
        #check webpage
        #check length token

    def onStop(self):
        Domoticz.Log("onStop called")

    def onHeartbeat(self):
        timenow = (datetime.now().minute)
        if timenow == 0:
            data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {current {total }}}}}}" }' # asking for today's and tomorrow's hourly prices
            headers = {
            'Authorization': 'Bearer '+Parameters["Mode1"], # Tibber Token
            'Content-Type': 'application/json',
            }
            response = requests.post('https://api.tibber.com/v1-beta/gql', headers=headers, data=data) # make the query to Tibber
            response_json = response.json()
            CurrentPrice = response_json["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]["current"]["total"]
            Devices[1].Update(0,str(CurrentPrice))
            Domoticz.Log("Price updated")

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
debian@NUC:~/domotic
