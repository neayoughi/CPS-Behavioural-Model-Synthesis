#!/bin/bash

current_datetime=$(date '+%Y-%m-%d %H:%M:%S')

# Ports array
ports=(80 22)

protocols=("TCP" "UDP")

# Generate random packet size function
generate_random_packet_size() {
     echo $(shuf -i 50-500 -n 5)
     #echo $((RANDOM % (500 - 50 + 1) + 50))
}

# Interval between attacks
attack_interval=300

timeout_duration=180

loop_counter=1

# Type of attack
attack_type="DOS"

# Function to send normal traffic
send_normal_traffic() {
	sizes=($(generate_random_packet_size))
    for port in "${ports[@]}"; do
        for protocol in "${protocols[@]}"; do
            for size in "${sizes[@]}"; do
                #size=$(generate_random_packet_size)
                echo "Sending Normal traffic to port $port with $protocol protocol and $size size packets"
                echo "Time: $(date '+%Y-%m-%d %H:%M:%S'), Port: $port, Protocol: $protocol, Packet Size: $size, Attack Type: Normal" >>parameter_changes.txt
                bash hping_traffic.sh $port $protocol $size "Normal"
                sleep 10
            done
        done
    done
}

# Send initial normal traffic
send_normal_traffic

for _ in {1..2}; do
	sizes=($(generate_random_packet_size))

	for port in "${ports[@]}"; do
		for protocol in "${protocols[@]}"; do
			for size in "${sizes[@]}"; do
				echo "Attacking vulnerable machine on port $port with $protocol protocol and $size size packets"
			       	timeout ${timeout_duration}s bash hping.sh $port $protocol $size $attack_type
			done
			#send_normal_traffic
		done
	done
	send_normal_traffic
done

echo "Attacks have finished"

