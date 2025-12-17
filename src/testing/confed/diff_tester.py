import csv
import json
import glob

files = glob.glob('gobgp/results/*.txt')

comparison_file = 'comparison.csv'
comparison_dict = {}

with open('../../all_test_cases.json', mode='r') as f:
    test_cases = json.load(f)

with open('frr/results.txt', 'r') as f:
    frr_test_results = f.read().split('\n')
    
with open(comparison_file, mode='w') as csvfile:
    fieldnames = ['Test Case', 'Batfish R2 AS Path', 'GoBGP R2 AS Path', 'FRR R2 AS Path', 'Batfish R3 AS Path', 'GoBGP R3 AS Path', 'FRR R3 AS Path', 'Batfish LocalPref', 'GoBGP LocalPref', 'FRR LocalPref', 'Match']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    data = []
    for i in range(len(files)):
        with open('batfish/results/test_case' + str(i) + '.txt', 'r') as f:
            batfish_test_result = f.read().split('\n')
            
        with open('gobgp/results/' + str(i) + '.txt', 'r') as f:
            gobgp_result = f.read().split('\n')
        
        batfish_test_result = batfish_test_result[2:]
        gobgp_test_result = [gobgp_result[0], gobgp_result[2]]
        gobgp_local_pref_results = [gobgp_result[1], gobgp_result[3]]
        
        print(batfish_test_result)
        print(gobgp_test_result)
        batfish_as_paths = []
        batfish_local_pref = None
        for line in batfish_test_result:
            tokens = line.split()
            print(tokens)
            as_path = ' '.join(tokens[2:-1])
            localpref = tokens[-1]
            batfish_as_paths.append(as_path)
            if tokens[1] == 'r3':
                batfish_local_pref = localpref
        
        gobgp_as_paths = []
        gobgp_local_pref = None
        for line in gobgp_test_result:
            tokens = line.split(':')
            as_path = tokens[1].strip()
            if as_path != '':
                gobgp_as_paths.append(as_path)
        
        gobgp_local_pref_results[1] = gobgp_local_pref_results[1].replace("Attrs for router 3: ", "").strip()
        if gobgp_local_pref_results[1] != '':
            # print(gobgp_local_pref_results[1])
            sp = gobgp_local_pref_results[1].split("[{")[1].split("}]")[0].split("} {")
            for att in sp:
                if att.startswith("LocalPref"):
                    gobgp_local_pref = int(att[11:].replace(",",""))
                    
        frr_as_paths = []
        tokens = frr_test_results[i].split(',')
        if tokens[2] != '':
            frr_as_paths.append(tokens[2])
        if tokens[3] != '':
            frr_as_paths.append(tokens[3])
            
        frr_local_pref = None
        if tokens[5] != '':
            frr_local_pref = int(tokens[5])
                
        result_row = {
            'Test Case': f"Origin AS: {test_cases[i][0]}\nRouter 2: {test_cases[i][1]}\nRouter 3: {test_cases[i][2]}\nRemove Private AS: {test_cases[i][3]}\nReplace AS: {test_cases[i][4]}\nLocal Pref: {test_cases[i][5]}",
            'Batfish R2 AS Path': batfish_as_paths[0] if len(batfish_as_paths) > 0 else 'None',
            'GoBGP R2 AS Path': gobgp_as_paths[0] if len(gobgp_as_paths) > 0 else 'None',
            'FRR R2 AS Path': frr_test_results[i].split(',')[2] if frr_test_results[i].split(',')[2] != '' else 'None',
            'Batfish R3 AS Path': batfish_as_paths[1] if len(batfish_as_paths) > 1 else 'None',
            'GoBGP R3 AS Path': gobgp_as_paths[1] if len(gobgp_as_paths) > 1 else 'None',
            'FRR R3 AS Path': frr_test_results[i].split(',')[3] if frr_test_results[i].split(',')[3] != '' else 'None',
            'Batfish LocalPref': batfish_local_pref if batfish_local_pref is not None else 'None',
            'GoBGP LocalPref': gobgp_local_pref if gobgp_local_pref is not None else 'None',
            'FRR LocalPref': frr_local_pref if frr_local_pref is not None else 'None'
        }
        
        if batfish_as_paths == gobgp_as_paths and batfish_local_pref == gobgp_local_pref and frr_as_paths == gobgp_as_paths and batfish_as_paths == frr_as_paths and gobgp_local_pref==frr_local_pref and batfish_local_pref==frr_local_pref:
            result_row['Match'] = 'Yes'
        else:
            result_row['Match'] = 'No'
            
        data.append(result_row)
    
    writer.writerows(data)
        
    