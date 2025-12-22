
import yaml
import json
from argparse import ArgumentParser
import yaml
import os

def print_colored(text, color):
    colors = {
        "black": "\033[30m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }

    color_code = colors.get(color.lower(), colors["reset"])
    print(f"{color_code}{text}{colors['reset']}")

    
def write_config(router1, router2, router3):
    router1_config = dict()
    router2_config = dict()
    router3_config = dict()
    
    ############################### ROUTER 1 CONFIGURATION ####################
    router1_config['global'] = {
        'config': {
            'router-id': '3.0.0.3',
            'as': router1['asNumber']
        }
    }
    
    router1_config['neighbors'] = []
    router1_config['neighbors'].append({
        'config': {
            'neighbor-address': '3.0.0.2',
            'peer-as': router2['asNumber']
        },        
        'transport': {
            'config': {
                'local-address': '3.0.0.3'
            }
        },
        'afi-safis':[
            {
                'config': {
                    'afi-safi-name': 'ipv4-unicast'
                }
            }
        ]
    })
    
    if router1['isRR']:
        router1_config['neighbors'][0]['route-reflector'] = {
            'config':{
                    'route-reflector-client': True,
                    'route-reflector-cluster-id': '3.0.0.3'
                }
            }
        
    router1_config['neighbors'].append({
        'config': {
            'neighbor-address': '2.0.0.2',
            'peer-as': 65000
        },
        'transport': {
            'config': {
                'local-address': '2.0.0.3'
            }
        },
        'afi-safis':[
            {
                'config': {
                    'afi-safi-name': 'ipv4-unicast'
                }
            }
        ] 
    })
        
    ############################### ROUTER 2 CONFIGURATION ####################
    router2_config['global'] = {
        'config': {
            'router-id': '3.0.0.2',
            'as': router2['asNumber']
        }
    }
    
    router2_config['neighbors'] = []
    router2_config['neighbors'].append({
        'config': {
            'neighbor-address': '3.0.0.3',
            'peer-as': router1['asNumber']
        },
        'transport': {
            'config': {
                'local-address': '3.0.0.2'
            }
        },
        'afi-safis':[
            {
                'config': {
                    'afi-safi-name': 'ipv4-unicast'
                }
            }
        ]        
    })
    
    if router2['isRR1']:
        router2_config['neighbors'][0]['route-reflector'] ={
                'config':{
                    'route-reflector-client': True,
                    'route-reflector-cluster-id': '3.0.0.2'
                }
            }
        
    router2_config['neighbors'].append({
        'config': {
            'neighbor-address': '4.0.0.3',
            'peer-as': router3['asNumber']
        },
        'transport': {
            'config': {
                'local-address': '4.0.0.2'
            }
        },
        'afi-safis':[
            {
                'config': {
                    'afi-safi-name': 'ipv4-unicast'
                }
            }
        ]        
    })
    
    if router2['isRR3']:
        router2_config['neighbors'][1]['route-reflector'] = {
            'config':{
                'route-reflector-client': True,
                'route-reflector-cluster-id': '4.0.0.2'
            }
        }
        
    ############################### ROUTER 3 CONFIGURATION ####################
    router3_config['global'] = {
        'config': {
            'router-id': '4.0.0.3',
            'as': router3['asNumber']
        }
    }
    
    router3_config['neighbors'] = []
    router3_config['neighbors'].append({
        'config': {
            'neighbor-address': '4.0.0.2',
            'peer-as': router2['asNumber']
        },
        'transport': {
            'config': {
                'local-address': '4.0.0.3'
            }
        },
        'afi-safis':[
            {
                'config': {
                    'afi-safi-name': 'ipv4-unicast'
                }
            }
        ]
    })
    
    if router3['isRR']:
        router3_config['neighbors'][0]['route-reflector'] = {
                'config':{
                    'route-reflector-client': True,
                    'route-reflector-cluster-id': '4.0.0.3'
                }
        }

    ############################ ExaBGP Configuration #########################

    exabgp_config_lines = [
        'process announce-routes {',
        '   run python exabgp/example.py;',
        '   encoder json;',
        '}',
        '',
        'neighbor 2.0.0.3 {',
        '   router-id 2.0.0.2;',
        '   local-address 2.0.0.2;',
        f'   local-as 65000;',
        f'   peer-as {router2["asNumber"]};',
        '',
        '   api {',
        '       processes [announce-routes];',
        '   }',
        '}'
    ]

    with open('exabgp1/conf.ini', 'w') as f:
        f.write('\n'.join(exabgp_config_lines))
        
    with open('gobgp1/gobgp.yml', 'w') as f:
        yaml.dump(router1_config, f)
        
    with open('gobgp2/gobgp.yml', 'w') as f:
        yaml.dump(router2_config, f)
    
    with open('gobgp3/gobgp.yml', 'w') as f:
        yaml.dump(router3_config, f)
