import datetime
from flask import Flask, render_template, send_file
from matplotlib.figure import Figure
import io
from mod_co2modnitor import get_all
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import sqlite3
import matplotlib.dates as mdates


app = Flask(__name__)

# In-memory storage for sensor data
sensor_data = []

# Function to fetch and store data
def fetch_sensor_data():
    global sensor_data
    data = get_all('/dev/hidraw0')
    if data is not None:
        with sqlite3.connect('sensor_data.db') as conn:
            cursor = conn.cursor()
            # Insert the sensor data into the measurements table
            cursor.execute('''
            INSERT INTO measurements (time, temperature, co2)
            VALUES (?, ?, ?)
            ''', (datetime.datetime.now(), data['Temperature'], data['CO2']))
            conn.commit()

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


# Functions to fetch data from the database

def get_latest_record():
    conn = sqlite3.connect('sensor_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT time, temperature, co2 FROM measurements ORDER BY time DESC LIMIT 1')
    last_record = cursor.fetchone()
    conn.close()
    return last_record


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


@app.route('/')
def index():
    # Fetch the last record from the database
    last_record = get_latest_record()

    # If there's no data, use 'N/A'
    if last_record:
        last_time, last_temperature, last_co2 = last_record
        last_temperature = round(float(last_temperature), 2)
    else:
        last_time, last_temperature, last_co2 = 'N/A', 'N/A', 'N/A'
    
    return render_template('index.html', last_temperature=last_temperature, last_co2=last_co2)


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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

