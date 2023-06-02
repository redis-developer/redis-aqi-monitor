#  cSpell:disable
from fastapi import FastAPI, Request
import os
from dateutil.parser import *
from datetime import *
import redis

TIMEFORMAT='%Y-%m-%d %H:%M:%S'
TIMEZONE_DIFF=5
redis = redis.Redis(
    host=os.getenv("AQI_HOST"), 
    port=os.getenv("AQI_PORT"), 
    password=os.getenv("AQI_PASS"), 
    decode_responses=True
)

app = FastAPI()

system_profile = {
  'active_sensors': {},
  'sensor_names': [],
  'active_since': datetime.now()
}

# returns information on the sensors connected to Redis
@app.get("/")
async def root():
  # fetch all active sensor keys
  active_sensors = redis.keys('ttl:*')
  # remove the tll prefix
  system_profile['sensor_names'] = []
  for sensor in active_sensors:
    system_profile['sensor_names'].append(sensor[4:])

  # get total count of active sensors
  system_profile['active_sensors'] = len(active_sensors)
  # get a sample of the last ten sensor readings
  system_profile['latest_10'] = redis.xrevrange('sensor:raw', '+','-' , 10)
  return {"response": system_profile}

# search endpoint for Grafana
@app.post("/search")
async def search(request: Request):
  body = await request.body()
  active_sensors = redis.keys('ttl:*')
  formatted_sensors = []

  for sensor in active_sensors:
    formatted_sensors.append(sensor[4:])
  # return a list of all active sensors to choose from
  return formatted_sensors
      
# returns an array of timestamps and values based on json request from Grafana
@app.post("/query")
async def query(request: Request):
  body = await request.json()
  targets = body['targets']
  response=[]
  # set up iterator to query for one or multiple TS and return in results_array
  for target_request in targets:
    target = target_request['target']
    from_time = body['range']['from']
    to_time = body['range']['to']
    interval = body['intervalMs']/100
    print(target)
    ts_key = f'ts:{target}:aqi'
    from_time = (parse(from_time) - timedelta(hours=TIMEZONE_DIFF)).strftime('%s')
    print(f'from_time: {from_time}')

    to_time = (parse(to_time) - timedelta(hours=TIMEZONE_DIFF)).strftime('%s')
    print(f'to_time: {to_time}')
    
    # request a specified range on timeseries
    results = redis.ts().range(ts_key, from_time, to_time, 
      aggregation_type='avg', 
      bucket_size_msec=int(interval))
    print('HIT RANGE')
    print(ts_key)
    print(results)
    # iterate through results, and prepare response payload 
    results_list = []
    for index, tuple in enumerate(results):
      graf_data = tuple[1]
      graf_stamp = int(tuple[0])*1000 # datetime.fromtimestamp(tuple[0]).strftime(TIMEFORMAT)
      results_list.append([graf_data, graf_stamp])
    response.append({'target' : target, 'datapoints' : results_list})
  
  print(response)
  return response
