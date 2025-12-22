import json
import yaml
import os
    
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
            'neighbor-address': '2.0.0.3',
            'peer-as': 65000
        },
        'transport': {
            'config': {
                'local-address': '2.0.0.2'
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
        
    with open('gobgp1/gobgp.yml', 'w') as f:
        yaml.dump(router1_config, f)
        
    with open('gobgp2/gobgp.yml', 'w') as f:
        yaml.dump(router2_config, f)
    
    with open('gobgp3/gobgp.yml', 'w') as f:
        yaml.dump(router3_config, f)
        

if not os.path.exists('gobgp1'):
    os.makedirs('gobgp1')

if not os.path.exists('gobgp2'):
    os.makedirs('gobgp2')
    
if not os.path.exists('gobgp3'):
    os.makedirs('gobgp3')
    
    
with open("../../../rr1_all_test_cases.json", "r") as f:
    test_cases = json.load(f)
    
    
f = open("results.txt", "w")
        
for i in range(len(test_cases)):
    t = test_cases[i]
    print("Test case:", (i+1))

    p_inRRflag, p_outRRflag, p_inAS, p_outAS = t[0], t[1], t[2], t[3]

    router1_asnum = 100
    if not p_inAS:
        router2_asnum = 200
    else:
        router2_asnum = 100
        
    if not p_outAS:
        router3_asnum = 300
    else:
        router3_asnum = router2_asnum
        
    # isRR<num> means route reflector to the neighbor
    # isClient<num> means route reflector client to the neighbor

    if p_inRRflag == 0:
        isRR1 = False
        isClient1 = True
        isRR_router1 = True
        isClient_router1 = False
    elif p_inRRflag == 1:
        isRR1 = True
        isClient1 = False
        isRR_router1 = False
        isClient_router1 = True
    else:
        isRR1 = False
        isClient1 = False
        isRR_router1 = False
        isClient_router1 = False
        
    if p_outRRflag == 0:
        isRR3 = False
        isClient3 = True
        isRR_router3 = True
        isClient_router3 = False
    elif p_outRRflag == 1:
        isRR3 = True
        isClient3 = False
        isRR_router3 = False
        isClient_router3 = True
    else:
        isRR3 = False
        isClient3 = False
        isRR_router3 = False
        isClient_router3 = False
        
    router1 = {
        'asNumber': router1_asnum,
        'isRR': isRR_router1,
        'isClient': isClient_router1
    }

    router2 = {
        'asNumber': router2_asnum,
        'isRR1': isRR1,
        'isClient1': isClient1,
        'isRR3': isRR3,
        'isClient3': isClient3
    }

    router3 = {
        'asNumber': router3_asnum,
        'isRR': isRR_router3,
        'isClient': isClient_router3
    }

    write_config(router1, router2, router3)
    os.system('bash start.sh')
    
    isReceivedR2 = False
    isReceivedR3 = False
    
    if os.path.exists('router2_RIB.txt'):
        with open('router2_RIB.txt', 'r') as r2:
            lines = r2.readlines()
            if(len(lines) > 1): isReceivedR2 = True
            os.remove('router2_RIB.txt')
    
    if os.path.exists('router3_RIB.txt'):
        
        with open('router3_RIB.txt', 'r') as r3:
            lines = r3.readlines()
            if(len(lines) > 1): isReceivedR3 = True
            os.remove('router3_RIB.txt')
    

    # if 'r2' in new_df['Node'].tolist(): isReceivedR2 = True
    # if 'r3' in new_df['Node'].tolist(): isReceivedR3 = True

    f.write(str(isReceivedR2) + ' ' + str(isReceivedR3) + '\n')
        

f.close()