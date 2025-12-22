docker compose down

docker compose up -d

# command to run by forking a new process
command_to_fork(){
    docker exec exabgp_1 bash -c "exabgp exabgp/conf.ini"
}

command_to_fork &

# let the parent process sleep so that exabgp can send the route
sleep 20

docker exec -it frr_2 vtysh -c "clear ip bgp * soft"

docker exec -it frr_3 vtysh -c "clear ip bgp * soft"

sleep 5

# get the output
docker exec -it frr_2 vtysh -c "show ip bgp 100.0.0.0/8" > router2_RIB.txt
docker exec -it frr_3 vtysh -c "show ip bgp 100.0.0.0/8" > router3_RIB.txt

# stop the containers and shut down the network
docker compose down

# stop all child processes before exiting
pkill -P $$