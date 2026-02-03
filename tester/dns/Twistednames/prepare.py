"""
Script copies the input zone file into an existing or a new TwistedNames container 
and starts the DNS server on container port 53, which is mapped to a host port.
"""

#!/usr/bin/env python3

import pathlib
import subprocess


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
        subprocess.run(['docker', 'run', '-dp', str(port) + ':53/udp', '--name=' +
                        cname, 'twistednames' + tag], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    else:
        # Stop the running server instance inside the container
        subprocess.run(['docker', 'exec', cname, 'pkill', 'twistd'],
                       stdout=subprocess.PIPE, check=False)
    # Copy the new zone file into the container
    subprocess.run(['docker', 'cp', str(zone_file), cname +
                    ':/' + zone_domain], stdout=subprocess.PIPE, check=False)

    # Start the server
    # twistd --logfile=- -n dns --bindzone test. --verbose
    subprocess.run(['docker', 'exec', cname, 'twistd', 'dns', '--bindzone',
                              zone_domain], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
