"""
Script copies the input zone file into an existing or a new Gdnsd container 
and starts the DNS server on container port 53, which is mapped to a host port.
"""

#!/usr/bin/env python3

import pathlib
import subprocess
from subprocess import DEVNULL


def run(zone_file: pathlib.Path, zone_domain: str, cname: str, port: int, restart: bool, tag: str) -> None:
    """
    :param zone_file: Path to the Bind-style zone file
    :param zone_domain: The domain name of the zone
    :param cname: Container name
    :param port: The host port which is mapped to the port 53 of the container
    :param restart: Whether to load the input zone file in a new container
                        or reuse the existing container
    :param tag: The image tag to be used if restarting the container
    """
    if restart:
        subprocess.run(['docker', 'container', 'rm', cname, '-f'],
                       stdout=subprocess.PIPE, check=False)
        subprocess.run(['docker', 'run', '-dp', str(port)+':53/udp', '--name=' +
                        cname, 'gdnsd' + tag], stdout=subprocess.PIPE, check=False)
    else:
        # Stop the running server instance inside the container
        subprocess.run(['docker', 'exec', cname, 'gdnsdctl', 'stop'],
                       stdout=DEVNULL, stderr=DEVNULL, check=False)
    # Copy the new zone file into the container
    subprocess.run(['docker', 'cp', str(zone_file), cname +
                    ':/usr/local/etc/gdnsd/zones/' + zone_domain], stdout=subprocess.PIPE, check=False)

    # Start the server
    subprocess.Popen(['docker', 'exec', cname, 'gdnsd', 'start'], stdout=DEVNULL, stderr=DEVNULL)