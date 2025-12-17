sudo docker compose down

sudo docker compose up -d

# let the routes be installed
sleep 10

# get the output
sudo docker exec -it frr_2 vtysh -c "show ip bgp 100.10.1.0/24" > router2_RIB.txt
sudo docker exec -it frr_3 vtysh -c "show ip bgp 100.10.1.0/24" > router3_RIB.txt

# stop the containers and shut down the network
sudo docker compose down

# stop all child processes before exiting
pkill -P $$