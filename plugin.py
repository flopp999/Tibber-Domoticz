# Tibber Python Plugin
#
# Author: flopp
#
"""
<plugin key="Tibber" name="Tibber API 0.86" author="flopp" version="0.86" wikilink="https://github.com/flopp999/Tibber/tree/main/Domoticz" externallink="https://tibber.com/se/invite/8af85f51">
    <description>
        <h2>Tibber API is used to fetch data from Tibber.com</h2><br/>
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Fetch current price including taxes, every hour at minute 0</li>
            <li>Fetch today's mean price including taxes, at midnight</li>
            <li>Possible to get prices including transfering fee</li>
            <li>Debug to file Tibber.log, in plugins/Tibber</li>
        </ul>
        <h3>Devices</h3>
        <ul style="list-style-type:square">
            <li>Creates a Custom Sensor with name "xxxxx - Price" and with a unique Tibber icon</li>
            <li>Select which unit you want use, "kr" or "öre"</li>
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
        <param field="Mode3" label="Transfer fee(öre)" width="50px" required="false" default="0"/>
        <param field="Mode2" label="Unit for devices" width="50px">
            <options>
                <option label="öre" value="öre"/>
                <option label="kr" value="kr" default="true" />
            </options>
        </param>
        <param field="Mode6" label="Debug to file (Tibber.log)" width="50px">
            <options>
                <option label="Yes" value="Yes" />
                <option label="No" value="No" default="true" />
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz

Package = True
try:
    import requests, json, os, logging, asyncio
except ImportError as e:
    Package = False

try:
    from logging.handlers import RotatingFileHandler
except ImportError as e:
    Package = False

try:
    from datetime import datetime
except ImportError as e:
    Package = False


from gql import Client, gql
from gql.transport.websockets import WebsocketsTransport


dir = os.path.dirname(os.path.realpath(__file__))
logger = logging.getLogger("Tibber")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(dir+'/Tibber.log', maxBytes=50000, backupCount=5)
logger.addHandler(handler)

class BasePlugin:
    enabled = False

    def __init__(self):
        return

    def onStart(self):
        WriteDebug("onStart")
        self.AllSettings = True
        self.AccessToken = Parameters["Mode1"]
        self.Unit = Parameters["Mode2"]
        self.Fee = ""
        try:
            float(Parameters["Mode3"])
            self.Fee = float(Parameters["Mode3"])
        except:
            Domoticz.Log("The Fee is not a number")
        self.CurrentPriceUpdated = False
        self.MeanPriceUpdated = False
        self.MinimumPriceUpdated = False
        self.MaximumPriceUpdated = False

        if len(self.AccessToken) < 43:
            Domoticz.Log("Access Token too short")
            WriteDebug("Access Token too short")
            self.AccessToken = CheckFile("AccessToken")
        else:
            WriteFile("AccessToken",self.AccessToken)

        self.GetDataCurrent = Domoticz.Connection(Name="Get Current", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")
        if not _plugin.GetDataCurrent.Connected() and not _plugin.GetDataCurrent.Connecting():
            _plugin.GetDataCurrent.Connect()
        self.GetDataMean = Domoticz.Connection(Name="Get Mean", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")
        if not _plugin.GetDataMean.Connected() and not _plugin.GetDataMean.Connecting():
            _plugin.GetDataMean.Connect()
        self.GetDataMinimum = Domoticz.Connection(Name="Get Minimum", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")
        if not _plugin.GetDataMinimum.Connected() and not _plugin.GetDataMinimum.Connecting():
            _plugin.GetDataMinimum.Connect()
        self.GetDataMaximum = Domoticz.Connection(Name="Get Maximum", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")
        if not _plugin.GetDataMaximum.Connected() and not _plugin.GetDataMaximum.Connecting():
            _plugin.GetDataMaximum.Connect()

        if ('tibberprice'  not in Images):
            Domoticz.Image('tibberprice.zip').Create()
        else:
            ImageID = Images["tibberprice"].ID
            if len(Devices) < 6:
                Domoticz.Device(Name="Current Price", Unit=1, TypeName="Custom", Used=1, Image=ImageID, Options={"Custom": "1;"+Parameters["Mode2"]}).Create()
                Domoticz.Device(Name="Mean Price", Unit=2, TypeName="Custom", Used=1, Image=ImageID, Options={"Custom": "1;"+Parameters["Mode2"]}).Create()
                Domoticz.Device(Name="Minimum Price", Unit=4, TypeName="Custom", Used=1, Image=ImageID, Options={"Custom": "1;"+Parameters["Mode2"]}).Create()
                Domoticz.Device(Name="Maximum Price", Unit=5, TypeName="Custom", Used=1, Image=ImageID, Options={"Custom": "1;"+Parameters["Mode2"]}).Create()
                Domoticz.Device(Name="Watt", Unit=6, TypeName="Custom", Used=1, Image=ImageID, Options={"Custom": "1;watt"}).Create()

            if self.Fee != "" and len(Devices) < 6:
                Domoticz.Device(Name="Current Price incl. fee", Unit=3, TypeName="Custom", Used=1, Image=ImageID, Options={"Custom": "1;"+Parameters["Mode2"]}).Create()

        if Package == False:
            Domoticz.Log("Missing packages")

    def onConnect(self, Connection, Status, Description):
        if CheckInternet() == True and self.AllSettings == True:
            if (Status == 0):
                if Connection.Name == ("Get Current"):
                    data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {current {total }}}}}}" }' # asking for this hourly price
                    headers = {
                        'Host': 'api.tibber.com',
                        'Authorization': 'Bearer '+self.AccessToken, # Tibber Token
                        'Content-Type': 'application/json'
                        }
                    WriteDebug("innan current")
                    Connection.Send({'Verb':'POST', 'URL': '/v1-beta/gql', 'Headers': headers, 'Data': data})

                if Connection.Name == ("Get Minimum"):
                    data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {today {total }}}}}}" }' # asking for this hourly price
                    headers = {
                        'Host': 'api.tibber.com',
                        'Authorization': 'Bearer '+self.AccessToken, # Tibber Token
                        'Content-Type': 'application/json'
                        }
                    WriteDebug("innan minimum")
                    Connection.Send({'Verb':'POST', 'URL': '/v1-beta/gql', 'Headers': headers, 'Data': data})

                if Connection.Name == ("Get Maximum"):
                    data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {today {total }}}}}}" }' # asking for this hourly price
                    headers = {
                        'Host': 'api.tibber.com',
                        'Authorization': 'Bearer '+self.AccessToken, # Tibber Token
                        'Content-Type': 'application/json'
                        }
                    WriteDebug("innan maximum")
                    Connection.Send({'Verb':'POST', 'URL': '/v1-beta/gql', 'Headers': headers, 'Data': data})

                if Connection.Name == ("Get Mean"):
                    data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {today {total }}}}}}" }' # asking for today's hourly prices
                    headers = {
                        'Host': 'api.tibber.com',
                        'Authorization': 'Bearer '+self.AccessToken, # Tibber Token
                        'Content-Type': 'application/json'
                        }
                    WriteDebug("innan mean")
                    Connection.Send({'Verb':'POST', 'URL': '/v1-beta/gql', 'Headers': headers, 'Data': data})

    def onMessage(self, Connection, Data):
        Status = int(Data["Status"])

        if (Status == 400):
            Domoticz.Error(str("Something went wrong"))
            if _plugin.GetDataCurrent.Connected():
                _plugin.GetDataCurrent.Disconnect()
            if _plugin.GetDataMean.Connected():
                _plugin.GetDataMean.Disconnect()

        if Connection.Name == ("Get Current"):
            if (Status == 200):
                self.data = Data['Data'].decode('UTF-8')
                self.data = json.loads(self.data)
                CurrentPrice = round(self.data["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]["current"]["total"],3)
                if _plugin.Unit == "öre":
                    CurrentPrice = CurrentPrice * 100
                Devices[1].Update(0,str(round(CurrentPrice,1)))
                if self.Fee != "":
                    if _plugin.Unit == "öre":
                        Devices[3].Update(0,str(CurrentPrice+self.Fee))
                    else:
                        Devices[3].Update(0,str(CurrentPrice+(self.Fee/100)))
                WriteDebug("Current Price Updated")
                Domoticz.Log("Current Price Updated")
                self.CurrentPriceUpdated = True
                _plugin.GetDataCurrent.Disconnect()

        if Connection.Name == ("Get Minimum"):
            if (Status == 200):
                self.data = Data['Data'].decode('UTF-8')
                self.data = json.loads(self.data)
                MinimumPrice = []
                for each in self.data["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]["today"]:
                    MinimumPrice.append(each["total"])
                MinimumPrice = min(MinimumPrice)
                if _plugin.Unit == "öre":
                    MinimumPrice = MinimumPrice * 100
                Devices[4].Update(0,str(round(MinimumPrice,1)))
                self.MinimumPriceUpdated = True
                WriteDebug("Minimum Price Updated")
                Domoticz.Log("Minimum Price Updated")
                _plugin.GetDataMinimum.Disconnect()

        if Connection.Name == ("Get Maximum"):
            if (Status == 200):
                self.data = Data['Data'].decode('UTF-8')
                self.data = json.loads(self.data)
                MaximumPrice = []
                for each in self.data["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]["today"]:
                    MaximumPrice.append(each["total"])
                MaximumPrice = max(MaximumPrice)
                if _plugin.Unit == "öre":
                    MaximumPrice = MaximumPrice * 100
                #need to fix with decimals if KR is used
                Devices[5].Update(0,str(round(MaximumPrice,1)))
                self.MaximumPriceUpdated = True
                WriteDebug("Maximum Price Updated")
                Domoticz.Log("Maximum Price Updated")
                _plugin.GetDataMaximum.Disconnect()

        if Connection.Name == ("Get Mean"):
            if (Status == 200):
                self.data = Data['Data'].decode('UTF-8')
                self.data = json.loads(self.data)
                MeanPrice = float(0)
                for each in self.data["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]["today"]:
                    MeanPrice += each["total"]
                MeanPrice = round(MeanPrice / 24,3)
                if _plugin.Unit == "öre":
                    MeanPrice = MeanPrice * 100
                Devices[2].Update(0,str(MeanPrice))
                self.MeanPriceUpdated = True
                WriteDebug("Mean Price Updated")
                Domoticz.Log("Mean Price Updated")
                _plugin.GetDataMean.Disconnect()


    def onHeartbeat(self):
        WriteDebug("onHeartbeat")
        HourNow = (datetime.now().hour)
        MinuteNow = (datetime.now().minute)

        async def main():
            transport = WebsocketsTransport(
            url='wss://api.tibber.com/v1-beta/gql/subscriptions',
            headers={'Authorization': 'd1007ead2dc84a2b82f0de19451c5fb22112f7ae11d19bf2bedb224a003ff74a'}
            )
            async with Client(
                transport=transport, fetch_schema_from_transport=True,
            ) as session:
                query = gql(
                """
                subscription{liveMeasurement(homeId:"c70dcbe5-4485-4821-933d-a8a86452737b"){power}}
                """
                )
                result = await session.execute(query)
                self.watt = result["liveMeasurement"]["power"]
                Devices[6].Update(0,str(self.watt))
                Domoticz.Log(str(self.watt))

        asyncio.run(main())

        if MinuteNow < 59 and self.CurrentPriceUpdated == False:
            if not _plugin.GetDataCurrent.Connected() and not _plugin.GetDataCurrent.Connecting():
                WriteDebug("onHeartbeatGetDataCurrent")
                _plugin.GetDataCurrent.Connect()
        if MinuteNow == 59 and self.CurrentPriceUpdated == True:
            self.CurrentPriceUpdated = False

        if HourNow >= 0 and MinuteNow >= 10 and MinuteNow < 59 and self.MinimumPriceUpdated == False:
            if not _plugin.GetDataMinimum.Connected() and not _plugin.GetDataMinimum.Connecting():
                WriteDebug("onHeartbeatGetDataMinimum")
                _plugin.GetDataMinimum.Connect()
        if HourNow == 23 and MinuteNow == 59 and self.MinimumPriceUpdated == True:
            self.MinimumPriceUpdated = False

        if HourNow >= 0 and MinuteNow >= 12 and MinuteNow < 59 and self.MaximumPriceUpdated == False:
            if not _plugin.GetDataMaximum.Connected() and not _plugin.GetDataMaximum.Connecting():
                WriteDebug("onHeartbeatGetDataMaximum")
                _plugin.GetDataMaximum.Connect()
        if HourNow == 23 and MinuteNow == 59 and self.MaximumPriceUpdated == True:
            self.MaximumPriceUpdated = False

        if HourNow >= 1 and MinuteNow >= 6 and MinuteNow < 59 and self.MeanPriceUpdated == False:
            if not _plugin.GetDataMean.Connected() and not _plugin.GetDataMean.Connecting():
                WriteDebug("onHeartbeatGetDataMean")
                _plugin.GetDataMean.Connect()
        if HourNow == 23 and MinuteNow == 59 and self.MeanPriceUpdated == True:
            self.MeanPriceUpdated = False


global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    _plugin.onMessage(Connection, Data)

def CreateFile():
    if not os.path.isfile(dir+'/Tibber.ini'):
        data = {}
        data["Config"] = []
        data["Config"].append({
             "AccessToken": ""
             })
        with open(dir+'/Tibber.ini', 'w') as outfile:
            json.dump(data, outfile, indent=4)

def CheckFile(Parameter):
    if os.path.isfile(dir+'/Tibber.ini'):
        with open(dir+'/Tibber.ini') as jsonfile:
            data = json.load(jsonfile)
            data = data["Config"][0][Parameter]
            if data == "":
                _plugin.AllSettings = False
            else:
                return data

def WriteFile(Parameter,text):
    CreateFile()
    with open(dir+'/Tibber.ini') as jsonfile:
        data = json.load(jsonfile)
    data["Config"][0][Parameter] = text
    with open(dir+'/Tibber.ini', 'w') as outfile:
        json.dump(data, outfile, indent=4)

def CheckInternet():
    WriteDebug("Entered CheckInternet")
    try:
        WriteDebug("Try ping")
        requests.get(url='http://api.tibber.com/', timeout=2)
        WriteDebug("Ping done")
        return True
    except:
        if _plugin.GetDataCurrent.Connected():
            _plugin.GetDataCurrent.Disconnect()
        if _plugin.GetDataMean.Connected():
            _plugin.GetDataMean.Disconnect()
        WriteDebug("Internet is not available")
        return False

def WriteDebug(text):
    if Parameters["Mode6"] == "Yes":
        timenow = (datetime.now())
        logger.info(str(timenow)+" "+text)

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
