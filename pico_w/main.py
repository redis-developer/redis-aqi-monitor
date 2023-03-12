#  cSpell:disable
import machine
import network
import time
import secrets
import picoredis as client
import PMS5003
import utility

SENSOR_INTERVAL = 5 # seconds between each air sensor reading
TTL_TIMER = 60 * 5 # 5 minutes between each ping for liveness
SENSOR_LOCATION = 'bedroom'
STREAM_KEY = 'sensor:raw'

# connect to WIFI
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(secrets.WIFI_SSD, secrets.WIFI_PASS)

max_wait = 10
while max_wait > 0:
  if wlan.status() < 0 or wlan.status() >= 3:
    break
  max_wait -= 1
  print('Connecting to WIFI...')
  time.sleep(1)

if wlan.status() != 3:
  raise RuntimeError('Network connection failed')
else:
  connection_info = wlan.ifconfig()
  print(f'Connected with IP: {connection_info[0]}')

# Connect to RedisCloud database
redis = client.Redis(
  host = secrets.REDIS_HOST, 
  port = secrets.REDIS_PORT)
redis.auth(secrets.REDIS_PASS)

# Initial announcement that we exist
redis.set(f'ttl:{SENSOR_LOCATION}', 'active', 'EX', TTL_TIMER)

# Select pins for connecting to sensor
UART_connection = machine.UART(
  1, 
  tx=machine.Pin(8),
  rx=machine.Pin(9),
  baudrate=9600)

# Connect to sensor
sensor = PMS5003.PMS5003(
  uart=UART_connection,
  pin_enable=machine.Pin(3),
  pin_reset=machine.Pin(2),
  mode="active")

count_down_timer = TTL_TIMER

# loop that will run while the Pico W has power
while True:
  # announce our existence one interval before timer reaches zero
  if count_down_timer <= SENSOR_INTERVAL:
    redis.set(f'ttl:{SENSOR_LOCATION}', 'active', 'EX', TTL_TIMER)
    count_down_timer = TTL_TIMER
  try:
    # read values from sensor
    raw_reading = sensor.read()
    aqi_int = raw_reading.pm_ug_per_m3(2.5, False)
    aqi = utility.convert(aqi_int)
    temperature_reading = utility.read_onboard_temp()
    
    # send readings to Redis via a stream add command
    results = redis.XADD(STREAM_KEY, 
      '*', 
      'target', SENSOR_LOCATION, 
      'PM2.5', raw_reading,
      'AQI', aqi,
      'temp', temperature_reading)
    
    print(f'Stream Entry ID: {results}  AQI: {aqi}')
  
  except Exception as err:
    # report any errors in adding to stream
    print(f'Unexpected {err}, {type(err)}')

  finally:
    # reduce the countdown timer
    count_down_timer = count_down_timer - SENSOR_INTERVAL
    # sleep until time to read again
    time.sleep(SENSOR_INTERVAL)



{
  
'target': 'office',
'PM2.5': 4,
'AQI': 16,
'temp': 67.75

  
  }