
############  Required  ############

if [ ! -d "venv" ]
then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Install required dependency
if [ ! -d "dependency" ]
then
    mkdir dependency
fi
if [ ! -d "dependency/mininet" ]
then
    cd dependency
    git clone git://github.com/mininet/mininet
    sudo ./mininet/util/install.sh -a
    path=$(pwd)/mininet
    cd ..
    echo "export PYTHONPATH=\$PYTHONPATH:${path}" >> venv/bin/activate
fi


############  Optional  ############

# Install YOLO key files
if [ ! -d "dependency/yolo" ]
then
    mkdir dependency/yolo
    cd dependency/yolo
    wget https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3-tiny.cfg
    wget https://pjreddie.com/media/files/yolov3-tiny.weights
    wget https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names
    path_yolo=$(pwd)
    cd ../..
    echo "export CFG_URL=\"${path_yolo}/yolov3-tiny.cfg\"" >> venv/bin/activate
    echo "export WEIGHT_URL=\"${path_yolo}/yolov3-tiny.weights\"" >> venv/bin/activate
    echo "export CLASS_URL=\"${path_yolo}/coco.names\"" >> venv/bin/activate
fi

