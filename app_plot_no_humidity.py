import datetime
from flask import Flask, render_template, send_file
from matplotlib.figure import Figure
import io
from mod_co2modnitor import get_all
# from general_humidity_sensor_dht22 import get_temp_humidity  # <--- DISABLED
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import sqlite3
import matplotlib.dates as mdates


app = Flask(__name__)


def get_latest_record():
    conn = sqlite3.connect('sensor_data.db')
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT time, temperature, co2, humidity FROM measurements ORDER BY time DESC LIMIT 1')
        last_record = cursor.fetchone()
    except sqlite3.OperationalError:
        # If table doesn't exist, create it
        cursor.execute('''
        CREATE TABLE measurements (
            time DATETIME PRIMARY KEY,
            temperature REAL,
            co2 REAL,
            humidity REAL
        )
        ''')
        conn.commit()
        last_record = None
    conn.close()
    return last_record


def initialize_averages():
    global avg_temp, avg_co2
    last_record = get_latest_record()
    if last_record:
        # We still unpack 4 values because the DB has 4 columns, but we ignore humidity
        _, avg_temp, avg_co2, _ = last_record
    else:
        avg_temp = 0  
        avg_co2 = 0   


def fetch_sensor_data():
    global avg_temp, avg_co2
    global last_raw_temp, last_raw_co2

    co2_data = get_all('/dev/hidraw0')
    
    # Humidity is completely ignored now
    
    if co2_data is not None:
        # Update moving average
        avg_temp = alpha * co2_data['Temperature'] + (1 - alpha) * avg_temp
        avg_co2 = alpha * co2_data['CO2'] + (1 - alpha) * avg_co2

        # Store last raw measurement
        last_raw_temp = co2_data['Temperature']
        last_raw_co2 = co2_data['CO2']


def write_sensor_data():
    with sqlite3.connect('sensor_data.db') as conn:
        cursor = conn.cursor()
        # We write 'None' into the humidity column to keep the DB structure valid
        cursor.execute('''
        INSERT INTO measurements (time, temperature, co2, humidity)
        VALUES (?, ?, ?, ?)
        ''', (datetime.datetime.now(), avg_temp, avg_co2, None))
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
    if not times: 
        return
    time_range = max(times) - min(times)

    if time_range <= datetime.timedelta(hours=6):
        interval = 1
    else:
        interval_hours = (time_range.total_seconds() // 3600) // 6
        interval = max(1, int(interval_hours))

    locator = mdates.HourLocator(interval=interval)
    formatter = mdates.DateFormatter('%H:%M')
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    fig.autofmt_xdate()


# Define alpha and initialize moving averages
alpha = 0.2
avg_temp = 0
avg_co2 = 0

# Define globals for last raw measurement
last_raw_temp = None
last_raw_co2 = None

# Initialize moving averages with the latest record
initialize_averages()

# Fetch and write the first sensor data
fetch_sensor_data()
write_sensor_data()

# Scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=fetch_sensor_data, trigger="interval", minutes=1)
scheduler.add_job(func=write_sensor_data, trigger="interval", minutes=5)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())


@app.route('/')
def index():
    # 1. Fetch the last AVERAGE record from the database
    last_avg_record = get_latest_record()
    if last_avg_record:
        _, avg_temp_db, avg_co2_db, _ = last_avg_record
        avg_temp = round(float(avg_temp_db), 2)
        avg_co2 = round(float(avg_co2_db), 2)
    else:
        avg_temp, avg_co2 = 'N/A', 'N/A'

    # 2. Access the global RAW variables from memory
    global last_raw_temp, last_raw_co2
    raw_temp = round(last_raw_temp, 2) if last_raw_temp is not None else 'N/A'
    raw_co2 = round(last_raw_co2, 2) if last_raw_co2 is not None else 'N/A'

    # 3. Pass data to template - REMOVED HUMIDITY ARGUMENTS
    return render_template(
        'index_css.html',
        last_temperature=avg_temp,
        last_co2=avg_co2,
        raw_temperature=raw_temp,
        raw_co2=raw_co2
        # humidity arguments deleted
    )

@app.route('/plot/temperature')
def plot_temperature():
    records = get_records_for_plotting(select_columns='time, temperature', time_period_hours=24)
    times, temperatures = zip(*records) if records else ([], [])
    times = [datetime.datetime.fromisoformat(t) for t in times]
    fig = Figure()
    ax = fig.subplots()
    ax.plot(times, temperatures)
    set_x_ticks(fig, ax, times)
    ax.set_title('Temperature over the last 24 hours')
    ax.set_xlabel('Time')
    ax.set_ylabel('Temperature (°C)')
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/plot/co2')
def plot_co2():
    records = get_records_for_plotting(select_columns='time, co2', time_period_hours=24)
    times, co2_levels = zip(*records) if records else ([], [])
    times = [datetime.datetime.fromisoformat(t) for t in times]
    fig = Figure()
    ax = fig.subplots()
    ax.plot(times, co2_levels)
    set_x_ticks(fig, ax, times)
    ax.set_title('CO2 Levels over the last 24 hours')
    ax.set_xlabel('Time')
    ax.set_ylabel('CO2 (ppm)')
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

# REMOVED @app.route('/plot/humidity') entirely

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
