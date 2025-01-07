#!/usr/bin/env python3
# %% settings
num_beeps = 10
odd_probability = 0.2

beep_duration = 0.5
inter_beep_duration = 1

normal_freq = 1000
odd_freq = 1400

NORMAL_TRIG = 100
ODD_TRIG = 101
NORMAL_TRIG_END = 200
ODD_TRIG_END = 201

# %%
import random
import socket
import time

import numpy as np
import sounddevice as sd

TCP_IP = "127.0.0.1"
TCP_PORT = 5005


def play_beep(freq=400, duration=0.5, volume=1):
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = volume * np.sin(2 * np.pi * freq * t)  # 400 Hz

    # Apply fade in/out to prevent pops
    fade_duration = 0.05
    fade_length = int(fade_duration * sample_rate)
    fade_out = np.linspace(0, 1, fade_length)
    fade_out = np.exp(-fade_out * 10)
    tone[-fade_length:] *= fade_out

    sd.play(tone, sample_rate)
    sd.wait()  # Wait until sound has finished playing


# %%

# Create server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Allow reuse of address
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((TCP_IP, TCP_PORT))
server_socket.listen(1)  # Listen for 1 connection

print(f"Listening on {TCP_IP}:{TCP_PORT}")
client_socket, addr = server_socket.accept()  # Wait for connection
print(f"Connected to {addr}")

# %%
# define beeps
num_odd = int(num_beeps * odd_probability)
num_normal = num_beeps - num_odd
beep_types = [False] * num_normal + [True] * num_odd
random.shuffle(beep_types)
print(beep_types)

# play beeps
for beep_type in beep_types:
    if beep_type:
        client_socket.send(bytes([ODD_TRIG]))
        play_beep(odd_freq, beep_duration)
        client_socket.send(bytes([ODD_TRIG_END]))
    else:
        client_socket.send(bytes([NORMAL_TRIG]))
        play_beep(normal_freq, beep_duration)
        client_socket.send(bytes([NORMAL_TRIG_END]))
    time.sleep(inter_beep_duration)


# %%
client_socket.close()
server_socket.close()