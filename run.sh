#!/usr/bin/env bash
cd `dirname $0`

if [ -f .installed ]
  then
    source viam-env/bin/activate
  else
    apt-get install python3-pip
    python3 -m pip install --user virtualenv --break-system-packages
    python3 -m venv viam-env
    source viam-env/bin/activate
    pip3 install --upgrade -r requirements.txt
    if [ $? -eq 0 ]
      then
        touch .installed
    fi
fi

# Be sure to use `exec` so that termination signals reach the python process,
# or handle forwarding termination signals manually
exec python3 -m main $@
