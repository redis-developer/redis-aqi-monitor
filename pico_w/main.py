import machine
import network
import time
import secrets
import picoredis as client
import PMS5003
import utility

SENSOR_INTERVAL = 5 # seconds between each read
TTL_TIMER = 60 * SENSOR_INTERVAL # 5 minutes
SENSOR_LOCATION = 'office'
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

# Connect to Redis cloud database
r = client.Redis(host = secrets.REDIS_HOST, port = secrets.REDIS_PORT)
r.auth(secrets.REDIS_PASS)
r.set(f'ttl:{SENSOR_LOCATION}', 'active', 'EX', TTL_TIMER)

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
# main program for pico w
while True:
    # sends a status to Redis to indicate sensor is active
    if count_down_timer <= 5:
        r.set(f'ttl:{SENSOR_LOCATION}', 'active', 'EX', TTL_TIMER)
        count_down_timer = TTL_TIMER
        print('reset timer!')
    try:
        # read value from sensor
        aqi_reading= sensor.read()
        aqi_int = aqi_reading.pm_ug_per_m3(2.5, False)
        aqi = utility.convert(aqi_int)
        # read onboard temperature
        temperature_reading = utility.read_onboard_temp()
        # send readings to Redis via a stream add command
        results = r.xadd(
                    STREAM_KEY, 
                    '*', 
                    'target', SENSOR_LOCATION, 
                    'PM2.5', aqi_reading,
                    'AQI', aqi,
                    'temp', temperature_reading)
        print(results)        
    except:
        # handle any errors in adding to stream
        exception_status = str(wlan.status())
        print(f'Could not connect with status: {exception_status}')
    finally:
        # reattempt add in five seconds
        count_down_timer = count_down_timer - 5
        time.sleep(SENSOR_INTERVAL)
