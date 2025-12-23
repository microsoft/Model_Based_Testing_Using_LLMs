PREFIX="$1"

sudo docker compose down

sudo docker compose up -d

# let the routes be installed
sleep 20

sudo docker exec -it frr_2 vtysh -c "clear ip bgp * soft"
sudo docker exec -it frr_3 vtysh -c "clear ip bgp * soft"

sleep 10

# get the output
sudo docker exec -it frr_2 vtysh -c "show ip bgp ${PREFIX}" > router2_RIB.txt
sudo docker exec -it frr_3 vtysh -c "show ip bgp ${PREFIX}" > router3_RIB.txt

# stop the containers and shut down the network
sudo docker compose down

# stop all child processes before exiting
pkill -P $$