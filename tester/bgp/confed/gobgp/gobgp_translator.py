import json
import yaml
import os

with open("../../../all_test_cases.json", "r") as f:
    test_cases = json.load(f)
    
def get_as_path(file):
    if not os.path.exists(file):
        return "Error: output file not generated"
    
    with open(file, 'r') as f:
        rib_lines = f.read().split('\n')
        
    if len(rib_lines) == 0:
        return "Error: No output generated"
    
    elif len(rib_lines) == 1:
        if rib_lines[0].startswith("Network not in table") or rib_lines[0]=='':
            return "No route received"
    
    as_path_index = rib_lines[0].find('AS_PATH')
    age_index = rib_lines[0].find('Age')
    
    attrs_index = rib_lines[0].find('Attrs')
    
    as_path = rib_lines[1][as_path_index:age_index].strip()
    attrs = rib_lines[1][attrs_index:].strip()
    
    print(as_path, attrs)
    return as_path, attrs

    
def write_config(originAS, router2, router3, remove_private_as_flag, replace_as_flag, local_preference):
    router2_config = dict()
    router3_config = dict()
    
    ############################### ROUTER 2 CONFIGURATION ####################
    router2_config['global'] = {
        'config': {
            'router-id': '192.168.255.1'
        },
        'apply-policy': {
            'config': {
                'export-policy-list': ['RM1'],
                'default-export-policy': 'reject-route'
            }
        }
    }
    
    if router2['subAS'] != 0:
        router2_config['global']['config']['as'] = router2['subAS']
        router2_config['global']['confederation'] = {
            'config': {
                'enabled': True,
                'identifier': router2['asNumber'],
                'member-as-list': [] # will be filled in later
            }
        }
    else:
        router2_config['global']['config']['as'] = router2['asNumber']
        
    router2_config['neighbors'] = []
    router2_config['neighbors'].append({
        'config': {
            'neighbor-address': '3.0.0.3',
            'peer-as': originAS
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
    router2_config['neighbors'].append({
        'config':{
            'neighbor-address': '4.0.0.3',
            'peer-as': 0 # will be filled in later
        },
        'transport':{
            'config':{
                'local-address': '4.0.0.2'
            }
        },
        'afi-safis':[
            {
                'config':{
                    'afi-safi-name': 'ipv4-unicast'
                }
            }
        ]
    })
    if remove_private_as_flag:
        router2_config['neighbors'][1]['config']['remove-private-as'] = "all"
    # if replace_as_flag:
    #     router2_config['neighbors'][1]['as-path-options'] = {
    #         'config': {
    #             'replace-peer-as': True
    #         }
    #     }
    router2_config['policy-definitions'] = []
    router2_config['policy-definitions'].append({
        'name': 'RM1',
        'statements': [
            {
                'name': 'RM1',
                'actions': {
                    'route-disposition': 'accept-route',
                    'bgp-actions': {
                        'set-local-pref': local_preference
                    }
                }
            }
        ]
    })
    
    #################### ROUTER 3 CONFiGURATION ####################
    router3_config['global'] = {
        'config': {
            'router-id': '192.168.255.2'
        } 
    }
    
    if router3['subAS'] != 0:
        router3_config['global']['config']['as'] = router3['subAS']
        router3_config['global']['confederation'] = {
            'config': {
                'enabled': True,
                'identifier': router3['asNumber'],
                'member-as-list': [] # will be filled in later
            }
        }
    else:
        router3_config['global']['config']['as'] = router3['asNumber']
        
    router3_config['neighbors'] = []
    router3_config['neighbors'].append({
        'config':{
            'neighbor-address': '4.0.0.2',
            'peer-as': 0 # will be filled in later
        },
        'transport':{
            'config':{
                'local-address': '4.0.0.3'
            }
        },
        'afi-safis':[
            {
                'config':{
                    'afi-safi-name': 'ipv4-unicast'
                }
            }
        ]
    })
    
    if router2['asNumber'] != router3['asNumber']:
        router2_config['neighbors'][1]['config']['peer-as'] = router3['asNumber']
        router3_config['neighbors'][0]['config']['peer-as'] = router2['asNumber']
    else:
        if router2['subAS'] != 0:
            if router2['subAS'] != router3['subAS']:
                router2_config['global']['confederation']['config']['member-as-list'].append(router3['subAS'])
                router3_config['global']['confederation']['config']['member-as-list'].append(router2['subAS'])
            
            router2_config['neighbors'][1]['config']['peer-as'] = router3['subAS']
            router3_config['neighbors'][0]['config']['peer-as'] = router2['subAS']
            
    exabgp_config_lines = [
        'process announce-routes {',
        '   run python exabgp/example.py;',
        '   encoder json;',
        '}',
        '',
        'neighbor 3.0.0.2 {',
        '   router-id 3.0.0.3;',
        '   local-address 3.0.0.3;',
        f'   local-as {originAS};',
        f'   peer-as {router2["asNumber"]};',
        '',
        '   api {',
        '       processes [announce-routes];',
        '   }',
        '}'
    ]
            
    with open('gobgp1/gobgp.yml', 'w') as f:
        yaml.dump(router2_config, f, default_flow_style=False, sort_keys=False)
        
    with open('gobgp2/gobgp.yml', 'w') as f:
        yaml.dump(router3_config, f, default_flow_style=False, sort_keys=False)

    with open('exabgp1/conf.ini', 'w') as f:
        f.write('\n'.join(exabgp_config_lines))
        
    with open('exabgp1/example.py', 'r') as f:
        example_lines = f.read().split('\n')
        example_lines[8] = '   \'announce route 100.0.0.0/8 next-hop self' + '\','
        
    with open('exabgp1/example.py', 'w') as f:
        f.write('\n'.join(example_lines))    


# router2 = {
#     'asNumber': 768,
#     'subAS': 0
# }
# router3 = {
#     'asNumber': 512,
#     'subAS': 0
# }
# write_config(64512, 50, router2, router3, True, True)


if not os.path.exists('results'):
    os.mkdir('results')
    
for i in range(549, len(test_cases)):
    t = test_cases[i]
    print("Test case:", (i+1))
    write_config(t[0], t[1], t[2], t[3], t[4], t[5])
    os.system('bash start.sh')
    as_path1, attrs1 = get_as_path("router2_RIB.txt")
    as_path2, attrs2 = get_as_path("router3_RIB.txt")
    
    with open('results/' + str(i) + '.txt', 'w') as f:
        f.write("AS path for router 2: " + as_path1 + '\n')
        f.write("Attrs for router 2: " + attrs1 + '\n')
        f.write("AS path for router 3: " + as_path2 + '\n')
        f.write("Attrs for router 3: " + attrs2 + '\n')
               
    if os.path.exists('router2_RIB.txt'):
        os.remove('router2_RIB.txt')
        
    if os.path.exists('router3_RIB.txt'):
        os.remove('router3_RIB.txt')