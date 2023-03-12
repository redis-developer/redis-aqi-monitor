import os
from alert import alert
from redis import Redis
from math import floor

STREAM_KEY = 'sensor:raw'
AQI_THRESHOLD = 100*12

r = Redis(host=os.getenv('REDIS_HOST'), 
  port=os.getenv('REDIS_PORT'),
  password=os.getenv('REDIS_PASS'),
  decode_responses=True)

# placeholder if there is a pause in consumer service
json_stream_entry_id = r.get('json_stream_entry_id')

while(True):
  # read first result from stream that receives raw sensor data
  result = r.xread(streams={STREAM_KEY: json_stream_entry_id},
    count=1,
    block=50000)

  # extract values from result
  entry_stream_id = result[0][1][0][0]
  timestamp = int(result[0][1][0][0][:13])
  sensor_readings = result[0][1][0][1]
  
  target = sensor_readings["target"]
  json_key = f'json:{target}'

  pm2_5 = int(sensor_readings["PM2.5"])
  temp = float(sensor_readings["temp"])
  aqi = int(sensor_readings["AQI"])

  # check for 12 * 5 second threshold readings in a row (1 minute)
  location_json = r.json().get(json_key)
  # if a json object has not yet been made, create an array
  if location_json is None:
    last_12 = [0,0,0,0,0,0,0,0,0,0,0,0]
  else:
    last_12 = location_json['last_12']
  
  # "slide" out the oldest reading, add the newest
  last_12.append(aqi)
  last_12.pop(0)

  # alert if threshold is crossed:
  if sum(last_12) >= AQI_THRESHOLD:
    aqi_average = floor(sum(last_12)/12)
    has_been_notified = r.get('user_notified')
    if not has_been_notified:
      alert(aqi_average, target)
      r.set('user_notified', 1, 3600)

  # create a new JSON document or update an existing one
  try:
    result = r.json().set(json_key, '.', 
      { 'timestamp': timestamp,
        'current_pm2_5': pm2_5, 
        'current_temp': temp, 
        'current_aqi': aqi, 
        'last_12': last_12
      })

  except:
    print(f'Error:\nkey: {json_key}')
  finally:
    # update entry_stream_id so we know where to pull the next entry
    last_entry = int(entry_stream_id[14:])+1
    new_stream_id = f'{entry_stream_id[:14]}{last_entry}'
    r.set('json_stream_entry_id', new_stream_id)
    json_stream_entry_id = new_stream_id
