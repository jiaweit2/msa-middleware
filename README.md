# MSA-Middleware

## Install
Clone the middleware, go to the directory:
```
cd path/to/msa-middleware
```

### Create Virtualenv
```
python3 -m venv venv
```
Then install the packages:
```
# Start Virtualenv
source venv/bin/activate
pip install -r requirements.txt 
``` 

### Environment Variables
#### Add some variables in `venv/bin/activate` as follows
Add mininet path to PYTHONPATH:
```
export PYTHONPATH=$PYTHONPATH:/path/to/mininet
```
Add dependent paths for YOLO(annotator):
```
export CFG_URL="path/to/darknet/cfg/yolov3-tiny.cfg"
export WEIGHT_URL="path/to/darknet/yolov3-tiny.weights"
export CLASS_URL="path/to/darknet/data/coco.names"
```

## Run
Start the middleware in `msa-middleware/application/`
```
sudo python launch_mininet.py
```

## Example Application
Run `commander.py` on any host in mininet:
```
h1 python -u application/commander.py
```
