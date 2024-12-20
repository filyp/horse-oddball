# pin is 123
from collections import deque

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore


class RealtimePlotter:
    def __init__(self, buffer_size=5000, num_electrodes=3, sample_rate=1000):
        self.num_electrodes = num_electrodes
        self.sample_rate = sample_rate

        # Create the application and window
        self.app = pg.mkQApp()
        self.win = pg.GraphicsLayoutWidget()
        self.win.setWindowTitle("Real-time Plot")
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
            plot = self.win.addPlot(
                row=0, col=i, title=f"Time Series Data - Electrode {i+1}"
            )
            plot.setLabel("left", "Amplitude")
            plot.setLabel("bottom", "Samples")
            plot.showGrid(x=True, y=True)
            plot.setYRange(-40e-6, 40e-6)
            self.plots.append(plot)

            # FFT plot (row 1, column i)
            fft_plot = self.win.addPlot(
                row=1, col=i, title=f"Frequency Spectrum - Electrode {i+1}"
            )
            fft_plot.setLabel("left", "Magnitude")
            fft_plot.setLabel("bottom", "Frequency (Hz)")
            fft_plot.showGrid(x=True, y=True)
            fft_plot.setYRange(0, 0.01)
            self.fft_plots.append(fft_plot)

            # Initialize data buffer and curves for this electrode
            data_buffer = deque(maxlen=buffer_size)
            for _ in range(buffer_size):
                data_buffer.append(0)
            self.data_buffers.append(data_buffer)

            # Create curves
            self.curves.append(plot.plot(pen="y"))
            self.fft_curves.append(fft_plot.plot(pen="c"))

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
        for i in range(self.num_electrodes):
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
                fft_freq = np.fft.rfftfreq(n_samples, d=1 / self.sample_rate)

                # Only plot frequencies up to 60Hz
                freq_mask = fft_freq <= 60
                fft_freq = fft_freq[freq_mask]
                fft_magnitude = np.abs(fft_data)[freq_mask]

                # Update FFT plot
                self.fft_curves[i].setData(fft_freq, fft_magnitude)

