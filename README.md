# MSA-Middleware
This middleware follows the MDO effect loop for query-centric event detection, providing optimizations for resource-constrained networks. It is designed to be easy to use, deploy and customize. In practice, the middleware is expected to be installed on every node to form a network. Python3 is required. More details about the motivations, architecture, application examples and evaulations can be found in this [paper](https://drive.google.com/file/d/1wL_WE4y1kJTB6scQzbTcRWNUiQ0OkRGv/view?usp=sharing).


## Install
Clone the middleware, go to the directory:
```
./install.sh
```
This will install everything. You may edit `install.sh` to only install some components.


## Customization
All custom files are expected to be Python files. Details may be found in this [wiki](https://github.com/jiaweit2/msa-middleware/wiki/Customization). You may skip this section if you just want to run the default demo. Users may edit the following files to customize:
- Edit `middleware/custom/confs/global-conf.json` to config the global settings.
- Create or edit `middleware/custom/confs/conf-{Node ID}.json` to config each node respectively.
- Write your own query in `application/data/query`.
- Write your own annotators/sensors under corresponding directories of `middleware/custom/`.
- Write your own commander method in `application/commander-template.py` for running (streaming) query only, static query already implemented. 


## Run a Node
```
./start.sh [-s | -n | -sn] [Node ID]
```
A node ID is required when a node is run. For example, to start a broker/server: `./start.sh -s`; to start a node: `./start.sh -n 0001`.


## Run a Simulated Network
Start the simulation in `mininet`:
```
source venv/bin/activate
sudo python application/launch_mininet.py
```

## Query Example
Run `commander-camera.py` on any node:
```
# if in mininet:
xterm h1

# run the commander to start the query (in application/data/query)
source venv/bin/activate
python -u application/commander-camera.py
```
