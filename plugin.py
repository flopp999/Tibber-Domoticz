# Tibber Python Plugin
#
# Author: flopp
#
"""
<plugin key="Tibber" name="Tibber API" author="flopp" version="0.72" wikilink="https://github.com/flopp999/Tibber/tree/main/Domoticz" externallink="https://tibber.com/se/invite/8af85f51">
    <description>
        <h2>Tibber API is used to fetch data from Tibber.com</h2><br/>
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Fetch current price, every hour at minute 0</li>
            <li>Fetch today's mean price, every hour at minute 0</li>
            <li>coming: fetch consumption</li>
        </ul>
        <h3>Devices</h3>
        <ul style="list-style-type:square">
            <li>Creates a Custom Sensor with name "xxxxx - Price" and with a unique Tibber icon</li>
            <li>Select which unit you want use, "kr" or "öre"</li>
            <li>Select what data to fetch, Current price (coming later and/or Consumption)</li>
        </ul>
        <h3>How to get your personal Tibber Access Token?</h3>
        <ul style="list-style-type:square">
            <li>Login to this page to create your personal token &<a href="https://developer.tibber.com">https://developer.tibber.com</a></li>
            <li>Copy your Tibber Access Token to the field below</li>
        </ul>
        <h4>Default Tibber Access Token is a demo copied from &<a href="https://developer.tibber.com/explorer">https://developer.tibber.com/explorer</a></h4><br/>
        <h3>Configuration</h3>
    </description>
    <params>
        <param field="Mode1" label="Tibber Access Token" width="460px" required="true" default="d1007ead2dc84a2b82f0de19451c5fb22112f7ae11d19bf2bedb224a003ff74a"/>
        <param field="Mode2" label="Unit" width="100px">
            <options>
                <option label="öre" value="öre"/>
                <option label="kr" value="kr" default="true" />
            </options>
        </param>
        <param field="Mode3" label="Data to fetch" width="100px">
            <options>
                <option label="Current price" value="3" default="true" />
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
        if (len(Devices) < 2):
            Domoticz.Device(Name="Current Price", Unit=1, TypeName="Custom", Used=1, Options={"Custom": "1;"+Parameters["Mode2"]}).Create()
            Domoticz.Device(Name="Mean Price", Unit=2, TypeName="Custom", Used=1, Options={"Custom": "1;"+Parameters["Mode2"]}).Create()
        self.CurrentPriceUpdated = False
        self.MeanPriceUpdated = False
        self.UpdateCurrentPrice()
        self.UpdateMeanPrice()

        #check webpage
        #check length token

    def onHeartbeat(self):
        MinuteNow = (datetime.now().minute)
        if MinuteNow > 1 and self.CurrentPriceUpdated == True:
            self.CurrentPriceUpdated = False
            self.MeanPriceUpdated = False
        if MinuteNow == 0 and self.CurrentPriceUpdated == False:
            self.UpdateCurrentPrice()
            self.UpdateMeanPrice()

    def UpdateCurrentPrice(self):
        if CheckInternet() == True:
#        if Parameters["Mode3"] == 1:
#            data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {current {total }}}}}}" }' # asking for today's and tomorrow's hourly prices
#        if Parameters["Mode3"] == 2:
#            data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {current {total }}}}}}" }' # asking for today's and tomorrow's hourly prices
            if (Parameters["Mode3"] == "3"):
                data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {current {total }}}}}}" }' # asking for today's and tomorrow's hourly prices
            headers = {
            'Authorization': 'Bearer '+Parameters["Mode1"], # Tibber Token
            'Content-Type': 'application/json',
            }
            response = requests.post('https://api.tibber.com/v1-beta/gql', headers=headers, data=data) # make the query to Tibber
            if response.status_code == 200:
                response_json = response.json()
                CurrentPrice = round(response_json["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]["current"]["total"],2)
                if Parameters["Mode2"] == "öre":
                    CurrentPrice = CurrentPrice * 100
                Devices[1].Update(0,str(CurrentPrice))
                self.CurrentPriceUpdated = True
                Domoticz.Log("Current Price updated")

    def UpdateMeanPrice(self):
        if CheckInternet() == True:
            data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {today {total }}}}}}" }' # asking for today's and tomorrow's hourly prices
            headers = {
            'Authorization': 'Bearer '+Parameters["Mode1"], # Tibber Token
            'Content-Type': 'application/json',
            }
            response = requests.post('https://api.tibber.com/v1-beta/gql', headers=headers, data=data) # make the query to Tibber
            if response.status_code == 200:
                response_json = response.json()
                MeanPrice = float(0)
                for each in response_json["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]["today"]:
                    MeanPrice += each["total"]
                MeanPrice = round(MeanPrice / 24,2)
                if Parameters["Mode2"] == "öre":
                    MeanPrice = MeanPrice * 100
                Devices[2].Update(0,str(MeanPrice))
                self.MeanPriceUpdated = True
                Domoticz.Log("Mean Price Updated")

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def CheckInternet():
    try:
        requests.get(url='http://www.google.com/', timeout=5)
        return True
    except requests.ConnectionError:
        return False

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
