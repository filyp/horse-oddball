# Installation

Get the right plux library version from [PLUX-API-Python3](https://github.com/pluxbiosignals/python-samples/tree/master/PLUX-API-Python3). Create a virtual environment and install the requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate  # or .venv/Scripts/activate on Windows
pip install -r requirements.txt
```

# Running

To run the UI and record the signal:
```bash
.venv/bin/python3 plux.py
```

To play the sounds and send triggers:
```bash
.venv/bin/python3 play_sounds.py
```

To close, just close the UI window. Also when the sounds end, the UI will close by itself.
EDF recordings will be saved to the `recordings` folder.

# Tip
For a handy windows shortcut:
1. Right-click on your desktop
2. Select New > Shortcut
3. In the location field, enter (replacing ... with your path):
```
%ComSpec% /k "cd C:\Users\...\horse-oddball && .venv\Scripts\python.exe plux.py"
```
4. Click Next, give the shortcut a name, and click Finish.