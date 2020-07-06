#!/bin/bash
if [ -e tika-server-*.jar ];
then
    echo server file already present
else
    exec wget https://downloads.apache.org/tika/tika-server-1.24.1.jar
fi
