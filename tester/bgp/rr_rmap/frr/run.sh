PREFIX="$1"

if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE="docker-compose"
else
    echo "Error: docker compose or docker-compose is required." >&2
    exit 1
fi

$COMPOSE down

$COMPOSE up -d

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
echo -e "\n@@@ FRR Router 2 RIB:"
docker exec -it frr_2 vtysh -c "show ip bgp"
echo -e "\n@@@ FRR Router 3 RIB:"
docker exec -it frr_3 vtysh -c "show ip bgp"

docker exec -it frr_1 vtysh -c "show ip bgp" > router1_full_RIB.txt
docker exec -it frr_2 vtysh -c "show ip bgp" > router2_full_RIB.txt
docker exec -it frr_3 vtysh -c "show ip bgp" > router3_full_RIB.txt
docker exec -it frr_2 vtysh -c "show ip bgp ${PREFIX}" > router2_RIB.txt
docker exec -it frr_3 vtysh -c "show ip bgp ${PREFIX}" > router3_RIB.txt

# stop the containers and shut down the network
$COMPOSE down

# Fix permissions for mounted volumes (Docker may create files as root)
sudo chmod -R a+rw frr1 frr2 frr3 exabgp1 2>/dev/null || true

# stop all child processes before exiting
pkill -P $$