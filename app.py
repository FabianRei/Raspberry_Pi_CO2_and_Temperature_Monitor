from flask import Flask, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# Import the get_all function from your module
from mod_co2modnitor import get_all

app = Flask(__name__)

# Function to fetch and store data
def fetch_sensor_data():
    global sensor_data
    sensor_data = get_all('/dev/hidraw0')

# Initially fetch data
fetch_sensor_data()

# Scheduler to fetch data every five minutes
scheduler = BackgroundScheduler()
scheduler.add_job(func=fetch_sensor_data, trigger="interval", minutes=5)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

@app.route('/')
def index():
    # Render the HTML template with the last fetched sensor data
    temperature = round(sensor_data['Temperature'], 2)
    co2 = sensor_data['CO2']
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CO2 and Temperature</title>
    </head>
    <body>
        <h1>Current Readings</h1>
        <p>Temperature: {{ temperature }}°C</p>
        <p>CO2: {{ co2 }} ppm</p>
    </body>
    </html>
    """
    return render_template_string(html_template, temperature=temperature, co2=co2)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

