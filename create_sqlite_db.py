import sqlite3

# Connect to the SQLite database (it will be created if it doesn't exist)
conn = sqlite3.connect('sensor_data.db')

# Create a cursor object using the cursor method
cursor = conn.cursor()

# Create table
cursor.execute('''
               CREATE TABLE IF NOT EXISTS measurements (
               time TEXT,
               temperature REAL,
               co2 INTEGER
                )
               ''')

# Commit the changes and close the connection
conn.commit()
conn.close()

