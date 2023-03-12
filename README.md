# Redis AQI Monitor

This repository is a suite of scripts intended to demonstrate the capabilities of Redis Stack with IoT. Sensor readings are stored in a Redis Stream data structure and fan out to TimeSeries and JSON documents.

## Filesystem

There are three top-level folders used for different aspects of the process of gathering and interpreting sensor data:
- :open_file_folder: `pico_w`: this houses the code that is installed in the Raspberry Pico W unit
- :open_file_folder: `consumer`: this contains services to consume data from the main stream data structure of sensor readings and create other data structures, such as a TimeSeries or JSON
- :open_file_folder: `api`: this is a fastAPI server that serves relevant sensor data to Grafana. It also has sample query endpoints to demonstrate the JSON query capabilities


## Hardware Overview
A Raspberry Pi Pico W compute unit, essentially a microcontroller capable of running a truncated version of Python, is wired to a readily-available air particulate sensor. The sensor specifically returns an array of particulate matter density per cubic meter. For this application, particulate matter of 2.5 microns or smaller was chosen as a metric to track. This size range is the largest threat to human health during times of wildfires and heavy air pollution.

The Pico W unit has onboard wireless capabilities and requires approximately 4.5 volts to operate; this means it can operate on batteries anywhere within range of a wireless access point.

## Software Overview

### The portable sensor unit
The Pico W unit, with the installed software within this project, records particulate value readings every five seconds. The value is also converted to the standard AQI value most commonly seen in in online air quality maps, such as PurpleAir.com. The Pico W also has an onboard temperature sensor, so a temperature reading is recorded as well for additional data tracking.

These three values are sent to a stream data structure housed in a cloud instance of Redis. A cloud infrastructure was chosen to ensure high-availability to any sensor connected to the internet; there is no need for a local machine serving Redis.

### Consumers of the stream data structure
Sources that send data to a stream are called *producers*. A producer can be a sensor, another Redis data structure, even another Stream. Services that process data from the stream are called *consumers*. 

In this project, two consumers run continuously. 

The `consumer_ts.py` script reads each entry from the stream (`sensor:raw`) and adds the values to a respective TimeSeries data structure. `temp`, `pm2_5`, and `aqi` are each added to their respective timeseries instances.

```python
result = redis.xread(
  streams={STREAM_KEY: last_stream_entry_id},
  count=1,
  block=50000)

payload = result[0][1][0] # payload for stream entry 1678071037305-0
# extract values form payload
timestamp = payload[0][:13] # stream id without the segment: 1678071037305
target = payload[1]['target']
pm2_5 = payload[1]['PM2.5']
aqi =  payload[1]['AQI']
temp =  payload[1]['temp']

# establish timeseries key prefix for target location
ts_key_prefix = f'ts:{target}'

try:
  # create three separate timeseries entries from each stream entry
  ts_entry_temp = redis.ts().add(f'{ts_key_prefix}:aqi', timestamp[:10], aqi, duplicate_policy='first')
  ts_entry_pm25 = redis.ts().add(f'{ts_key_prefix}:pm', timestamp[:10], pm2_5, duplicate_policy='first')
  ts_entry_temp = redis.ts().add(f'{ts_key_prefix}:pm', timestamp[:10], temp, duplicate_policy='first')
```

The `consumer_json.py` file also reads each entry from the stream and updates a JSON document dedicated to each sensor location. A text message alert system is also included within this file to deploy third party notifications when the AQI value has crossed a defined threshold after one minute.

```python
result = r.json().set(json_key, '.', 
  { 'timestamp': timestamp,
    'current_pm2_5': pm2_5, 
    'current_temp': temp, 
    'current_aqi': aqi, 
    'last_12': last_12})
```

There is a rolling list property within each JSON document called `last_12`. This is an array of the last 12 AQI readings, comprising a snapshot of 1 minute of time. If the sum of all AQI readings within this array is above a defined threshold, then the text message alert is sent. This assumes that there is a consistent trend of higher AQI than normal and that the user should be alerted. Once a text message is sent, a temporary variable `user_notified` is created that acts as a boolean block for text messages being sent numerous times. A sensible default of one hour exists between text notifications.

```python
location_json = r.json().get(json_key)

# if we need to create this JSON document, populate the array
if location_json is None:
  last_12 = [0,0,0,0,0,0,0,0,0,0,0,0]
else:
  last_12 = location_json['last_12']

last_12.append(aqi)
last_12.pop(0)
sum_last_12 = sum(last_12)

# alert if threshold is crossed:
if sum_last_12 >= AQI_THRESHOLD:
  aqi_average = floor(sum_last_12/12)
  has_been_notified = r.get('user_notified')
  if not has_been_notified:
    alert(aqi_average, target)
    r.set('user_notified', 1, 3600)
```


### Serving the sensor data

This project contains a fastAPI webserver under the folder `api`. There are several routes used by Grafana for displaying all available timeseries endpoints and the actual payloads of coordinates for plotting.  Here are the endpoints:

| method | endpoint  | purpose |
|--------|-----------|---------|
| `GET`  | `/`       | returns a JSON object of all sensors and a sample of the last ten entries in the stream of sensor readings |
| `GET`  | `/json/query/{sensor}/aqi?min=int&max=int` | example of the query capabilities Redis implements upon JSON documents. This endpoint returns a specified sensor's readings where the aqi **value** is between `min` and `max`
| `POST` | `/query` | part of an autocomplete feature within Grafana that returns an array of available sensors |
| `POST` | `/search` | receives a JSON request from Grafana's SimpleJSON plugin and returns an array of one or more readings of sensors based on a given time frame

The Simple JSON plugin for Grafana allows for a quick way to integrate the timeseries data. After receiving a request from Grafana for a specified time window, one or more locations, and the interval of data points, the `RANGE` command is executed to retrieve the values and timestamps:

```python
  for target_request in targets:
    target = target_request['target']
    from_time = body['range']['from']
    to_time = body['range']['to']
    interval = body['intervalMs']/100

    ts_key = f'ts:{target}:aqi'
    from_time = (parse(from_time) - timedelta(hours=8)).strftime('%s')
    to_time = (parse(to_time) - timedelta(hours=8)).strftime('%s')
    
    # request a specified range on timeseries
    results = redis.ts().range(ts_key, 
      from_time, 
      to_time, 
      aggregation_type='avg', 
      bucket_size_msec=int(interval))
```

