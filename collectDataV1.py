import serial.tools.list_ports
import time
import matplotlib.pyplot as plt
from collections import deque
import numpy as np
from scipy.interpolate import make_interp_spline
import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate('/Users/jessica/Documents/vscode/crisislab/serviceAccountKey.json')

firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://crisislab24-default-rtdb.firebaseio.com/'
})

ref = db.reference('threshold/')

ports = serial.tools.list_ports.comports()
serialInst = serial.Serial()

portList = []

for onePort in ports:
    portList.append(str(onePort))
    print(str(onePort))

serialInst.baudrate = 115200
serialInst.port = '/dev/cu.usbserial-110'
serialInst.open()

max_points = 10
heights = deque(maxlen=max_points)
timestamps = deque(maxlen=max_points)

#CHANGE TO THRESHOLD ON THE DAY
THRESHOLD = 1
AIRPRES = 102392

start_time = time.time()

plt.ion()
fig, ax = plt.subplots()
line, = ax.plot([], [], marker='o')
ax.set_xlabel('Time (s)')
ax.set_ylabel('Height (m)')
ax.set_title('Height vs Time')
ax.grid(True)

ax.axhline(y=THRESHOLD, color='r', linestyle='-')
ax.annotate('Threshold', xy=(0.02, 0.95), xycoords='axes fraction', color='r', fontsize=10, fontweight='bold', bbox=dict(facecolor='white', alpha=0.8))

skip_initial_readings = 2
readings_counter = 0

while True:
    if serialInst.in_waiting:
        packet = serialInst.readline()
        decoded_packet = packet.decode('utf').strip()

        print(decoded_packet,"hPa")

        try:
            numeric_value = int(''.join(filter(str.isdigit, decoded_packet)))
            print(numeric_value)
            rawHeight = (((((numeric_value) - AIRPRES) / (997 * 9.81)) * 100) + 1)
            height = round(rawHeight, 2)
            print(height,"cm")

            if readings_counter < skip_initial_readings:
                readings_counter += 1
                continue

            if height >= THRESHOLD:
                thresholdMet = True
                #ref.set(thresholdMet)
                heights.append(height)
                timestamps.append(time.time() - start_time)
                print('data written')
                
                #update the plot
                line.set_xdata(timestamps)
                line.set_ydata(heights)
                ax.relim()
                ax.autoscale_view()
                plt.draw()
                plt.pause(0.01)

            else:
                heights.append(height)
                timestamps.append(time.time() - start_time)

                #update the plot
                line.set_xdata(timestamps)
                line.set_ydata(heights)
                ax.relim()
                ax.autoscale_view()
                plt.draw()
                plt.pause(0.01)
            
            ax.relim()
            ax.autoscale_view()
            plt.draw()
            plt.pause(0.01)
            
        except ValueError:
            print("recieved non-numeric data: ", decoded_packet)

        except KeyboardInterrupt:
            print("data collection as stopped")
            plt.ioff()
            plt.show()
