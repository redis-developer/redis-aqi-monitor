import os
from redis import Redis

STREAM_KEY = 'sensor:raw'

r = Redis(host=os.getenv('REDIS_HOST'), 
        port=os.getenv('REDIS_PORT'),
        password=os.getenv('REDIS_PASS'),
        decode_responses=True)

last_stream_entry_id = 0
first_run = True

while(True):
    # read first result from stream     
    result = r.xread(streams={STREAM_KEY: last_stream_entry_id}, count=1, block=50000)
    payload = result[0][1][0]
    # extract timestamp, particulate, and temperature
    timestamp = payload[0][:13]
    target = payload[1]['target']
    pm2_5 = payload[1]['PM2.5']
    temp =  payload[1]['temp']
    
    # establish timeseries key prefix for target location
    ts_key_prefix = f'ts:{target}'
    
    if first_run:
        # check if key exists
        ts_exists = r.exists(f'{ts_key_prefix}:temp')
        print(ts_exists)
        if ts_exists:
            # get last processed stream entry id to send back to start converting from last task
            last_stream_entry_id = r.get(f'{ts_key_prefix}:last_id_converted')

        else:
            # create timeseries for both temperature and particulate count with the appropriate label 
            r.ts().create(f'{ts_key_prefix}:temp',  duplicate_policy='FIRST')
            r.ts().create(f'{ts_key_prefix}:pm',  duplicate_policy='FIRST')
        
        first_run = False
    try:
        ts_entry = r.ts().add(f'{ts_key_prefix}:temp', timestamp[:10], temp)
        ts_entry = r.ts().add(f'{ts_key_prefix}:pm', timestamp[:10], pm2_5)

    except:
        print(f'Error:\nkey: {ts_key_prefix}\ntimestamp: {timestamp}, {temp}')
    finally:
        last_stream_entry_id = result[0][1][0][0]
        r.set(f'{ts_key_prefix}:last_id_converted', last_stream_entry_id)
