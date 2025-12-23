 docker compose down

#python3 gobgp_translator.py

# setup the network and start the docker containers
 docker compose up -d

# command to run by forking a new process
command_to_fork(){
     docker exec exabgp_1 bash -c "exabgp exabgp/conf.ini"
}

# forking a new process to run exabgp command
command_to_fork &

# let the parent process sleep so that exabgp can send the route
# and gobgp can update its routing tables
sleep 20

# get the output
 docker exec -it gobgp_1 gobgp global rib > router1_RIB.txt
 docker exec -it gobgp_2 gobgp global rib > router2_RIB.txt
 docker exec -it gobgp_3 gobgp global rib > router3_RIB.txt

# stop the containers and shut down the network
 docker compose down

# stop all child processes before exiting
pkill -P $$