from fastapi import FastAPI, Request
import os
from dateutil.parser import *
from datetime import *
import redis

TIMEFORMAT = '%Y-%m-%d %H:%M:%S'

redis = redis.Redis(
    host=os.getenv("REDIS_HOST"), 
    port=os.getenv("REDIS_PORT"), 
    password=os.getenv("REDIS_PASS"), 
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
  results_list = []
  targets = body['targets']

  # set up iterator to query for one or multiple TS and return in results_array
  for target_request in targets:
    target = target_request['target']
    from_time = body['range']['from']
    to_time = body['range']['to']
    interval = body['intervalMs']/100

    ts_key = f'ts:{target}:aqi'
    from_time = (parse(from_time) - timedelta(hours=8)).strftime('%s')
    to_time = (parse(to_time) - timedelta(hours=8)).strftime('%s')
    
    # request a specified range on timeseries
    results = redis.ts().range(ts_key, from_time, to_time, 
      aggregation_type='avg', 
      bucket_size_msec=int(interval))

    # iterate through results, and prepare response payload 
    for index, tuple in enumerate(results):
      graf_data = tuple[1]
      graf_stamp = datetime.fromtimestamp(tuple[0]).strftime(TIMEFORMAT)
      results_list.append([graf_data, graf_stamp])
      
  response = [{'target' : target, 'datapoints' : results_list}]

  return response
