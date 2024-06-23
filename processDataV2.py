#import extensions
from flask import Flask, jsonify, render_template
import serial.tools.list_ports
import time
from collections import deque
import threading
import firebase_admin
from firebase_admin import credentials, db

#intialize connection with database
cred = credentials.Certificate('/Users/jessica/Documents/vscode/crisislab/serviceAccountKey.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://crisislab24-default-rtdb.firebaseio.com/'
})
ref = db.reference('data/threshold')

app = Flask(__name__)

ports = serial.tools.list_ports.comports()
serialInst = serial.Serial()
portList = []

#constants
THRESHOLD = 2 #CHANGE TO THRESHOLD ON DAY
AIRPRES = 101300

#list avaliable ports in terminal
for onePort in ports:
    portList.append(str(onePort))
    print(str(onePort))

serialInst.baudrate = 115200
serialInst.port = '/dev/cu.usbserial-110'
serialInst.open()

#set max points on graph
max_points = 30
heights = deque(maxlen=max_points)
timestamps = deque(maxlen=max_points)
pressures = deque(maxlen=max_points)

start_time = time.time()

skip_initial_readings = 2
readings_counter = 0
initial_height = None

def read_serial_data():
    global readings_counter, initial_height
    while True:
        if serialInst.in_waiting:
            packet = serialInst.readline()
            decoded_packet = packet.decode('utf').strip()

            try:
                numeric_value = int(''.join(filter(str.isdigit, decoded_packet)))
                rawHeight = (((((numeric_value) - AIRPRES) / (997 * 9.81)) * 100) + 1)
                height = round(rawHeight, 0)
                rawPressure = numeric_value
                pressure = round(rawPressure, 0)

                #skip first couple of readings
                if readings_counter < skip_initial_readings:
                    readings_counter += 1
                    continue

                #set initial height of water
                if initial_height is None:
                    initial_height = height

                #if height meets threshold write to DB
                if height >= (initial_height + THRESHOLD):
                    thresholdMet = True
                    ref.set(thresholdMet)
                    heights.append(height)
                    pressures.append(pressure)
                    timestamps.append(time.time() - start_time)
                else:
                    heights.append(height)
                    pressures.append(pressure)
                    timestamps.append(time.time() - start_time)

            except ValueError:
                print("Received non-numeric data:", decoded_packet)

serial_thread = threading.Thread(target=read_serial_data)
serial_thread.daemon = True
serial_thread.start()

#save and show data on graphs
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    dynamic_threshold = (THRESHOLD + initial_height)
    print('THRESHOLD=', dynamic_threshold)
    return jsonify({
        'timestamps': list(timestamps), 
        'heights': list(heights),
        'threshold': dynamic_threshold,
        'pressures': list(pressures) 
    })

if __name__ == '__main__':
    app.run(debug=True)
