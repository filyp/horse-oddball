# %%
# pin is 123
# other_dev = MyDevice("00:07:80:0F:2F:EF")

from collections import deque
import inspect
import socket
import sys
import threading
from queue import Queue
import traceback

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

import plux


def signal_int_to_volts(signal_int):
    vcc = 3.3
    Geeg = 41782  # sensor gain
    return (signal_int / (2**16) - 1 / 2) * vcc / Geeg


class RealtimePlotter:
    def __init__(self, buffer_size=5000):
        # Create the application and window
        self.app = pg.mkQApp()
        self.win = pg.GraphicsLayoutWidget()
        self.win.setWindowTitle('Real-time Plot')
        self.win.resize(1000, 800)
        
        # Create the time series plot
        self.plot = self.win.addPlot(title='Time Series Data')
        self.plot.setLabel('left', 'Amplitude')
        self.plot.setLabel('bottom', 'Samples')
        self.plot.showGrid(x=True, y=True)
        self.plot.setYRange(-40e-6, 40e-6)
        
        # Add FFT plot below
        self.win.nextRow()
        self.fft_plot = self.win.addPlot(title='Frequency Spectrum')
        self.fft_plot.setLabel('left', 'Magnitude')
        self.fft_plot.setLabel('bottom', 'Frequency (Hz)')
        self.fft_plot.showGrid(x=True, y=True)
        self.fft_plot.setYRange(0, 0.01)
        
        # Initialize data buffer and curves
        self.data_buffer = deque(maxlen=buffer_size)
        for _ in range(buffer_size):
            self.data_buffer.append(0)
        self.curve = self.plot.plot(pen='y')
        self.fft_curve = self.fft_plot.plot(pen='c')
        
        # Setup timer for updates
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(60)  # 50ms update rate
        
        self.win.show()

    def update_data(self, new_data):
        """Add new data point to the plot"""
        self.data_buffer.append(new_data)

    def update_plot(self):
        """Update both the time series plot and FFT plot"""
        # Update time series plot
        data_list = list(self.data_buffer)
        self.curve.setData(data_list)
        
        # Compute and update FFT
        n_samples = 1000
        recent_data = data_list[-n_samples:]
        if len(recent_data) == n_samples:
            # Apply Hanning window to reduce spectral leakage
            window = np.hanning(n_samples)
            windowed_data = recent_data * window
            
            # Compute FFT
            fft_data = np.fft.rfft(windowed_data)  # rfft is more efficient for real signals
            fft_freq = np.fft.rfftfreq(n_samples, d=1/1000)
            
            # Only plot frequencies up to 60Hz
            freq_mask = fft_freq <= 60
            fft_freq = fft_freq[freq_mask]
            fft_magnitude = np.abs(fft_data)[freq_mask]
            
            # Update FFT plot
            self.fft_curve.setData(fft_freq, fft_magnitude)


# %%
class MyDevice(plux.MemoryDev):
    lastSeq = 0

    def onRawFrame(self, nSeq, data):
        volt_data = [signal_int_to_volts(d) for d in data]
        # print(nSeq, volt_data)
        # if nSeq % 10 == 0:
        plotter.update_data(volt_data[0])

        if nSeq - self.lastSeq > 1:
            print("ZGUBIONE FREJMY:", nSeq - self.lastSeq)
        self.lastSeq = nSeq
        return stop

    def onEvent(self, event):
        print("Event:", type(event), end=" ")
        print({k: v for k, v in inspect.getmembers(event) if not k.startswith("_")})

        if type(event) == plux.Event.Disconnect:
            print("Disconnect event - Reason:", event.reason)
            return True
        else:
            return stop


# %%
stop = False
plotter = RealtimePlotter()
# print("Found devices: ", plux.BaseDev.findDevices())
dev = MyDevice("00:07:80:58:9B:B4")  # MAC address of device
print("Properties:", dev.getProperties())

def run_plux():
    try:
        dev.start(1000, 15, 16)
        dev.loop()
    except Exception as e:
        print(e)
        traceback.print_exc()

plux_thread = threading.Thread(target=run_plux, daemon=True)
plux_thread.start()

# blocking - QT event loop must run in the main thread
# it waits until the window is closed
plotter.app.exec()

print("Closing")
stop = True
plux_thread.join()
dev.stop()
dev.close()

# %%
