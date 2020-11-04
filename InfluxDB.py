# Created by Daniel Nilsson
# Please use my invite-link to help me with my work, we get 500skr each :)
# https://tibber.com/se/invite/8af85f51
# Version 1.0
# Script to fetch hourly prices fro Tibber and store the data into InfluxDB

import json,datetime,requests # import libraries

headers = {
    'Authorization': 'Bearer xxxxxxxxx', # replace xxxxxxxxx with your Tibber Token
    'Content-Type': 'application/json',
}

data = '{ "query": "{viewer {homes {currentSubscription {priceInfo {today {total startsAt }}}}}}" }' # asking for today's hourly prices

response = requests.post('https://api.tibber.com/v1-beta/gql', headers=headers, data=data) # make the query to Tibber
response = response._content # selecting the important data from the response
parsed = json.loads(response) # parse it so we can use it easier
file = open("input.txt", "w") # create a file to store the data
file.writelines(["# DML","\n# CONTEXT-DATABASE: Tibber\n\n"]) # write some important text in the file
for data in parsed["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]["today"]:
  time = data["startsAt"]
  utctime = str(datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S%z").timestamp())[:-2]
  total = str(round(day["total"]*100,2))
  f1.writelines(["El Pris=",total," ",utc,"\n"])
file.close()
