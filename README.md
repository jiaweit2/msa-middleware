# MSA-Middleware

## Install
Clone the middleware, go to the directory:
```
./install.sh
```
This will install everything. You may edit `install.sh` to only install some components.

## Config
Edit `middleware/custom/global-conf.json` to config the nodes information in the correct format. An example is given in that file.

## Run a Simulated Network
Start the simulation in `mininet`:
```
source venv/bin/activate
sudo python application/launch_mininet.py
```

## Run a Node
```
./start.sh [-s | -n | -sn] [Node ID]
```

## Query Example
Run `commander-camera.py` on any node:
```
# if in mininet
xterm h1

# run the commander to start the query in application/data/query
source venv/bin/activate
python -u application/commander.py
```
