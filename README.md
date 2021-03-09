# MSA-Middleware

## Install
Clone <a href="https://github.com/jiaweit2/aurora-net-iobt-cra-site-server.git">AURORA-NET</a>, follow its instructions to install AURORA-NET.

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
pip install -r requirements.txt 
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
