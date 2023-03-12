#  cSpell:disable
import os
from redis import Redis

STREAM_KEY = "sensor:raw"

redis = Redis(host=os.getenv("REDIS_HOST"), 
  port=os.getenv("REDIS_PORT"),
  password=os.getenv("REDIS_PASS"),
  decode_responses=True)

stream_entry_id = redis.get("ts_stream_entry_id")

while(True):
  # read first result from stream  
  result = redis.xread(
    streams={STREAM_KEY: stream_entry_id},
    count=1,
    block=50000)

  payload = result[0][1][0] # payload for stream entry 1678071037305-0
  # extract values form payload
  timestamp = payload[0][:10] # stream id without the segment: 1678071037305
  ts_key_prefix = f'ts:{payload[1]["target"]}'
  sensor_values = payload[1]

  try:
    # create three separate timeseries entries from each stream entry
    ts_entry_temp = redis.ts().add(f'{ts_key_prefix}:aqi', 
      timestamp,sensor_values["AQI"], 
      duplicate_policy='first')
    
    ts_entry_pm25 = redis.ts().add(f'{ts_key_prefix}:pm',
      timestamp, 
      sensor_values["PM2.5"], 
      duplicate_policy='first')
    
    ts_entry_temp = redis.ts().add(f'{ts_key_prefix}:temp', 
      timestamp,
      sensor_values["temp"],
      duplicate_policy='first')

  except Exception as err:
    # report any errors in adding to timeseries
    print(f'Unexpected {err}, {type(err)}')
    
  finally:
    # update last stream entry id for next iteration
    stream_entry_id = result[0][1][0][0]
    redis.set('ts_stream_entry_id', stream_entry_id)
