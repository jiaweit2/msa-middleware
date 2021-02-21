docker run -i --rm --name node_"$1" \
    -v ${PWD}/../:/usr/src/app/ \
    -v "$3":/usr/src/app/darknet/ \
    --network host \
    -e PYTHONPATH="/usr/src/app/:$PYTHONPATH" \
    aurora-net python -u middleware/node/node.py --id "$1" --annotators "$2"
