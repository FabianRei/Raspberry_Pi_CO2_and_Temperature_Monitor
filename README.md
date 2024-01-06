# Raspberry Pi CO2 and Temperature Monitor

This repository contains a modified version of the CO2 and temperature monitoring script originally found in [JsBergbau's TFACO2AirCO2ntrol_CO2Meter](https://github.com/JsBergbau/TFACO2AirCO2ntrol_CO2Meter) repository. The original `co2monitor.py` script has been adapted into `mod_co2modnitor.py` and integrated into a Flask web application for real-time data visualization.

## Modifications

- **mod_co2modnitor.py**: Adapted from `co2monitor.py`, this module contains the logic for interfacing with the CO2 monitor device and retrieving sensor data.

- **Flask Web Application (`app.py`)**: A simple web application developed with Flask to display real-time CO2 and temperature readings. The application runs a background task to fetch sensor data every five minutes, reducing the load on the Raspberry Pi Zero.

## Setup and Usage

1. **Install Flask**: Ensure Flask is installed on your Raspberry Pi. If not, install it using `pip3 install Flask`.

2. **Run the Application**: Start the Flask server by running `python3 app.py` in the terminal. This will host the web application on your Raspberry Pi's IP address, accessible via port 5000.

3. **View Data**: Open a web browser and navigate to `http://<raspberry-pi-ip>:5000` to view the current CO2 and temperature readings.

## Requirements

- A Raspberry Pi (tested on Raspberry Pi Zero W; performance issues noted)
- The CO2 monitor device compatible with the original script
- Python 3 installed on the Raspberry Pi
- Flask installed on the Raspberry Pi

## Notes

- This application is designed for personal, non-commercial use.
- The Flask server is configured for development and should not be used in a production environment.
- Due to performance constraints on the Raspberry Pi Zero W, especially with graph plotting libraries, future development may involve upgrading to a more capable Raspberry Pi model.

