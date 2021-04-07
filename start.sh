#!/bin/bash


function usage {
    echo "usage: ./start.sh [-s | -n | -sn] [Node ID]"
    echo "  -s          Run the Broker"
    echo "  -n          Run the node"
    echo "  Node ID     Assign a node ID"
    exit 1
}

if [ "$1" != "-s" ] && [ "$1" != "-n" ] && [ "$1" != "-sn" ]; then
    usage
fi

if ([ "$1" == "-n" ] || [ "$1" == "-sn" ]) && [ -z $2 ]; then
    usage
fi

source venv/bin/activate

if [ "$1" == "-s" ] || [ "$1" == "-sn" ]
then
    cd server
    python -u aurora_local_server_xsub.py &
    sleep 1
    python -u aurora_local_server_xpub.py &
    cd ..
fi

if ([ "$1" == "-n" ] || [ "$1" == "-sn" ]) && [ ! -z $2 ]
then
    python -u middleware/node/node.py --id $2
fi