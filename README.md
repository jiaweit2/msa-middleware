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
pip install -e
``` 

### Environment Variables
Add some paths in `venv/bin/activate`:
```
export PYTHONPATH=$PYTHONPATH:/path/to/mininet
```
Also, config the middleware variables in `msa-middleware/application/config.py` before running.

## Run
Start Virtualenv
```
source venv/bin/activate
```
Start the middleware in `msa-middleware/application/`
```
sudo python launch_mininet.py
```

## Example Application
Run `commander.py` on any host in mininet:
```
h1 python -u application/commander.py
```