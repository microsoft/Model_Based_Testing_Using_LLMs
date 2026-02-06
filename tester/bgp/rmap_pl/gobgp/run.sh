if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE="docker-compose"
else
    echo "Error: docker compose or docker-compose is required." >&2
    exit 1
fi

$COMPOSE down

#python3 gobgp_translator.py

# setup the network and start the docker containers
$COMPOSE up -d

# command to run by forking a new process
command_to_fork(){
    docker exec exabgp_1 bash -c "exabgp exabgp/conf.ini"
}

# forking a new process to run exabgp command
command_to_fork &

# let the parent process sleep so that exabgp can send the route
# and gobgp can update its routing tables
sleep 25

# get the output
echo -e "\n@@@ GoBGP Router 2 RIB:"
docker exec -it gobgp_2 gobgp global rib
docker exec -it gobgp_2 gobgp global rib > router2_RIB.txt

# stop the containers and shut down the network
$COMPOSE down

# Fix permissions for mounted volumes (Docker may create files as root)
sudo chmod -R a+rw gobgp2 exabgp1 2>/dev/null || true

# stop all child processes before exiting
pkill -P $$