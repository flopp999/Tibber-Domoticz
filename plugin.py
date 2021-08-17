# Tibber Python Plugin
#
# Author: flopp999
#
"""
<plugin key="Tibber" name="Tibber API 0.98" author="flopp999" version="0.98" wikilink="https://github.com/flopp999/Tibber-Domoticz" externallink="https://tibber.com/se/invite/8af85f51">
    <description>
        <h2>Tibber API is used to fetch data from Tibber.com</h2><br/>
        <h2>Support me with a coffee &<a href="https://www.buymeacoffee.com/flopp999">https://www.buymeacoffee.com/flopp999</a></h2><br/>
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Fetch current price including taxes, minimum power, maximum power, average power, accumulated cost and accumulated consumption, this will happen every hour at minute 0</li>
            <li>Fetch today's minimum, maximum and mean price including taxes, this will happen 10 minutes past midnight</li>
            <li>Fetch current Power(watt) every 10 seconds if you have Tibber Watty/Pulse installed</li>
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
        <param field="Mode4" label="Home ID" width="350px" required="false" default="Copy from Domoticz Log or Tibber Develop webpage"/>
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

    def onStop(self):
        if _plugin.GetDataCurrent.Connected() or _plugin.GetDataCurrent.Connecting():
            _plugin.GetDataCurrent.Disconnect()
        if _plugin.GetDataMiniMaxMean.Connected() or _plugin.GetDataMiniMaxMean.Connecting():
            _plugin.GetDataMiniMaxMean.Disconnect()
        if _plugin.CheckRealTimeHardware.Connected() or _plugin.CheckRealTimeHardware.Connecting():
            _plugin.CheckRealTimeHardware.Disconnect()
        if _plugin.GetHomeID.Connected() or _plugin.GetHomeID.Connecting():
            _plugin.GetHomeID.Disconnect()
        if  _plugin.GetHouseNumber.Connected() or _plugin.GetHouseNumber.Connecting():
            _plugin.GetHouseNumber.Disconnect()

    def onStart(self):
        WriteDebug("onStart")
        self.AllSettings = False
        self.LiveDataUpdated = False
        self.CurrentPriceUpdated = False
        self.MiniMaxMeanPriceUpdated = False
        self.LiveDataUpdated = False
        self.AccessToken = Parameters["Mode1"]
        self.Unit = Parameters["Mode2"]
        self.HomeID = Parameters["Mode4"]
        self.Fee = ""
        self.Pulse = "No"
        self.House = 0
        self.RealTime = False

        self.headers = {
            'Host': 'api.tibber.com',
            'Authorization': 'Bearer '+self.AccessToken,  # Tibber Token
            'Content-Type': 'application/json'
            }

        if self.Fee != 0:
            try:
                float(Parameters["Mode3"])
                self.Fee = float(Parameters["Mode3"])
                self.AllSettings = True
            except:
                Domoticz.Log("The Fee is not a number")

        if len(self.AccessToken) < 43:
            Domoticz.Log("Access Token too short")
            WriteDebug("Access Token too short")
        else:
            self.AllSettings = True

        if len(self.HomeID) is not 36:  # will get Home ID from server
            self.HomeID = ""
            Domoticz.Log("Home ID is not correct")
            WriteDebug("Home ID not correct")
        else:
            self.AllSettings = True

        if os.path.isfile(dir+'/tibberprice.zip'):
            if "tibberprice" not in Images:
                Domoticz.Image("tibberprice.zip").Create()
            self.ImageID = Images["tibberprice"].ID

        if Package is False:
            Domoticz.Log("Missing packages")

        self.GetHomeID = Domoticz.Connection(Name="Get HomeID", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")
        if not _plugin.GetHomeID.Connected() and not _plugin.GetHomeID.Connecting() and not self.HomeID:
            _plugin.GetHomeID.Connect()

        self.GetHouseNumber = Domoticz.Connection(Name="Get House Number", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")
        if not _plugin.GetHouseNumber.Connected() and not _plugin.GetHouseNumber.Connecting() and self.HomeID:
            _plugin.GetHouseNumber.Connect()

        self.CheckRealTimeHardware = Domoticz.Connection(Name="Check Real Time Hardware", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")

        self.GetDataCurrent = Domoticz.Connection(Name="Get Current", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")

        self.GetDataMiniMaxMean = Domoticz.Connection(Name="Get MiniMaxMean", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")

    def onConnect(self, Connection, Status, Description):
        if CheckInternet() is True and self.AllSettings is True:
            if (Status == 0):
                if Connection.Name == ("Get HomeID"):
                    data = '{ "query": "{viewer {homes {id}}}" }'  # asking for HomeID
                    Connection.Send({'Verb': 'POST', 'URL': '/v1-beta/gql', 'Headers': self.headers, 'Data': data})

                if Connection.Name == ("Get House Number"):
                    data = '{ "query": "{viewer {homes {id}}}" }'  # asking for all homids
                    Connection.Send({'Verb': 'POST', 'URL': '/v1-beta/gql', 'Headers': self.headers, 'Data': data})

                if Connection.Name == ("Get Current"):
                    data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {current {total }}}}}}" }'  # asking for this hourly price
                    Connection.Send({'Verb': 'POST', 'URL': '/v1-beta/gql', 'Headers': self.headers, 'Data': data})

                if Connection.Name == ("Get MiniMaxMean"):
                    data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {today {total }}}}}}" }'  # asking for this hourly price
                    Connection.Send({'Verb': 'POST', 'URL': '/v1-beta/gql', 'Headers': self.headers, 'Data': data})

                if Connection.Name == ("Check Real Time Hardware"):
                    data = '{ "query": "{viewer {homes {id,features {realTimeConsumptionEnabled}}}}" }'  # check if Real Time hardware is installed
                    Connection.Send({'Verb': 'POST', 'URL': '/v1-beta/gql', 'Headers': self.headers, 'Data': data})


    def onMessage(self, Connection, Data):
        Status = int(Data["Status"])
        Data = Data['Data'].decode('UTF-8')
        Data = json.loads(Data)

        if (Status == 200):
            if "errors" in Data:
                Domoticz.Log(str(Data["errors"][0]["extensions"]["code"]))

            elif Connection.Name == ("Get HomeID"):

                for each in Data["data"]["viewer"]["homes"]:
                    Domoticz.Log("Home "+str(self.House)+" has ID = "+str(each["id"]))
                self.HomeID = Data["data"]["viewer"]["homes"][self.House]["id"]
                WriteDebug("HomeID collected")
                _plugin.GetHomeID.Disconnect()
                _plugin.GetHouseNumber.Connect()

            elif Connection.Name == ("Get House Number"):

                if 'errors' in Data:
                    self.AllSettings = False
                    Domoticz.Error(str(Data["errors"][0]["message"]))

                else:
                    if len(Data["data"]["viewer"]["homes"]) > 0:
                        for each in Data["data"]["viewer"]["homes"]:
                            if self.HomeID == each["id"]:
                                continue
                            self.House += 1
                    Domoticz.Log("Using Home ID = "+str(self.HomeID))
                    _plugin.CheckRealTimeHardware.Connect()
                _plugin.GetHouseNumber.Disconnect()

            elif Connection.Name == ("Check Real Time Hardware"):
                for each in Data["data"]["viewer"]["homes"]:
                    if each["id"] == self.HomeID:
                        self.RealTime = each["features"]["realTimeConsumptionEnabled"]
                if self.RealTime is False:
                    Domoticz.Log("No real time hardware is installed")
                    WriteDebug("No real time hardware is installed")
                else:
                    Domoticz.Log("Real time hardware is installed and will be fetched every 10 seconds")
                    WriteDebug("Real time hardware is installed")
                _plugin.CheckRealTimeHardware.Disconnect()
                _plugin.GetDataCurrent.Connect()


            elif Connection.Name == ("Get Current"):
                CurrentPrice = round(Data["data"]["viewer"]["homes"][self.House]["currentSubscription"]["priceInfo"]["current"]["total"], 3)
                if _plugin.Unit == "öre":
                    CurrentPrice = CurrentPrice * 100
                UpdateDevice("Current Price", str(round(CurrentPrice, 1)))
                if self.Fee != "":
                    if self.Unit == "öre":
                        UpdateDevice("Current Price incl. fee", str(round(CurrentPrice+self.Fee, 1)))
                    else:
                        UpdateDevice("Current Price incl. fee", str(round(CurrentPrice+(self.Fee/100), 1)))
                WriteDebug("Current Price Updated")
                self.CurrentPriceUpdated = True
                _plugin.GetDataCurrent.Disconnect()
                _plugin.GetDataMiniMaxMean.Connect()

            elif Connection.Name == ("Get MiniMaxMean"):
                MiniMaxPrice = []
                MeanPrice = float(0)
                for each in Data["data"]["viewer"]["homes"][self.House]["currentSubscription"]["priceInfo"]["today"]:
                    Domoticz.Log(str(each))
                    MiniMaxPrice.append(each["total"])
                    MeanPrice += each["total"]
                MinimumPrice = min(MiniMaxPrice)
                MaximumPrice = max(MiniMaxPrice)
                MeanPrice = round(MeanPrice / 24, 3)
                if _plugin.Unit == "öre":
                    MinimumPrice = MinimumPrice * 100
                    MaximumPrice = MaximumPrice * 100
                    MeanPrice = MeanPrice * 100
                UpdateDevice("Mean Price", str(MeanPrice))
                UpdateDevice("Minimum Price", str(round(MinimumPrice, 1)))
                UpdateDevice("Maximum Price", str(round(MaximumPrice, 1)))
                self.MiniMaxMeanPriceUpdated = True
                WriteDebug("Minimum Price Updated")
                WriteDebug("Maximum Price Updated")
                WriteDebug("Mean Price Updated")
                _plugin.GetDataMiniMaxMean.Disconnect()

        else:
            WriteDebug("Status = "+str(Status))
            Domoticz.Error(str("Status "+str(Status)))
            Domoticz.Error(str(Data))
            if _plugin.GetDataCurrent.Connected():
                _plugin.GetDataCurrent.Disconnect()
            if _plugin.GetDataMiniMaxMean.Connected():
                _plugin.GetDataMiniMaxMean.Disconnect()

    def onHeartbeat(self):
        WriteDebug("onHeartbeat")
        HourNow = (datetime.now().hour)
        MinuteNow = (datetime.now().minute)

        if self.RealTime is True and self.AllSettings is True:
            WriteDebug("onHeartbeatLivePower")
            async def LivePower():
                transport = WebsocketsTransport(url='wss://api.tibber.com/v1-beta/gql/subscriptions', headers={'Authorization': self.AccessToken})
                try:
                    async with Client(transport=transport, fetch_schema_from_transport=True, execute_timeout=7) as session:
                        query = gql("subscription{liveMeasurement(homeId:\"" + self.HomeID + "\"){power, minPower, maxPower, powerProduction, powerReactive, powerProductionReactive, minPowerProduction, maxPowerProduction, lastMeterProduction, powerFactor, voltagePhase1, voltagePhase2, voltagePhase3, currentL1, currentL2, currentL3}}")
                        result = await session.execute(query)
                        for name,value in result["liveMeasurement"].items():
                            Domoticz.Log(name)
                            Domoticz.Log(str(value))
                            if value is not None:
                                UpdateDevice(str(name), str(value))
                    self.LiveDataUpdated = True
                except Exception as e:
                    WriteDebug("Something went wrong during fetching Live Data from Tibber")
                    WriteDebug(str(e))
                    pass
            asyncio.run(LivePower())

        if MinuteNow < 59 and self.LiveDataUpdated is False and self.RealTime is True and self.AllSettings is True:
            WriteDebug("onHeartbeatLiveData")

            async def LiveData():
                transport = WebsocketsTransport(url='wss://api.tibber.com/v1-beta/gql/subscriptions', headers={'Authorization': self.AccessToken})
                try:
                    async with Client(transport=transport, fetch_schema_from_transport=True, execute_timeout=7) as session:
                        query = gql("subscription{liveMeasurement(homeId:\"" + self.HomeID + "\"){lastMeterConsumption, accumulatedConsumption, accumulatedProduction, accumulatedConsumptionLastHour, accumulatedProductionLastHour, accumulatedCost, accumulatedReward, averagePower}}")
                        result = await session.execute(query)
                        for name,value in result["liveMeasurement"].items():
                            Domoticz.Log(name)
                            Domoticz.Log(str(value))
                            if value is not None:
                                UpdateDevice(str(name), str(value))
                    self.LiveDataUpdated = True
                except Exception as e:
                    WriteDebug("Something went wrong during fetching Live Data from Tibber")
                    WriteDebug(str(e))
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


def UpdateDevice(Name, sValue):
    if Name == "Current Price":
        ID = 1
        Unit = ""
    if Name == "Mean Price":
        ID = 2
        Unit = ""
    if Name == "Current Price incl. fee":
        ID = 3
        Unit = ""
    if Name == "Minimum Price":
        ID = 4
        Unit = ""
    if Name == "Maximum Price":
        ID = 5
        Unit = ""
    if Name == "power":
        ID = 6
        Unit = ""
    if Name == "minPower":
        ID = 7
        Unit = ""
    if Name == "maxPower":
        ID = 8
        Unit = ""
    if Name == "averagePower":
        ID = 9
        Unit = ""
    if Name == "accumulatedCost":
        ID = 10
        Unit = ""
    if Name == "accumulatedConsumption":
        ID = 11
        Unit = ""
    if Name == "accumulatedProduction":
        ID = 12
        Unit = ""
    if Name == "powerProduction":
        ID = 13
        Unit = ""
    if Name == "accumulatedConsumptionLastHour":
        ID = 14
        Unit = ""
    if Name == "accumulatedProductionLastHour":
        ID = 15
        Unit = ""
    if Name == "accumulatedReward":
        ID = 16
        Unit = ""
    if Name == "minPower":
        ID = 17
        Unit = ""
    if Name == "averagePower":
        ID = 18
        Unit = ""
    if Name == "maxPower":
        ID = 19
        Unit = ""
    if Name == "lastMeterConsumption":
        ID = 20
        Unit = ""
    if Name == "powerReactive":
        ID = 21
        Unit = ""
    if Name == "powerProductionReactive":
        ID = 22
        Unit = ""
    if Name == "minPowerProduction":
        ID = 23
        Unit = ""
    if Name == "maxPowerProduction":
        ID = 24
        Unit = ""
    if Name == "powerFactor":
        ID = 25
        Unit = ""
    if Name == "voltagePhase1":
        ID = 26
        Unit = ""
    if Name == "voltagePhase2":
        ID = 27
        Unit = ""
    if Name == "voltagePhase3":
        ID = 28
        Unit = ""
    if Name == "currentL1":
        ID = 29
        Unit = ""
    if Name == "currentL2":
        ID = 30
        Unit = ""
    if Name == "currentL3":
        ID = 31
        Unit = ""

    if (ID in Devices):
        if Devices[ID].sValue != sValue:
            Devices[ID].Update(0, str(sValue))
            Domoticz.Log(Name+" Updated")
    if (ID not in Devices):
        Domoticz.Device(Name=Name, Unit=ID, TypeName="Custom", Used=1, Image=(_plugin.ImageID), Options={"Custom": "0;"+Unit}, Description="Desc").Create()
        Devices[ID].Update(nValue, str(sValue), Name=Name)

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)


def onMessage(Connection, Data):
    _plugin.onMessage(Connection, Data)


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
        if _plugin.CheckRealTimeHardware.Connected() or _plugin.CheckRealTimeHardware.Connecting():
            _plugin.CheckRealTimeHardware.Disconnect()
        if _plugin.GetHomeID.Connected() or _plugin.GetHomeID.Connecting():
            _plugin.GetHomeID.Disconnect()
        if _plugin.GetHouseNumber.Connected() or _plugin.GetHouseNumber.Connecting():
            _plugin.GetHouseNumber.Disconnect()
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
