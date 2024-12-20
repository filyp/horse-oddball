# %%
# pin is 123
import inspect
import os
import socket
import sys
import threading
import traceback
from collections import deque
from datetime import datetime
from queue import Queue

import mne
import numpy as np
import pyqtgraph as pg
from mne.io import RawArray
from pyqtgraph.Qt import QtCore

import plux

num_electrodes = 3
sample_rate = 1000
mac_address = "00:07:80:58:9B:B4"
# the other one: "00:07:80:0F:2F:EF"

# Create a buffer to store data before saving
data_buffer = []

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
        self.win.resize(1800, 800)  # Increased width to accommodate 3 columns
        
        # Create lists to store plots and curves for each electrode
        self.plots = []
        self.fft_plots = []
        self.curves = []
        self.fft_curves = []
        self.data_buffers = []
        
        # Create 3 columns of plots (one for each electrode)
        for i in range(num_electrodes):
            # Time series plot (row 0, column i)
            plot = self.win.addPlot(row=0, col=i, title=f'Time Series Data - Electrode {i+1}')
            plot.setLabel('left', 'Amplitude')
            plot.setLabel('bottom', 'Samples')
            plot.showGrid(x=True, y=True)
            plot.setYRange(-40e-6, 40e-6)
            self.plots.append(plot)
            
            # FFT plot (row 1, column i)
            fft_plot = self.win.addPlot(row=1, col=i, title=f'Frequency Spectrum - Electrode {i+1}')
            fft_plot.setLabel('left', 'Magnitude')
            fft_plot.setLabel('bottom', 'Frequency (Hz)')
            fft_plot.showGrid(x=True, y=True)
            fft_plot.setYRange(0, 0.01)
            self.fft_plots.append(fft_plot)
            
            # Initialize data buffer and curves for this electrode
            data_buffer = deque(maxlen=buffer_size)
            for _ in range(buffer_size):
                data_buffer.append(0)
            self.data_buffers.append(data_buffer)
            
            # Create curves
            self.curves.append(plot.plot(pen='y'))
            self.fft_curves.append(fft_plot.plot(pen='c'))
        
        # Setup timer for updates
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(60)
        
        self.win.show()

    def update_data(self, new_data):
        """Add new data points to the plots"""
        # new_data should be a list of 3 values, one for each electrode
        for i, value in enumerate(new_data):
            self.data_buffers[i].append(value)

    def update_plot(self):
        """Update both the time series plots and FFT plots for all electrodes"""
        for i in range(num_electrodes):
            # Update time series plot
            data_list = list(self.data_buffers[i])
            self.curves[i].setData(data_list)
            
            # Compute and update FFT
            n_samples = 1000
            recent_data = data_list[-n_samples:]
            if len(recent_data) == n_samples:
                # Apply Hanning window to reduce spectral leakage
                window = np.hanning(n_samples)
                windowed_data = recent_data * window
                
                # Compute FFT
                fft_data = np.fft.rfft(windowed_data)
                fft_freq = np.fft.rfftfreq(n_samples, d=1/sample_rate)
                
                # Only plot frequencies up to 60Hz
                freq_mask = fft_freq <= 60
                fft_freq = fft_freq[freq_mask]
                fft_magnitude = np.abs(fft_data)[freq_mask]
                
                # Update FFT plot
                self.fft_curves[i].setData(fft_freq, fft_magnitude)


# %%
class MyDevice(plux.MemoryDev):
    lastSeq = 0

    def onRawFrame(self, nSeq, data):
        global data_buffer
        volt_data = [signal_int_to_volts(d) for d in data]
        volt_data = volt_data[:num_electrodes]

        # Store data for BDF file (only the first num_electrodes channels)
        data_buffer.append(volt_data)
        
        # Update plotter as before
        plotter.update_data(volt_data)

        # check for lost frames
        if nSeq - self.lastSeq > 1:
            print("ZGUBIONE FREJMY:", nSeq - self.lastSeq)
        self.lastSeq = nSeq
        return stop

    def onEvent(self, event):
        """Close the loop if device disconnected. In case of other events, print them."""
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
dev = MyDevice(mac_address)
print("Properties:", dev.getProperties())

def run_plux():
    try:
        dev.start(sample_rate, 15, 16)   # 1000 Hz, ports 1-8, 16 bits
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


# Convert buffer to numpy array (channels x samples)
data = np.array(data_buffer).T

# Initialize MNE info structure
info = mne.create_info(
    ch_names=[f'EEG{i+1}' for i in range(num_electrodes)],
    sfreq=sample_rate,
    ch_types=['eeg'] * num_electrodes,
)

# Create RawArray object
raw = RawArray(data, info)
# Generate filename with timestamp
os.makedirs("recordings", exist_ok=True)
filename = os.path.join("recordings", f'{datetime.now().strftime("%Y%m%d_%H%M%S")}.edf')
# Save to BDF file
mne.export.export_raw(filename, raw)
print(f"Saved recording to {filename}")
