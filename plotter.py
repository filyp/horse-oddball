# pin is 123
from collections import deque

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from scipy import signal

fft_max = 0.0002


class RealtimePlotter:
    def __init__(self, buffer_size=1000, num_electrodes=3, sample_rate=200):
        self.num_electrodes = num_electrodes
        self.sample_rate = sample_rate

        # Create the application and window
        self.app = pg.mkQApp()
        self.win = pg.GraphicsLayoutWidget()
        self.win.setWindowTitle("Real-time Plot")
        self.win.resize(1500, 750)  # Increased width to accommodate 3 columns

        # Create lists to store plots and curves for each electrode
        self.plots = []
        self.fft_plots = []
        self.curves = []
        self.fft_curves = []
        self.data_buffers = []

        # Design the low-pass filter
        nyquist = sample_rate / 2
        cutoff = 45  # Hz
        order = 4
        self.b, self.a = signal.butter(order, cutoff / nyquist, btype="low")

        # Add filter states (one per electrode)
        self.filter_states = [
            signal.lfilter_zi(self.b, self.a) for _ in range(num_electrodes)
        ]

        # Add filtered data buffers
        self.filtered_buffers = []
        for _ in range(num_electrodes):
            filtered_buffer = deque(maxlen=buffer_size)
            for _ in range(buffer_size):
                filtered_buffer.append(0)
            self.filtered_buffers.append(filtered_buffer)

        # Create time array for x-axis
        self.time_array = np.linspace(-buffer_size/sample_rate, 0, buffer_size)

        # Create 3 columns of plots (one for each electrode)
        for i in range(num_electrodes):
            # Time series plot (row 0, column i)
            plot = self.win.addPlot(
                row=0, col=i, title=f"Time Series Data - Electrode {i+1}"
            )
            plot.setLabel("left", "Amplitude")
            plot.setLabel("bottom", "Time (s)")
            plot.showGrid(x=True, y=True)
            plot.setYRange(-40e-6, 40e-6)
            self.plots.append(plot)

            # FFT plot (row 1, column i)
            fft_plot = self.win.addPlot(
                row=1, col=i, title=f"Frequency Spectrum - Electrode {i+1}"
            )
            fft_plot.setLabel("left", "Magnitude")
            fft_plot.setLabel("bottom", "Frequency (Hz)")
            fft_plot.showGrid(x=False, y=False)
            fft_plot.setYRange(0, fft_max)
            self.fft_plots.append(fft_plot)

            # Initialize data buffer and curves for this electrode
            data_buffer = deque(maxlen=buffer_size)
            for _ in range(buffer_size):
                data_buffer.append(0)
            self.data_buffers.append(data_buffer)

            # Create curves
            self.curves.append(plot.plot(pen="y"))
            self.fft_curves.append(
                fft_plot.plot(
                    stepMode=True,
                    fillLevel=0,
                    brush=(0,255,255,150),
                    pen=None  # Remove the contour
                )
            )

            # Set Y range to start from 0
            fft_plot.setLimits(yMin=0)   # Ensure 0 stays at bottom

        # Setup timer for updates
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(80)

        self.win.show()

    def update_data(self, new_data):
        """Add new data points to the plots"""
        for i, value in enumerate(new_data):
            self.data_buffers[i].append(value)

            # Real-time filtering of single sample
            filtered_value, self.filter_states[i] = signal.lfilter(
                self.b, self.a, [value], zi=self.filter_states[i]
            )
            self.filtered_buffers[i].append(filtered_value[0])

    def update_plot(self):
        """Update both the time series plots and FFT plots for all electrodes"""
        for i in range(self.num_electrodes):
            # Update time series plot with filtered data
            filtered_list = list(self.filtered_buffers[i])
            self.curves[i].setData(self.time_array, filtered_list)

            # Update FFT plot
            data_list = list(self.data_buffers[i])
            n_samples = 200
            recent_data = data_list[-n_samples:]
            if len(recent_data) == n_samples:
                window = np.hanning(n_samples)
                windowed_data = recent_data * window

                fft_data = np.fft.rfft(windowed_data)
                fft_freq = np.fft.rfftfreq(n_samples, d=1/self.sample_rate)
                
                freq_mask = fft_freq <= 60
                fft_freq = fft_freq[freq_mask]
                fft_magnitude = np.abs(fft_data)[freq_mask]

                # Calculate edges for the bars
                freq_step = fft_freq[1] - fft_freq[0]
                bar_edges = np.append(fft_freq - freq_step/2, fft_freq[-1] + freq_step/2)  # Add one more edge

                self.fft_curves[i].setData(
                    x=bar_edges,
                    y=fft_magnitude,
                )

    def close(self):
        # Move cleanup to the main Qt thread using signals/slots
        QtCore.QMetaObject.invokeMethod(self.timer, "stop", QtCore.Qt.QueuedConnection)
        QtCore.QMetaObject.invokeMethod(self.win, "close", QtCore.Qt.QueuedConnection)
        QtCore.QMetaObject.invokeMethod(self.app, "quit", QtCore.Qt.QueuedConnection)
