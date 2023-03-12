import machine
import PMS5003

AQI_MATRIX = [
  {'C_LO': 0, 'C_HI': 12.0, 'I_LO': 0, 'I_HI': 50},
  {'C_LO': 12.1, 'C_HI': 35.4, 'I_LO': 51, 'I_HI': 100},
  {'C_LO': 35.5, 'C_HI': 55.4, 'I_LO': 101, 'I_HI': 150},
  {'C_LO': 55.5, 'C_HI': 150.4, 'I_LO': 151, 'I_HI': 200},
  {'C_LO': 150.5, 'C_HI': 250.4, 'I_LO': 201, 'I_HI': 300},
  {'C_LO': 250.5, 'C_HI': 350.4, 'I_LO': 301, 'I_HI': 400},
  {'C_LO': 350.5, 'C_HI': 500.4, 'I_LO': 401, 'I_HI': 500},
]

def convert_with_data(pm2_5, row):
  thresh = AQI_MATRIX[row]
  pt_1 = (thresh['I_HI'] - thresh['I_LO']) / (thresh['C_HI'] - thresh['C_LO'])
  pt_2 = pm2_5 - thresh['C_LO']
  aqi = int(pt_1 * pt_2 + thresh['I_LO'])
  return aqi

def convert(pm2_5):
  # determine which threshold to use for this concentration
  if  pm2_5 < 12:
    aqi = convert_with_data(pm2_5, 0)
  elif pm2_5 > 12.1 and pm2_5 < 35.4:
    aqi = convert_with_data(pm2_5, 1)
  elif pm2_5 > 35.5 and pm2_5 < 55.4:
    aqi = convert_with_data(pm2_5, 2)
  elif pm2_5 > 55.5 and pm2_5 < 150.4:
    aqi = convert_with_data(pm2_5, 3)
  elif pm2_5 > 150.5 and pm2_5 < 250.4:
    aqi = convert_with_data(pm2_5, 4)
  elif pm2_5 > 250.5 and pm2_5 < 350.4:
    aqi = convert_with_data(pm2_5, 5)
  elif pm2_5 > 350.5 and pm2_5 < 500.4:
    aqi = convert_with_data(pm2_5, 6)
    
  return aqi

def read_onboard_temp():
  sensor_temp = machine.ADC(4)
  conversion_factor = 3.3 / (65535)
  reading = sensor_temp.read_u16() * conversion_factor
  temperature = (reading - 0.706)/0.001721
  temperature = (temperature * 1.8) + 53.5
  temperature = round(temperature, 2) 
  return temperature