#  cSpell:disable
import os
from redis import Redis

STREAM_KEY = "sensor:raw"
RETENTION = 1000*60*60*24*3 # 3 days of milliseconds

redis = Redis(host=os.getenv("AQI_HOST"), 
  port=os.getenv("AQI_PORT"),
  password=os.getenv("AQI_PASS"),
  decode_responses=True)

stream_entry_id = '$'

while(True):
  
  # read newest result from stream  
  result = redis.xread(block=50000, streams={STREAM_KEY: stream_entry_id})

  payload = result[0][1][0] # payload for stream entry 1678071037305-0
  # extract values form payload
  timestamp = payload[0][:10] # stream id without the segment: 1678071037305
  print(timestamp)
  ts_key_prefix = f'ts:{payload[1]["target"]}'
  sensor_values = payload[1]

  try:
    # create three separate timeseries entries from each stream entry
    ts_entry_aqi = redis.ts().add(f'{ts_key_prefix}:aqi',
      timestamp,
      sensor_values["AQI"],
      retention_msecs=RETENTION,
      duplicate_policy='first')
    
    ts_entry_pm25 = redis.ts().add(f'{ts_key_prefix}:pm',
      timestamp,
      sensor_values["PM2.5"],
      retention_msecs=RETENTION,
      duplicate_policy='first')

    ts_entry_temp = redis.ts().add(f'{ts_key_prefix}:temp',
      timestamp,
      sensor_values["temp"],
      retention_msecs=RETENTION,
      duplicate_policy='first')

  except Exception as err:
    # report any errors in adding to timeseries
    print(f'Unexpected {err}, {type(err)}')
    
  finally:
    # update last stream entry id for next iteration
    stream_entry_id = result[0][1][0][0]