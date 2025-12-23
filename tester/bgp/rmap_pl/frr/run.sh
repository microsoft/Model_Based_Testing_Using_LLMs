PREFIX="$1"

sudo docker compose down

sudo docker compose up -d

# command to run by forking a new process
command_to_fork(){
    sudo docker exec exabgp_1 bash -c "exabgp exabgp/conf.ini"
}

command_to_fork &

# let the parent process sleep so that exabgp can send the route
sleep 20

sudo docker exec -it frr_2 vtysh -c "clear ip bgp * soft"

sleep 5

# get the output
sudo docker exec -it frr_2 vtysh -c "show ip bgp" > full_RIB.txt
sudo docker exec -it frr_2 vtysh -c "show ip bgp ${PREFIX}" > router2_RIB.txt

# stop the containers and shut down the network
sudo docker compose down

# stop all child processes before exiting
pkill -P $$