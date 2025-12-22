PREFIX="$1"

docker compose down

docker compose up -d

# command to run by forking a new process
command_to_fork(){
    docker exec exabgp_1 bash -c "exabgp exabgp/conf.ini"
}

command_to_fork &

# let the routes be installed
sleep 20

docker exec -it frr_1 vtysh -c "clear ip bgp * soft"
docker exec -it frr_2 vtysh -c "clear ip bgp * soft"
docker exec -it frr_3 vtysh -c "clear ip bgp * soft"

sleep 10

# get the output
docker exec -it frr_1 vtysh -c "show ip bgp" > router1_full_RIB.txt
docker exec -it frr_2 vtysh -c "show ip bgp" > router2_full_RIB.txt
docker exec -it frr_3 vtysh -c "show ip bgp" > router3_full_RIB.txt
docker exec -it frr_2 vtysh -c "show ip bgp ${PREFIX}" > router2_RIB.txt
docker exec -it frr_3 vtysh -c "show ip bgp ${PREFIX}" > router3_RIB.txt

# stop the containers and shut down the network
docker compose down

# stop all child processes before exiting
pkill -P $$