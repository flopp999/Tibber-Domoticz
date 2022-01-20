# Tibber Python Plugin
#
# Author: flopp999
#
"""
<plugin key="Tibber" name="Tibber API 1.11" author="flopp999" version="1.11" wikilink="https://github.com/flopp999/Tibber-Domoticz" externallink="https://tibber.com/se/invite/8af85f51">
    <description>
        <h2>Tibber API is used to fetch data from Tibber.com</h2><br/>
        <h2>Support me with a coffee &<a href="https://www.buymeacoffee.com/flopp999">https://www.buymeacoffee.com/flopp999</a></h2><br/>
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Fetch current price excluding taxes, minimum power, maximum power, average power, accumulated cost and accumulated consumption, this will happen every hour at minute 0</li>
            <li>Fetch today's minimum, maximum and mean price including taxes, this will happen 10 minutes past midnight</li>
            <li>Fetch current Power(watt) every 30 seconds if you have Tibber Watty/Pulse installed</li>
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

MissingPackage = []

import traceback, sys

try:
    from datetime import datetime
except ImportError:
    Package = False

try:
    import requests, json, os, logging, asyncio
except ImportError as error:
    MissingPackage.append(error)
    Package = False

try:
    from logging.handlers import RotatingFileHandler
except ImportError:
    MissingPackage.append(error)
    Package = False

try:
    from gql import Client, gql
except ImportError:
    MissingPackage.append(error)
    Package = False

try:
    from gql.transport.websockets import WebsocketsTransport
except ImportError as error:
    MissingPackage.append(error)
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
        self.Subscription = ""
        self.Count = 0

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

        if os.path.isfile(dir+'/Tibber.zip'):
            if "Tibber" not in Images:
                Domoticz.Image("Tibber.zip").Create()
            self.ImageID = Images["Tibber"].ID

        if Package is False:
            Domoticz.Error("Missing packages")
            Domoticz.Error(str(MissingPackage))

        self.GetHomeID = Domoticz.Connection(Name="Get HomeID", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")
        if not _plugin.GetHomeID.Connected() and not _plugin.GetHomeID.Connecting() and not self.HomeID and Package:
            _plugin.GetHomeID.Connect()

        self.GetHouseNumber = Domoticz.Connection(Name="Get House Number", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")
        if not _plugin.GetHouseNumber.Connected() and not _plugin.GetHouseNumber.Connecting() and self.HomeID and Package:
            _plugin.GetHouseNumber.Connect()

        self.CheckRealTimeHardware = Domoticz.Connection(Name="Check Real Time Hardware", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")

        self.GetDataCurrent = Domoticz.Connection(Name="Get Current", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")
        self.GetSubscription = Domoticz.Connection(Name="Get Subscription", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")

        self.GetDataMiniMaxMean = Domoticz.Connection(Name="Get MiniMaxMean", Transport="TCP/IP", Protocol="HTTPS", Address="api.tibber.com", Port="443")

    def onConnect(self, Connection, Status, Description):
        if CheckInternet() is True and self.AllSettings is True:
            if (Status == 0):
                if Connection.Name == ("Get HomeID"):
                    data = '{ "query": "{viewer {homes {id}}}" }'  # asking for HomeID
                    Connection.Send({'Verb': 'POST', 'URL': '/v1-beta/gql', 'Headers': self.headers, 'Data': data})

                elif Connection.Name == ("Get House Number"):
                    data = '{ "query": "{viewer {homes {id}}}" }'  # asking for all homids
                    Connection.Send({'Verb': 'POST', 'URL': '/v1-beta/gql', 'Headers': self.headers, 'Data': data})

                elif Connection.Name == ("Get Subscription"):
                    data = '{ "query": "{viewer {homes {currentSubscription{status}}}}" }'  # asking subscription
                    Connection.Send({'Verb': 'POST', 'URL': '/v1-beta/gql', 'Headers': self.headers, 'Data': data})

                elif Connection.Name == ("Get Current"):
                    data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {current {total }}}}}}" }'  # asking for this hourly price
                    Connection.Send({'Verb': 'POST', 'URL': '/v1-beta/gql', 'Headers': self.headers, 'Data': data})

                elif Connection.Name == ("Get MiniMaxMean"):
                    data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {today {total }}}}}}" }'  # asking for this hourly price
                    Connection.Send({'Verb': 'POST', 'URL': '/v1-beta/gql', 'Headers': self.headers, 'Data': data})

                elif Connection.Name == ("Check Real Time Hardware"):
                    data = '{ "query": "{viewer {homes {id,features {realTimeConsumptionEnabled}}}}" }'  # check if Real Time hardware is installed
                    Connection.Send({'Verb': 'POST', 'URL': '/v1-beta/gql', 'Headers': self.headers, 'Data': data})


    def onMessage(self, Connection, Data):
        Status = int(Data["Status"])

        if (Status == 200):
            Data = Data['Data'].decode('UTF-8')
            Data = json.loads(Data)

            if "errors" in Data:
                Domoticz.Error(str(Data["errors"][0]["extensions"]["code"]))

            elif Connection.Name == ("Get HomeID"):

                for each in Data["data"]["viewer"]["homes"]:
                    Domoticz.Log("Home "+str(self.House)+" has ID = "+str(each["id"]))
                self.HomeID = Data["data"]["viewer"]["homes"][self.House]["id"]
                WriteDebug("HomeID collected")
                _plugin.GetHomeID.Disconnect()
                _plugin.GetHouseNumber.Connect()

            elif Connection.Name == ("Get House Number"):
#                Domoticz.Log(str(data))

                if 'errors' in Data:
                    self.AllSettings = False
                    Domoticz.Error(str(Data["errors"][0]["message"]))
                else:
#                    Domoticz.Log(str(data))

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
                _plugin.GetSubscription.Connect()

            elif Connection.Name == ("Get Subscription"):
                self.Subscription = Data["data"]["viewer"]["homes"][0]["currentSubscription"]["status"]
                if self.Subscription == "ended":
                    Domoticz.Log("Subscription not found")
                if self.Subscription == "running":
                    _plugin.GetDataCurrent.Connect()
                _plugin.GetSubscription.Disconnect()

            elif Connection.Name == ("Get Current"):
#                _plugin.GetDataCurrent.Disconnect()
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
#                _plugin.GetDataCurrent.Disconnect()
                _plugin.GetDataMiniMaxMean.Connect()

            elif Connection.Name == ("Get MiniMaxMean"):
                MiniMaxPrice = []
                MeanPrice = float(0)
                for each in Data["data"]["viewer"]["homes"][self.House]["currentSubscription"]["priceInfo"]["today"]:
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
        self.Count += 1
        Domoticz.Log(str(self.Count))
        Domoticz.Log(str(self.RealTime))
        Domoticz.Log(str(self.AllSettings))
        Domoticz.Log(str(Package))

        if self.Count == 1 and self.RealTime is True and self.AllSettings is True and Package is True:
            WriteDebug("onHeartbeatLivePower")
            Domoticz.Log("LiveOnheart")

            async def LivePower():
                transport = WebsocketsTransport(url='wss://api.tibber.com/v1-beta/gql/subscriptions', headers={'Authorization': self.AccessToken})
                try:
                    async with Client(transport=transport, fetch_schema_from_transport=True, execute_timeout=9) as session:
                        query = gql("subscription{liveMeasurement(homeId:\"" + self.HomeID + "\"){power, minPower, maxPower, lastMeterConsumption, powerReactive, powerFactor, averagePower}}")
                        result = await session.execute(query)
                        Domoticz.Log(str(result))
                        for name,value in result["liveMeasurement"].items():
                            if value is not None:
                                UpdateDevice(str(name), str(value))
                    self.LiveDataUpdated = True
                    Domoticz.Log("Live power updated")
#                except transport.exceptions.TransportQueryError as e:
#                    Domoticz.Log("timeout")
#                    Domoticz.Log(str(e))
#                except Exception as e:
                except gql.transport.exceptions.TransportQueryError as e:
                    Domoticz.Error("Transporterror")
                except ssl.SSLWantReadError as e:
                    Domoticz.Error("SSLWanr")
                except Exception as e:
                    Domoticz.Error(str(traceback.format_exc()))
                    Domoticz.Error(str(sys.exc_info()[0]))
                    WriteDebug("Something went wrong during fetching Live Data from Tibber")
                    WriteDebug(str(e))
                    pass



            asyncio.run(LivePower())

        if self.Count == 2 and self.RealTime is True and self.AllSettings is True and Package is True:
            WriteDebug("onHeartbeatLiveProduction")
            async def LiveProduction():
                transport = WebsocketsTransport(url='wss://api.tibber.com/v1-beta/gql/subscriptions', headers={'Authorization': self.AccessToken})
                try:
                    async with Client(transport=transport, fetch_schema_from_transport=True, execute_timeout=15) as session:
                        query = gql("subscription{liveMeasurement(homeId:\"" + self.HomeID + "\"){powerProduction, minPowerProduction, maxPowerProduction, lastMeterProduction, powerProductionReactive}}")
                        result = await session.execute(query)
                        for name,value in result["liveMeasurement"].items():
                            if value is not None:
                                UpdateDevice(str(name), str(value))
                    self.LiveDataUpdated = True
                    Domoticz.Log("Live production updated")
#                except transport.exceptions.TransportQueryError as e:
#                    Domoticz.Log("timeout")
#                    Domoticz.Log(str(e))
#                except Exception as e:
                except Exception as e:
                    Domoticz.Log(str(traceback.format_exc()))
                    Domoticz.Log(str(sys.exc_info()[0]))
                    WriteDebug("Something went wrong during fetching Live Data from Tibber")
                    WriteDebug(str(e))
                    pass
            asyncio.run(LiveProduction())

        if self.Count == 3 and self.RealTime is True and self.AllSettings is True and Package is True:
            WriteDebug("onHeartbeatLiveOther")
            async def LiveOther():
                transport = WebsocketsTransport(url='wss://api.tibber.com/v1-beta/gql/subscriptions', headers={'Authorization': self.AccessToken})
                try:
                    async with Client(transport=transport, fetch_schema_from_transport=True, execute_timeout=15) as session:
                        query = gql("subscription{liveMeasurement(homeId:\"" + self.HomeID + "\"){voltagePhase1, voltagePhase2, voltagePhase3, currentL1, currentL2, currentL3, signalStrength}}")
                        result = await session.execute(query)
                        for name,value in result["liveMeasurement"].items():
                            if value is not None:
                                UpdateDevice(str(name), str(value))
                    self.LiveDataUpdated = True
                    Domoticz.Log("Live other updated")
#                except transport.exceptions.TransportQueryError as e:
#                    Domoticz.Log("timeout")
#                    Domoticz.Log(str(e))
#                except Exception as e:
                except Exception as e:
                    Domoticz.Log(str(traceback.format_exc()))
                    Domoticz.Log(str(sys.exc_info()[0]))
                    WriteDebug("Something went wrong during fetching Live Data from Tibber")
                    WriteDebug(str(e))
                    pass
            asyncio.run(LiveOther())


#        if self.Count == 1 and MinuteNow < 59 and self.LiveDataUpdated is False and self.RealTime is True and self.AllSettings is True:
        if self.Count == 4 and self.RealTime is True and self.AllSettings is True and Package is True:
            WriteDebug("onHeartbeatLiveAccumulation")

            async def LiveAccumulation():
                transport = WebsocketsTransport(url='wss://api.tibber.com/v1-beta/gql/subscriptions', headers={'Authorization': self.AccessToken})
                try:
                    async with Client(transport=transport, fetch_schema_from_transport=True, execute_timeout=15) as session:
                        query = gql("subscription{liveMeasurement(homeId:\"" + self.HomeID + "\"){accumulatedConsumption, accumulatedProduction, accumulatedConsumptionLastHour, accumulatedProductionLastHour, accumulatedCost, accumulatedReward}}")
                        result = await session.execute(query)
                        for name,value in result["liveMeasurement"].items():
                            if value is not None:
                                UpdateDevice(str(name), value)
                    self.LiveDataUpdated = True
                    Domoticz.Log("Live accumulation updated")
                except Exception as e:
                    Domoticz.Log(str(traceback.format_exc()))
                    Domoticz.Log(str(sys.exc_info()[0]))
                    WriteDebug("Something went wrong during fetching Live Data from Tibber")
                    WriteDebug(str(e))
                    pass

            asyncio.run(LiveAccumulation())
            self.Count = 0

        if MinuteNow == 17 or MinuteNow == 59 and self.LiveDataUpdated is True:
            self.LiveDataUpdated = False

        if MinuteNow < 59 and self.CurrentPriceUpdated is False and self.Subscription is True:
            if not _plugin.GetDataCurrent.Connected() and not _plugin.GetDataCurrent.Connecting():
                WriteDebug("onHeartbeatGetDataCurrent")
                _plugin.GetDataCurrent.Connect()
        if MinuteNow == 59 and self.CurrentPriceUpdated is True:
            self.CurrentPriceUpdated = False

        if HourNow >= 0 and MinuteNow >= 10 and MinuteNow < 59 and self.MiniMaxMeanPriceUpdated is False and self.Subscription is True:
            if not _plugin.GetDataMiniMaxMean.Connected() and not _plugin.GetDataMiniMaxMean.Connecting():
                WriteDebug("onHeartbeatGetDataMiniMaxMean")
                _plugin.GetDataMiniMaxMean.Connect()
        if HourNow == 23 and MinuteNow == 59 and self.MiniMaxMeanPriceUpdated is True:
            self.MiniMaxMeanPriceUpdated = False


global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def LivePower():
    async def LivePower():
        Domoticz.Log("Live")
        transport = WebsocketsTransport(url='wss://api.tibber.com/v1-beta/gql/subscriptions', headers={'Authorization': self.AccessToken})
        try:
            async with Client(transport=transport, fetch_schema_from_transport=True, execute_timeout=9) as session:
                query = gql("subscription{liveMeasurement(homeId:\"" + self.HomeID + "\"){power, minPower, maxPower, lastMeterConsumption, powerReactive, powerFactor, averagePower}}")
                result = await session.execute(query)
                for name,value in result["liveMeasurement"].items():
                    if value is not None:
                        UpdateDevice(str(name), str(value))
            self.LiveDataUpdated = True
            Domoticz.Log("Live power updated")
#                except transport.exceptions.TransportQueryError as e:
#                    Domoticz.Log("timeout")
#                    Domoticz.Log(str(e))
#                except Exception as e:
        except Exception as e:
            Domoticz.Log(str(traceback.format_exc()))
            Domoticz.Log(str(sys.exc_info()[0]))
            WriteDebug("Something went wrong during fetching Live Data from Tibber")
            WriteDebug(str(e))
            pass
    asyncio.run(LivePower())



def UpdateDevice(Name, sValue):
    if Name == "Current Price":
        ID = 1
        Unit = ""
    elif Name == "Mean Price":
        ID = 2
        Unit = ""
    elif Name == "Current Price incl. fee":
        ID = 3
        Unit = ""
    elif Name == "Minimum Price":
        ID = 4
        Unit = ""
    elif Name == "Maximum Price":
        ID = 5
        Unit = ""
    elif Name == "power":
        ID = 6
        Unit = "W"
    elif Name == "minPower":
        ID = 7
        Unit = "W"
    elif Name == "maxPower":
        ID = 8
        Unit = "W"
    elif Name == "averagePower":
        ID = 9
        Unit = "W"
    elif Name == "accumulatedCost":
        ID = 10
        Unit = ""
    elif Name == "accumulatedConsumption":
        ID = 11
        Unit = "kWh"
    elif Name == "accumulatedProduction":
        ID = 12
        Unit = "kWh"
    elif Name == "powerProduction":
        ID = 13
        Unit = "kWh"
    elif Name == "accumulatedConsumptionLastHour":
        ID = 14
        Unit = "kWh"
    elif Name == "accumulatedProductionLastHour":
        ID = 15
        Unit = "kWh"
    elif Name == "accumulatedReward":
        ID = 16
        Unit = "kWh"
    elif Name == "signalStrength":
        ID = 17
        Unit = "dBm or %"
    elif Name == "lastMeterConsumption":
        ID = 20
        Unit = "kWh"
    elif Name == "powerReactive":
        ID = 21
        Unit = "VAR"
    elif Name == "powerProductionReactive":
        ID = 22
        Unit = "VAR"
    elif Name == "minPowerProduction":
        ID = 23
        Unit = "W"
    elif Name == "maxPowerProduction":
        ID = 24
        Unit = "W"
    elif Name == "powerFactor":
        ID = 25
        Unit = "kW"
    elif Name == "voltagePhase1":
        ID = 26
        Unit = "V"
    elif Name == "voltagePhase2":
        ID = 27
        Unit = "V"
    elif Name == "voltagePhase3":
        ID = 28
        Unit = "V"
    elif Name == "currentL1":
        ID = 29
        Unit = "A"
    elif Name == "currentL2":
        ID = 30
        Unit = "A"
    elif Name == "currentL3":
        ID = 31
        Unit = "A"
    elif Name == "lastMeterProduction":
        ID = 32
        Unit = ""
    else:
        Domoticz.Error(Name)

    if (ID not in Devices):
        Domoticz.Device(Name=Name, Unit=ID, TypeName="Custom", Used=1, Image=(_plugin.ImageID), Options={"Custom": "0;"+Unit}, Description="Desc").Create()

    if (ID in Devices):
        if Devices[ID].sValue != sValue:
            Devices[ID].Update(0, str(sValue))

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
        requests.get(url='https://api.tibber.com/', timeout=2)
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
