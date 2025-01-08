#!/usr/bin/env python3
# pin is 123
# %%
import inspect
import select
import socket
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

import mne
import numpy as np
from mne.io import RawArray

import plux
from plotter import RealtimePlotter

num_electrodes = 3
sample_rate = 1000
mac_address = "00:07:80:58:9B:B4"
# the other one: "00:07:80:0F:2F:EF"

# Add with other global variables
TCP_IP = "127.0.0.1"
TCP_PORT = 5005


def signal_int_to_volts(signal_int):
    vcc = 3
    Geeg = 41780  # sensor gain
    return (signal_int / (2**16) - 1 / 2) * vcc / Geeg


def is_socket_connected(sock):
    try:
        sock.send(b"")
        return True
    except socket.error:
        return False


class MyDevice(plux.MemoryDev):
    lastSeq = 0
    sample_counter = 0  # Add counter to track samples

    def onRawFrame(self, nSeq, data):
        global data_buffer, stop, events_buffer

        # Try to connect to trigger source
        if not is_socket_connected(trigger_socket):
            ret_code = trigger_socket.connect_ex((TCP_IP, TCP_PORT))
            if ret_code == 0:
                print("Connected to trigger source")

        # Check if new trigger data is available
        trigger = 0
        if is_socket_connected(trigger_socket):
            trig_exists = select.select([trigger_socket], [], [], 0)[0]
            if trig_exists:
                trigger_bytes = trigger_socket.recv(1)
                if trigger_bytes:  # after disconnect, select still sees but cant read
                    trigger = trigger_bytes[0]
                    print(time.time(), f"Received trigger: {trigger}")
                    # Store event with sample number and trigger value
                    events_buffer.append([len(data_buffer), 0, trigger])
                else:
                    print("Trigger socket disconnected")
                    stop = True
                    plotter.close()

        # Process EEG data as before
        volt_data = [signal_int_to_volts(d) for d in data]
        volt_data = volt_data[:num_electrodes]

        # Store all data at 1000Hz
        data_buffer.append(volt_data + [trigger])

        # Update plotter only every 5th sample (200Hz)
        if self.sample_counter % 5 == 0:
            plotter.update_data(volt_data)
        self.sample_counter += 1

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
data_buffer = []
events_buffer = []  # New buffer for events
trigger_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
plotter = RealtimePlotter(num_electrodes=num_electrodes, sample_rate=sample_rate // 5)

# print("Found devices: ", plux.BaseDev.findDevices())
dev = MyDevice(mac_address)
print("Properties:", dev.getProperties())


def run_plux():
    try:
        dev.start(sample_rate, 15, 16)  # 1000 Hz, ports 1-8, 16 bits
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

# Replace the saving part with:
rec_dir = Path("recordings")
rec_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
base_filename = rec_dir / timestamp

# Create MNE Raw object
info = mne.create_info(
    ch_names=[f"EEG{i+1}" for i in range(num_electrodes)] + ["TRIGGER"],
    sfreq=sample_rate,
    ch_types=["eeg"] * num_electrodes + ["stim"],
)
data = np.array(data_buffer).T  # convert buffer to numpy array (channels x samples)
raw = RawArray(data, info)

# Convert events_buffer to MNE events array format if there are any events
# turns out, it's the annotations which are needed by BrainVisionAnalyzer, not just events
# with annotations, added, the vhdr format wound probably even be unneeded - the .edf wound suffice
# also the TRIGGER channel is probably unnecessary now
# but let's keep them both for redundancy
if events_buffer:
    print("Events found:", events_buffer)
    events = np.array(events_buffer, dtype=int)
    
    # Create an annotations object from the events
    onset = events[:, 0] / sample_rate  # Convert sample numbers to seconds
    duration = np.zeros(len(events))  # Duration of each event (0 for instantaneous)
    description = [f"Stimulus/S{str(val)}" for val in events[:, 2]]  # BrainVision format
    
    # Create and add annotations to the raw object
    annot = mne.Annotations(onset=onset, duration=duration, description=description)
    raw.set_annotations(annot)

# Export to BrainVision format
mne.export.export_raw(base_filename.with_suffix('.vhdr'), raw, fmt='brainvision', overwrite=True)
print(f"Saved recording to {base_filename.with_suffix('.vhdr')}")

# Save EDF as before
edf_filename = base_filename.with_suffix(".edf")
mne.export.export_raw(edf_filename, raw)
print(f"Saved recording to {edf_filename}")

# ! cleanup
dev.stop()
dev.close()
if is_socket_connected(trigger_socket):
    trigger_socket.close()
