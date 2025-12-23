docker compose down

docker compose up -d

# let the routes be installed
sleep 20

docker exec -it frr_2 vtysh -c "clear ip bgp * soft"
docker exec -it frr_3 vtysh -c "clear ip bgp * soft"

sleep 10

# get the output
docker exec -it frr_2 vtysh -c "show ip bgp 100.0.0.0/8" > router2_RIB.txt
docker exec -it frr_3 vtysh -c "show ip bgp 100.0.0.0/8" > router3_RIB.txt

# stop the containers and shut down the network
docker compose down

# stop all child processes before exiting
pkill -P $$