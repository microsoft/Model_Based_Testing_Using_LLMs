from Scripts.preprocessor_checks import delete_container
import subprocess
import pathlib
from Implementations.Bind.prepare import run as bind
from Implementations.Knot.prepare import run as knot
from Implementations.Nsd.prepare import run as nsd
from Implementations.Powerdns.prepare import run as powerdns
from Scripts.test_with_valid_zone_files import prepare_containers, querier

#=== Configuration ===#
impl = "powerdns"
cid = 1
tag = ":latest"
zone_path = "./dns_extremal_tests_latest/ZoneFiles/3_1.txt"
query = ("exam!ple.example.com.", "A")
implementations = {"bind": (False, 8000), "nsd": (False, 8100), "knot": (False, 8200), "powerdns": (False, 8300)}

#=== Helper Functions ===#
def get_zone_domain(zone_file: str) -> str:
    domain = ''
    with open(zone_file, 'r') as zone_fp:
        for line in zone_fp:
            if 'SOA' in line:
                domain = line.split('\t')[0]
                if ' ' in domain:
                    domain = line.split()[0]
                break
    return domain


#=== Main ===#

# set the chosen impl to be tested
implementations[impl] = (True, implementations[impl][1])  

# delete previous container if exists
delete_container(f"{cid}_{impl}_server")

# start new container
subprocess.run(['docker', 'run', '-dp', str(implementations[impl][1] * cid) + ':53/udp',
                                '--name=' + str(cid) + '_' + impl + '_server', impl + tag], check=True)
print(f"Started new {impl} container with name {cid}_{impl}_server")

# Prepare the server with the zone file
zone_domain = get_zone_domain(zone_path)
prepare_containers(pathlib.Path(zone_path), zone_domain, cid, False, implementations, tag)
print(f"{impl} Server prepared with zone file {zone_path}")

# === Wait for user before proceeding === #
input("\n✅ Server is ready. You may change the configuration now. Press Enter to continue...\n")
## Example: In a separate terminal:
## docker exec -it 1_powerdns_server bash
## See from dockerfile where pdns.conf is located
## cd /usr/local/etc
## echo "8bit-dns=yes" >> pdns.conf
## cat pdns.conf # to verify

# Query the server
response = querier(query[0], query[1], implementations[impl][1] * cid)
print(f"Querying {impl} server at port {implementations[impl][1] * cid} for {query[0]} {query[1]}")

print(f"Response from {impl} server: {response}")



