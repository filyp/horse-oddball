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
.venv/bin/python3 record_and_visualize.py
```

To play the sounds and send triggers:
```bash
.venv/bin/python3 play_sounds.py
```

To close, just close the UI window. Also when the sounds end, the UI will close by itself.
EDF recordings will be saved to the `recordings` folder.

# Tip
For a handy shortcut:

## Windows
1. Right-click on your desktop
2. Select New > Shortcut
3. In the location field, enter (replacing ... with your path):
```
%ComSpec% /k "cd C:\Users\...\horse-oddball && .venv\Scripts\python.exe record_and_visualize.py"
```
4. Click Next, give the shortcut a name, and click Finish.

## Linux
The repository includes desktop shortcut files.

Create symbolic links to them:
```bash
ln -s "$(pwd)/record_and_visualize.desktop" ~/Desktop/
ln -s "$(pwd)/play_sounds.desktop" ~/Desktop/
```

After creating the shortcuts, make them executable:
```bash
chmod +x ~/Desktop/*.desktop
```
