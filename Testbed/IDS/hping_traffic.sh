#!/bin/bash

# Check if four arguments are provided
if [ $# -ne 4 ]; then
    echo "Usage: $0 <port> <protocol> <packet_size> <attack_type>"
    exit 1
fi

port=$1
protocol=$2
packet_size=$3
attack_type=$4
target_ip="10.0.192.8"

# Send a packet with the specified size
echo "Sending $attack_type traffic to $target_ip:$port with $protocol protocol and $packet_size size packets"
if [ "$protocol" == "UDP" ]; then
    sudo hping3 -c 1 --udp -p $port -d $packet_size $target_ip
else
    sudo hping3 -c 1 -S -p $port -d $packet_size $target_ip
fi



