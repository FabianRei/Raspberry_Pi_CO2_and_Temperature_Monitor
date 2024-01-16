import datetime
from flask import Flask, render_template, send_file
from matplotlib.figure import Figure
import io
from mod_co2modnitor import get_all
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)

# In-memory storage for sensor data
sensor_data = []

# Function to fetch and store data
def fetch_sensor_data():
    global sensor_data
    data = get_all('/dev/hidraw0')
    if data is not None:
        # Append the new data point with the current timestamp
        sensor_data.append({'time': datetime.datetime.now(), 'data': data})
        # Keep only the last 24 hours of data
        one_day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
        sensor_data = [point for point in sensor_data if point['time'] > one_day_ago]

# Fetch the first sensor data
fetch_sensor_data()

# Scheduler to fetch data every five minutes
scheduler = BackgroundScheduler()
scheduler.add_job(func=fetch_sensor_data, trigger="interval", minutes=5)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

@app.route('/')
def index():
    # Pass the last recorded values to the template
    last_record = sensor_data[-1]['data'] if sensor_data else {'Temperature': 'N/A', 'CO2': 'N/A'}
    return render_template('index.html', last_temperature=round(last_record['Temperature'], 2), last_co2=last_record['CO2'])

@app.route('/plot/temperature')
def plot_temperature():
    # Generate a plot of temperature over time
    fig = Figure()
    ax = fig.subplots()
    times = [point['time'] for point in sensor_data]
    temperatures = [point['data']['Temperature'] for point in sensor_data]
    ax.plot(times, temperatures)
    ax.set_title('Temperature over the last 24 hours')
    ax.set_xlabel('Time')
    ax.set_ylabel('Temperature (°C)')
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/plot/co2')
def plot_co2():
    # Generate a plot of CO2 over time
    fig = Figure()
    ax = fig.subplots()
    times = [point['time'] for point in sensor_data]
    co2_levels = [point['data']['CO2'] for point in sensor_data]
    ax.plot(times, co2_levels)
    ax.set_title('CO2 Levels over the last 24 hours')
    ax.set_xlabel('Time')
    ax.set_ylabel('CO2 (ppm)')
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

