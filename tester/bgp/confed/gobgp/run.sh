sudo docker compose down

#python3 gobgp_translator.py

# setup the network and start the docker containers
sudo docker compose up -d

# command to run by forking a new process
command_to_fork(){
    sudo docker exec exabgp_1 bash -c "exabgp exabgp/conf.ini"
}

# forking a new process to run exabgp command
command_to_fork &

# let the parent process sleep so that exabgp can send the route
# and gobgp can update its routing tables
sleep 25

# get the output
sudo docker exec -it gobgp_1 gobgp global rib
sudo docker exec -it gobgp_2 gobgp global rib
sudo docker exec -it gobgp_1 gobgp global rib > router2_RIB.txt
sudo docker exec -it gobgp_2 gobgp global rib > router3_RIB.txt

# stop the containers and shut down the network
sudo docker compose down

# stop all child processes before exiting
pkill -P $$