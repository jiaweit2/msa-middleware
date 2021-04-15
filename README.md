# MSA-Middleware
This middleware follows the MDO effect loop for query-centric event detection, providing optimizations for resource-constrained networks. It is designed to be easy to use, deploy and customize. In practice, the middleware is expected to be installed on every node to form a network.


## Install
Clone the middleware, go to the directory:
```
./install.sh
```
This will install everything. You may edit `install.sh` to only install some components.


## Config
- Edit `middleware/custom/global-conf.json` to config the nodes information in the correct format. An example is given in that file.
- Write your own query in `application/data/query`.


## Run a Node
```
./start.sh [-s | -n | -sn] [Node ID]
```

## Run a Simulated Network
Start the simulation in `mininet`:
```
source venv/bin/activate
sudo python application/launch_mininet.py
```

## Query Example
Run `commander-camera.py` on any node:
```
# if in mininet
xterm h1

# run the commander to start the query (in application/data/query)
source venv/bin/activate
python -u application/commander-camera.py
```
