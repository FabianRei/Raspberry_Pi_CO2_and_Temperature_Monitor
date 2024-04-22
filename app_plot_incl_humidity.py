import datetime
from flask import Flask, render_template, send_file
from matplotlib.figure import Figure
import io
from mod_co2modnitor import get_all
from general_humidity_sensor_dht22 import get_temp_humidity
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import sqlite3
import matplotlib.dates as mdates


app = Flask(__name__)


def get_latest_record():
    conn = sqlite3.connect('sensor_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT time, temperature, co2, humidity FROM measurements ORDER BY time DESC LIMIT 1')
    last_record = cursor.fetchone()
    conn.close()
    return last_record


def initialize_averages():
    global avg_temp, avg_co2, avg_humidity
    last_record = get_latest_record()
    if last_record:
        _, avg_temp, avg_co2, avg_humidity = last_record
    else:
        avg_temp = 0  # or some default/placeholder value
        avg_co2 = 0   # or some default/placeholder value
        avg_humidity = 0  # Default value


def fetch_sensor_data():
    global avg_temp, avg_co2, avg_humidity
    co2_data = get_all('/dev/hidraw0')
    humidity_data = get_temp_humidity()  # Assuming this function returns {'temperature': float, 'humidity': float}

    if co2_data is not None:
        avg_temp = alpha * co2_data['Temperature'] + (1 - alpha) * avg_temp
        avg_co2 = alpha * co2_data['CO2'] + (1 - alpha) * avg_co2

    if humidity_data is not None and humidity_data['humidity'] is not None:
        avg_humidity = alpha * humidity_data['humidity'] + (1 - alpha) * avg_humidity


def write_sensor_data():
    with sqlite3.connect('sensor_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO measurements (time, temperature, co2, humidity)
        VALUES (?, ?, ?, ?)
        ''', (datetime.datetime.now(), avg_temp, avg_co2, avg_humidity))
        conn.commit()


def get_records_for_plotting(select_columns='*', time_period_hours=24):
    one_day_ago = datetime.datetime.now() - datetime.timedelta(hours=time_period_hours)
    one_day_ago_str = one_day_ago.strftime('%Y-%m-%d %H:%M:%S')

    conn = sqlite3.connect('sensor_data.db')
    cursor = conn.cursor()
    query = f'''
        SELECT {select_columns} FROM measurements 
        WHERE time >= ? 
        ORDER BY time ASC
    '''
    cursor.execute(query, (one_day_ago_str,))
    records = cursor.fetchall()
    conn.close()
    return records


def set_x_ticks(fig, ax, times):
    # Determine the range of data
    time_range = max(times) - min(times)
    
    # Calculate the number of intervals based on the range
    if time_range <= datetime.timedelta(hours=6):
        # If the range is less than 6 hours, show all hours
        interval = 1
    else:
        # Calculate interval to show a maximum of 6 ticks
        interval_hours = (time_range.total_seconds() // 3600) // 6
        interval = max(1, int(interval_hours))

    # Set the locator and formatter
    locator = mdates.HourLocator(interval=interval)
    formatter = mdates.DateFormatter('%H:%M')

    # Apply the locator and formatter
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    # Rotate the dates for better readability
    fig.autofmt_xdate()


# Define alpha and initialize moving averages
alpha = 0.2  # Example value, adjust as needed
avg_temp = 0
avg_co2 = 0
avg_humidity = 0

# Initialize moving averages with the latest record
initialize_averages()

# Fetch and write the first sensor data
fetch_sensor_data()
write_sensor_data()

# Scheduler to fetch data every minute and write data every 5 minutes
scheduler = BackgroundScheduler()
scheduler.add_job(func=fetch_sensor_data, trigger="interval", minutes=1)
scheduler.add_job(func=write_sensor_data, trigger="interval", minutes=5)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

@app.route('/')
def index():
    # Fetch the last record from the database
    last_record = get_latest_record()

    # If there's no data, use 'N/A'
    if last_record:
        last_time, last_temperature, last_co2, last_humidity = last_record
        last_temperature = round(float(last_temperature), 2)
        last_co2 = round(float(last_co2), 2)
        last_humidity = round(float(last_humidity), 2) if last_humidity is not None else 'N/A'
    else:
        last_time, last_temperature, last_co2, last_humidity = 'N/A', 'N/A', 'N/A', 'N/A'

    return render_template('index_css.html', last_temperature=last_temperature, last_co2=last_co2, last_humidity=last_humidity)

@app.route('/plot/temperature')
def plot_temperature():
    # Fetch temperature data for plotting
    records = get_records_for_plotting(select_columns='time, temperature', time_period_hours=24)
    # Unpack the records into separate lists for time and temperature
    times, temperatures = zip(*records) if records else ([], [])
    # Convert strings to datetime objects
    times = [datetime.datetime.fromisoformat(t) for t in times]

    # Generate a plot of temperature over time
    fig = Figure()
    ax = fig.subplots()
    ax.plot(times, temperatures)
    set_x_ticks(fig, ax, times)  # Call the function to set the x-axis ticks
    ax.set_title('Temperature over the last 24 hours')
    ax.set_xlabel('Time')
    ax.set_ylabel('Temperature (°C)')
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/plot/co2')
def plot_co2():
    # Fetch CO2 data for plotting
    records = get_records_for_plotting(select_columns='time, co2', time_period_hours=24)
    # Unpack the records into separate lists for time and CO2 levels
    times, co2_levels = zip(*records) if records else ([], [])
    # Convert strings to datetime objects
    times = [datetime.datetime.fromisoformat(t) for t in times]
    # Generate a plot of CO2 over time
    fig = Figure()
    ax = fig.subplots()
    ax.plot(times, co2_levels)
    set_x_ticks(fig, ax, times)  # Call the function to set the x-axis ticks
    ax.set_title('CO2 Levels over the last 24 hours')
    ax.set_xlabel('Time')
    ax.set_ylabel('CO2 (ppm)')
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/plot/humidity')
def plot_humidity():
    # Fetch humidity data for plotting
    records = get_records_for_plotting(select_columns='time, humidity', time_period_hours=24)
    # Unpack the records into separate lists for time and humidity
    times, humidities = zip(*records) if records else ([], [])
    # Convert strings to datetime objects
    times = [datetime.datetime.fromisoformat(t) for t in times]

    # Generate a plot of humidity over time
    fig = Figure()
    ax = fig.subplots()
    ax.plot(times, humidities)
    set_x_ticks(fig, ax, times)  # Call the function to set the x-axis ticks

    ax.set_title('Humidity over the Last 24 Hours')
    ax.set_xlabel('Time')
    ax.set_ylabel('Humidity (%)')

    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

