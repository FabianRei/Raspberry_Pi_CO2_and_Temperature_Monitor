import board
import adafruit_dht

def get_temp_humidity():
    # Initialize the DHT22 sensor on GPIO14
    dhtDevice = adafruit_dht.DHT22(board.D14)
    
    try:
        # Try to get the temperature and humidity readings
        temperature = dhtDevice.temperature
        humidity = dhtDevice.humidity
        
        # Check if readings are valid and return them as a dictionary
        if humidity is not None and temperature is not None:
            return {'temperature': round(temperature, 2), 'humidity': round(humidity, 2)}
        else:
            print("Failed to retrieve data from humidity sensor")
            return {'temperature': None, 'humidity': None}

    except RuntimeError as error:
        # Handle errors that are common with DHT sensors
        print("Error reading data from the DHT sensor:", error.args[0])
        return {'temperature': None, 'humidity': None}

    finally:
        # Ensure the sensor is properly cleaned up
        dhtDevice.exit()

# Example of using the function
# sensor_data = get_temp_humidity()
# print(sensor_data)
