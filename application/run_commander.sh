docker run -i --rm --name commander \
    -v ${PWD}/../:/usr/src/app/ \
    --network host \
    -e PYTHONPATH="/usr/src/app/:$PYTHONPATH" \
    aurora-net python -u application/commander.py