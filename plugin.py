# Tibber Python Plugin
#
# Author: flopp999
#
"""
<plugin key="Tibber" name="Tibber API 0.90" author="flopp999" version="0.90" wikilink="https://github.com/flopp999/Tibber-Domoticz" externallink="https://tibber.com/se/invite/8af85f51">
    <description>
        <h2>Tibber API is used to fetch data from Tibber.com</h2><br/>
        <h2>Support me with a coffee &<a href="https://www.buymeacoffee.com/flopp999">https://www.buymeacoffee.com/flopp999</a></h2><br/>
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Fetch current price including taxes, minimum power, maximum power, average power, accumulated cost and accumulated consumption, this will happen every hour at minute 0</li>
            <li>Fetch today's minimum, maximum and mean price including taxes, this will happen 10 minutes past midnight</li>
            <li>Fetch current Power(watt) every 10 seconds if you have Tibber Pulse installed</li>
            <li>Possible to get prices including transfering fee</li>
            <li>Debug to file ../plugins/Tibber/Tibber.log</li>
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
from Domoticz import Devices, Parameters, Images

Package = True

try:
    import requests, json, os, logging, asyncio
except ImportError:
    Package = False

try:
    from logging.handlers import RotatingFileHandler
except ImportError:
    Package = False

try:
    from datetime import datetime
except ImportError:
    Package = False

try:
    from gql import Client, gql
except ImportError:
    Package = False

try:
    from gql.transport.websockets import WebsocketsTransport
except ImportError:
    Package = False

dir = os.path.dirname(os.path.realpath(__file__))
logger = logging.getLogger("Tibber")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(dir+'/Tibber.log', maxBytes=100000, backupCount=5)
logger.addHandler(handler)


class BasePlugin:
    enabled = False

    def __init__(self):
        return

    def onStart(self):
        WriteDebug("onStart")
        self.AllSettings = True
        self.LiveDataUpdated = False
        self.CurrentPriceUpdated = False
        self.MeanPriceUpdated = False
        self.MinimumPriceUpdated = False
        self.MaximumPriceUpdated = False
        self.AccessToken = Parameters["Mode1"]
        self.Unit = Parameters["Mode2"]
        self.Fee = ""
        self.HomeID = ""
        self.Pulse = "No"
        self.headers = {
            'Host': 'api.tibber.com',
            'Authorization': 'Bearer '+self.AccessToken,  # Tibber Token
            'Content-Type': 'application/json'
            }

        if self.Fee != 0:
            try:
                float(Parameters["Mode3"])
                self.Fee = float(Parameters["Mode3"])
                WriteFile("Fee", self.Fee)
            except:
                Domoticz.Log("The Fee is not a number")

        if self.Fee == 0:
            self.Fee = CheckFile("Fee")

        if len(self.AccessToken) < 43:
            Domoticz.Log("Access Token too short")
            WriteDebug("Access Token too short")
            self.AccessToken = CheckFile("AccessToken")
        else:
            WriteFile("AccessToken", self.AccessToken)

        if 'tibberprice' not in Images:
            Domoticz.Image('tibberprice.zip').Create()

        self.ImageID = Images["tibberprice"].ID

        if Package is False:
            Domoticz.Log("Missing packages")

        self.GetDataCurrent = Domoticz.Connection(Name="Get Current", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")
        if not _plugin.GetDataCurrent.Connected() and not _plugin.GetDataCurrent.Connecting():
            _plugin.GetDataCurrent.Connect()

        self.GetDataMiniMaxMean = Domoticz.Connection(Name="Get MiniMaxMean", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")
        if not _plugin.GetDataMiniMaxMean.Connected() and not _plugin.GetDataMiniMaxMean.Connecting():
            _plugin.GetDataMiniMaxMean.Connect()

        self.GetHomeID = Domoticz.Connection(Name="Get HomeID", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")
        if not _plugin.GetHomeID.Connected() and not _plugin.GetHomeID.Connecting():
            _plugin.GetHomeID.Connect()

        self.CheckRealTimeConsumption = Domoticz.Connection(Name="Check Real Time Consumption", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")
        if not _plugin.CheckRealTimeConsumption.Connected() and not _plugin.CheckRealTimeConsumption.Connecting():
            _plugin.CheckRealTimeConsumption.Connect()

    def onConnect(self, Connection, Status, Description):
        if CheckInternet() is True and self.AllSettings is True:
            if (Status == 0):
                if Connection.Name == ("Get Current"):
                    data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {current {total }}}}}}" }'  # asking for this hourly price
                    Connection.Send({'Verb': 'POST', 'URL': '/v1-beta/gql', 'Headers': self.headers, 'Data': data})

                if Connection.Name == ("Get MiniMaxMean"):
                    data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {today {total }}}}}}" }'  # asking for this hourly price
                    Connection.Send({'Verb': 'POST', 'URL': '/v1-beta/gql', 'Headers': self.headers, 'Data': data})

                if Connection.Name == ("Get HomeID"):
                    data = '{ "query": "{viewer {homes {id}}}" }'  # asking for HomeID
                    Connection.Send({'Verb': 'POST', 'URL': '/v1-beta/gql', 'Headers': self.headers, 'Data': data})

                if Connection.Name == ("Check Real Time Consumption"):
                    data = '{ "query": "{viewer {homes {features {realTimeConsumptionEnabled}}}}" }'  # asking for HomeID
                    Connection.Send({'Verb': 'POST', 'URL': '/v1-beta/gql', 'Headers': self.headers, 'Data': data})

    def onMessage(self, Connection, Data):
        Status = int(Data["Status"])

        if (Status == 400):
            Domoticz.Error(str("Something went wrong"))
            if _plugin.GetDataCurrent.Connected():
                _plugin.GetDataCurrent.Disconnect()
            if _plugin.GetDataMiniMaxMean.Connected():
                _plugin.GetDataMiniMaxMean.Disconnect()

        if (Status == 200):
            if Connection.Name == ("Get Current"):
                self.data = Data['Data'].decode('UTF-8')
                self.data = json.loads(self.data)
                CurrentPrice = round(self.data["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]["current"]["total"], 3)
                if _plugin.Unit == "öre":
                    CurrentPrice = CurrentPrice * 100

                UpdateDevice(1, 0, str(round(CurrentPrice, 1)), self.Unit, "Current Price")
                if self.Fee != "":
                    if _plugin.Unit == "öre":
                        UpdateDevice(3, 0, str(round(CurrentPrice+self.Fee, 1)), self.Unit, "Current Price incl. fee")
                    else:
                        UpdateDevice(3, 0, str(round(CurrentPrice+(self.Fee/100), 1)), self.Unit, "Current Price incl. fee")

                WriteDebug("Current Price Updated")
                Domoticz.Log("Current Price Updated")
                self.CurrentPriceUpdated = True
                _plugin.GetDataCurrent.Disconnect()

            if Connection.Name == ("Get HomeID"):
                self.data = Data['Data'].decode('UTF-8')
                self.data = json.loads(self.data)
                for each in self.data["data"]["viewer"]["homes"]:
                    Domoticz.Log(str(each))
                Domoticz.Log("HomeID collected")
                WriteDebug("HomeID collected")
                _plugin.GetHomeID.Disconnect()

            if Connection.Name == ("Check Real Time Consumption"):
                self.data = Data['Data'].decode('UTF-8')
                self.data = json.loads(self.data)
                self.RealTime = self.data["data"]["viewer"]["homes"][0]["features"]["realTimeConsumptionEnabled"]
                if self.RealTime is False:
                    Domoticz.Log("No real time consumption device is installed")
                    WriteDebug("No real time consumption device is installed")
                else:
                    Domoticz.Log("Real time consumption device is installed will fetch Power every 10 second")
                    WriteDebug("Real time consumption device is installed")
                _plugin.CheckRealTimeConsumption.Disconnect()

            if Connection.Name == ("Get MiniMaxMean"):
                self.data = Data['Data'].decode('UTF-8')
                self.data = json.loads(self.data)
                MiniMaxPrice = []
                MeanPrice = float(0)
                for each in self.data["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]["today"]:
                    MiniMaxPrice.append(each["total"])
                    MeanPrice += each["total"]
                MinimumPrice = min(MiniMaxPrice)
                MaximumPrice = max(MiniMaxPrice)
                MeanPrice = round(MeanPrice / 24, 3)
                if _plugin.Unit == "öre":
                    MinimumPrice = MinimumPrice * 100
                    MaximumPrice = MaximumPrice * 100
                    MeanPrice = MeanPrice * 100
                UpdateDevice(2, 0, str(MeanPrice), self.Unit, "Mean Price")
                UpdateDevice(4, 0, str(round(MinimumPrice, 1)), self.Unit, "Minimum Price")
                UpdateDevice(5, 0, str(round(MaximumPrice, 1)), self.Unit, "Maximum Price")
                self.MiniMaxMeanPriceUpdated = True
                WriteDebug("Minimum Price Updated")
                WriteDebug("Maximum Price Updated")
                WriteDebug("Mean Price Updated")
                Domoticz.Log("Minimum Price Updated")
                Domoticz.Log("Maximum Price Updated")
                Domoticz.Log("Mean Price Updated")
                _plugin.GetDataMiniMaxMean.Disconnect()

    def onHeartbeat(self):
        WriteDebug("onHeartbeat")
        HourNow = (datetime.now().hour)
        MinuteNow = (datetime.now().minute)

        if self.RealTime is True:
            WriteDebug("onHeartbeatLivePower")
            
            async def LivePower():
                transport = WebsocketsTransport(url='wss://api.tibber.com/v1-beta/gql/subscriptions', headers={'Authorization': self.AccessToken})
                try:
                    async with Client(
                        transport=transport, fetch_schema_from_transport=True, execute_timeout=7
                    ) as session:
                        query = gql("subscription{liveMeasurement(homeId:\"" + self.HomeID + "\"){power}}")
                        result = await session.execute(query)
                        self.watt = result["liveMeasurement"]["power"]
                        UpdateDevice(6, 0, str(self.watt), "watt", "Watt")
                except:
                    WriteDebug("Something went wrong during getting Power from Tibber")
                    pass

            asyncio.run(LivePower())

        if MinuteNow < 59 and self.LiveDataUpdated is False and self.RealTime is True:
            WriteDebug("onHeartbeatLiveData")

            async def LiveData():
                transport = WebsocketsTransport(url='wss://api.tibber.com/v1-beta/gql/subscriptions', headers={'Authorization': self.AccessToken})
                try:
                    async with Client(transport=transport, fetch_schema_from_transport=True, execute_timeout=7) as session:
                        query = gql("subscription{liveMeasurement(homeId:\"" + self.HomeID + "\"){minPower, maxPower, averagePower, accumulatedCost, accumulatedConsumption}}")
                        result = await session.execute(query)
                        minPower = result["liveMeasurement"]["minPower"]
                        maxPower = result["liveMeasurement"]["maxPower"]
                        avePower = result["liveMeasurement"]["averagePower"]
                        accCost = result["liveMeasurement"]["accumulatedCost"]
                        accCons = result["liveMeasurement"]["accumulatedConsumption"]
                        UpdateDevice(7, 0, str(minPower), "watt", "Minimum Power")
                        UpdateDevice(8, 0, str(maxPower), "watt", "Maximum Power")
                        UpdateDevice(9, 0, str(round(avePower, 0)), "watt", "Average Power")
                        UpdateDevice(10, 0, str(round(accCost, 1)), "kr", "Accumulated Cost")
                        UpdateDevice(11, 0, str(round(accCons, 1)), "kWh", "Accumulated Consumption")
                        self.LiveDataUpdated = True
                except:
                    WriteDebug("Something went wrong during getting Power from Tibber")
                    pass

            asyncio.run(LiveData())

        if MinuteNow == 59 and self.LiveDataUpdated is True:
            self.LiveDataUpdated = False

        if MinuteNow < 59 and self.CurrentPriceUpdated is False:
            if not _plugin.GetDataCurrent.Connected() and not _plugin.GetDataCurrent.Connecting():
                WriteDebug("onHeartbeatGetDataCurrent")
                _plugin.GetDataCurrent.Connect()
        if MinuteNow == 59 and self.CurrentPriceUpdated is True:
            self.CurrentPriceUpdated = False

        if HourNow >= 0 and MinuteNow >= 10 and MinuteNow < 59 and self.MiniMaxMeanPriceUpdated is False:
            if not _plugin.GetDataMiniMaxMean.Connected() and not _plugin.GetDataMiniMaxMean.Connecting():
                WriteDebug("onHeartbeatGetDataMiniMaxMean")
                _plugin.GetDataMiniMaxMean.Connect()
        if HourNow == 23 and MinuteNow == 59 and self.MiniMaxMeanPriceUpdated is True:
            self.MiniMaxMeanPriceUpdated = False


global _plugin
_plugin = BasePlugin()


def UpdateDevice(ID, nValue, sValue, unit, Name):
    if (ID in Devices):
        if (Devices[ID].nValue != nValue) or (Devices[ID].sValue != sValue):
            Devices[ID].Update(nValue, str(sValue))
    if (ID not in Devices):
        Domoticz.Device(Name=Name, Unit=ID, TypeName="Custom", Used=1, Image=(_plugin.ImageID), Options={"Custom": "0;"+unit}, Description="Desc").Create()


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


def WriteFile(Parameter, text):
    CreateFile()
    with open(dir+'/Tibber.ini') as jsonfile:
        data = json.load(jsonfile)
    data["Config"][0][Parameter] = text
    with open(dir+'/Tibber.ini', 'w') as outfile:
        json.dump(data, outfile, indent=4)


def CheckInternet():
    WriteDebug("Entered CheckInternet")
    try:
        WriteDebug("Ping")
        requests.get(url='http://api.tibber.com/', timeout=2)
        WriteDebug("Internet is OK")
        return True
    except:
        if _plugin.GetDataCurrent.Connected() or _plugin.GetDataCurrent.Connecting():
            _plugin.GetDataCurrent.Disconnect()
        if _plugin.GetDataMiniMaxMean.Connected() or _plugin.GetDataMiniMaxMean.Connecting():
            _plugin.GetDataMiniMaxMean.Disconnect()
        if _plugin.CheckRealTimeConsumption.Connected or _plugin.CheckRealTimeConsumption.Connecting():
            _plugin.CheckRealTimeConsumption.Disconnect()
        if _plugin.GetHomeID.Connected() or _plugin.GetHomeID.Connecting():
            _plugin.GetHomeID.Disconnect()
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
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
