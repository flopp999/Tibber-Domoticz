# Tibber Python Plugin
#
# Author: flopp
#
"""
<plugin key="Tibber" name="Tibber API Version: 0.81" author="flopp" version="0.81" wikilink="https://github.com/flopp999/Tibber/tree/main/Domoticz" externallink="https://tibber.com/se/invite/8af85f51">
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
Package = True
try:
    import requests
except ImportError as e:
    Package = False

try:
    import os
except ImportError as e:
    Package = False

try:
    import json
except ImportError as e:
    Package = False

try:
    from datetime import datetime
except ImportError as e:
    Package = False

class BasePlugin:
    enabled = False
    def __init__(self):
        self.Count = 0
        return

    def onStart(self):
        WriteToFile("onStart")
        if Package == True:
            if ('TibberPrice'  not in Images): Domoticz.Image('tibberprice.zip').Create()
                ImageID = Images["tibberprice"].ID
            if (len(Devices) < 2):
                Domoticz.Device(Name="Current Price", Unit=1, TypeName="Custom", Used=1, Image=ImageID, Options={"Custom": "1;"+Parameters["Mode2"]}).Create()
                Domoticz.Device(Name="Mean Price", Unit=2, TypeName="Custom", Used=1, Image=ImageID, Options={"Custom": "1;"+Parameters["Mode2"]}).Create()
            self.CurrentPriceUpdated = False
            self.MeanPriceUpdated = False
            self.UpdateCurrentPrice()
            self.UpdateMeanPrice()

            #check webpage
            #check length token
        if Package == False:
            Domoticz.Log("Missing packages")

    def onHeartbeat(self):
        WriteToFile("onHeartbeat")
        self.Count += 1
        if self.Count == 6:
            self.Count = 0
            if Package == True:
                WriteToFile("All packages is installed")
                MinuteNow = (datetime.now().minute)
                if MinuteNow > 6 and self.CurrentPriceUpdated == True:
                    WriteToFile("Set self.CurrentPriceUpdated = False")
                    self.CurrentPriceUpdated = False
                if MinuteNow > 31 and self.MeanPriceUpdated == True:
                    WriteToFile("Set self.MeanPriceUpdated = False")
                    self.MeanPriceUpdated = False
                if MinuteNow == 5 and self.CurrentPriceUpdated == False:
                    WriteToFile("Update CurrentPrice")
                    self.UpdateCurrentPrice()
                if MinuteNow == 30 and self.MeanPriceUpdated == False:
                    WriteToFile("Update MeanPrice")
                    self.UpdateMeanPrice()

    def UpdateCurrentPrice(self):
        WriteToFile("Entered UpdateCurrentPrice")
        if CheckInternet() == True:
            WriteToFile("Internet is OK")
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
            WriteToFile("Response")
            if response.status_code == 200:
                WriteToFile("CurrentPriceStatus200")
                response_json = response.json()
                CurrentPrice = round(response_json["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]["current"]["total"],2)
                if Parameters["Mode2"] == "öre":
                    CurrentPrice = CurrentPrice * 100
                Devices[1].Update(0,str(CurrentPrice))
                self.CurrentPriceUpdated = True
                WriteToFile("Current Price Updated")
                Domoticz.Log("Current Price updated")

    def UpdateMeanPrice(self):
        WriteToFile("Entered UpdateMeanPrice")
        if CheckInternet() == True:
            WriteToFile("Internet is OK")
            data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {today {total }}}}}}" }' # asking for today's and tomorrow's hourly prices
            headers = {
            'Authorization': 'Bearer '+Parameters["Mode1"], # Tibber Token
            'Content-Type': 'application/json',
            }
            response = requests.post('https://api.tibber.com/v1-beta/gql', headers=headers, data=data) # make the query to Tibber
            WriteToFile("Response")
            if response.status_code == 200:
                WriteToFile("MeanPriceStatus200")
                response_json = response.json()
                MeanPrice = float(0)
                for each in response_json["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]["today"]:
                    MeanPrice += each["total"]
                MeanPrice = round(MeanPrice / 24,2)
                if Parameters["Mode2"] == "öre":
                    MeanPrice = MeanPrice * 100
                Devices[2].Update(0,str(MeanPrice))
                self.MeanPriceUpdated = True
                WriteToFile("Mean Price Updated")
                Domoticz.Log("Mean Price Updated")

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def CheckInternet():
    WriteToFile("Entered CheckInternet")
    try:
        WriteToFile("Try ping")
        requests.get(url='http://www.google.com/', timeout=5)
        WriteToFile("Ping done")
        return True
    except requests.ConnectionError:
        WriteToFile("Internet is not available")
        return False

def WriteToFile(text):
    timenow = (datetime.now())
    file = open("plugins/Tibber/Tibber.log","a")
    file.write(str(timenow)+" "+text+"\n")
    file.close()

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
