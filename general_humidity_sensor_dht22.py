import time
import board
import adafruit_dht

def get_temp_humidity():
    max_attempts = 20  # 20 attempts, each with a 0.1-second delay will cover 2 seconds

    for attempt in range(max_attempts):
        # Initialize the DHT22 sensor on GPIO14 within the loop
        dhtDevice = adafruit_dht.DHT22(board.D14)

        try:
            # Try to get the temperature and humidity readings
            temperature = dhtDevice.temperature
            humidity = dhtDevice.humidity

            # Check if readings are valid and return them as a dictionary
            if humidity is not None and temperature is not None:
                return {'temperature': round(temperature, 2), 'humidity': round(humidity, 2)}

        except RuntimeError as error:
            # Print the error and retry after 0.1 seconds
            print(f"Attempt {attempt + 1}: Error reading data from the DHT sensor:", error.args[0])
            time.sleep(0.1)

        finally:
            # Ensure the sensor is properly cleaned up after each attempt
            dhtDevice.exit()

    # If all attempts fail, return None values
    print("Failed to retrieve data from humidity sensor after multiple attempts.")
    return {'temperature': None, 'humidity': None}

# Example of using the function
sensor_data = get_temp_humidity()
print(sensor_data)

