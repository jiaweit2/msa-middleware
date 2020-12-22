docker run -i --rm --name node_"$1" \
    -v ${PWD}/node/:/usr/src/app/ \
    --network host \
    aurora-net python -u node.py --id "$1"
