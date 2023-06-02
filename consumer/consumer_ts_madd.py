#  cSpell:disable
import os
from redis import Redis

STREAM_KEY = "sensor:raw"

redis = Redis(host=os.getenv("REDIS_HOST"), 
  port=os.getenv("REDIS_PORT"),
  password=os.getenv("REDIS_PASS"),
  decode_responses=True)

stream_entry_id = redis.get("ts_stream_entry_id") or 0

  # read first result from stream  
result = redis.xread(streams={STREAM_KEY: stream_entry_id}, block=50000)

stream_results = result[0][1]

ts_madd_array = []

redis.ts().create('ts:unit_1:temp', duplicate_policy= 'first')
redis.ts().create('ts:unit_1:aqi', duplicate_policy= 'first')
redis.ts().create('ts:unit_1:pm', duplicate_policy= 'first')

# redis.ts().create('ts:livingroom:temp', DUPLICATE_POLICY= 'first')
# redis.ts().create('ts:livingroom:aqi', DUPLICATE_POLICY= 'first')
# redis.ts().create('ts:livingroom:pm', DUPLICATE_POLICY= 'first')

for entry in stream_results:
      target = f'ts:{entry[1]["target"]}'
      print(target)
      my_tuple = (f'{target}:aqi', entry[0][:10], entry[1]['AQI'])
      ts_madd_array.append(my_tuple)

      my_tuple = (f'{target}:temp', entry[0][:10], entry[1]['temp'])
      ts_madd_array.append(my_tuple)

      my_tuple = (f'{target}:pm', entry[0][:10], entry[1]['PM2.5'])
      ts_madd_array.append(my_tuple)


print(ts_madd_array)
results = redis.ts().madd(ts_madd_array)
print(results)
