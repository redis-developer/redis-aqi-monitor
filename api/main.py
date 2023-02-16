from fastapi import FastAPI, Request
import os
from dateutil.parser import *
from datetime import *
import redis

r = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), password=os.getenv("REDIS_PASS"))

app = FastAPI()

temp_readings = {
    'sensors': {},
    'active_since': datetime.now()
}

@app.get("/")
async def root():
    latest_10 = r.xrevrange('sensor:raw', '+','-' , 10)
    print(latest_10)
    temp_readings['latest_10'] = latest_10
    return {"response": temp_readings}

@app.post("/search")
async def search(request: Request):
    body = await request.body()
    # todo poll for all keys with prefix 'ttl:<target>' and convert the result into a list of active sensors
    return ['bedroom', 'solarium', 'livingroom', 'bathroom', 'kitchen', 'office', 'spare-bedroom', 'foyer', 'upper_stairs']
    
# Translates JSON query to TS query
@app.post("/query")
async def query(request: Request):
    body = await request.json()
    results_list = []
    # set up iterator to query multiple TS and return in results_array
    targets = body['targets']
    for target_request in targets:
        target = target_request['target']
        from_time = body['range']['from']
        from_time = (parse(from_time) - timedelta(hours=8)).strftime('%s')

        to_time = body['range']['to']
        to_time = (parse(to_time) - timedelta(hours=8)).strftime('%s')

        interval = body['intervalMs']/100
        ts_key = f'ts:{target}:pm'
        results = r.ts().range(ts_key, from_time, to_time, aggregation_type='avg', bucket_size_msec=int(interval))

        for index, tuple in enumerate(results):
            grafana_datapoint = tuple[1]
            grafana_timestamp = datetime.fromtimestamp(tuple[0]).strftime('%Y-%m-%d %H:%M:%S')
            results_list.append([grafana_datapoint, grafana_timestamp])
            
    response = [{
                        'target' : target,
                        'datapoints' : results_list
                }]

    return response