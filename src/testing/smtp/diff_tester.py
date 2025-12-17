import json
from tqdm import tqdm

n_impl = 3

all_responses = []
for i in range(1, n_impl + 1):
    print(f"Collecting responses from implementation {i}...")
    with open(f'results{i}.txt', 'r') as f:
        lines = f.readlines()

    responses = []
    for line in lines:
        line = line.strip()
        response = eval(line)[2]
        responses.append(response)
        # print(response)

    all_responses.append(responses)

assert len(all_responses) == n_impl
for i in range(1, n_impl):
    assert len(all_responses[i]) == len(all_responses[i-1])

print("Responses collected successfully!")

with open('tests.json', 'r') as f:
    tests = json.load(f)

n_tests = len(tests)

print("Preparing diff testing results...")

diffs = {}
for i in tqdm(range(n_tests)):
    diff_element = [str(responses[i]) for responses in all_responses]
    test_case = [tests[i][1], tests[i][2]]
    diffs[i] = [test_case, diff_element]

with open('diff_testing_results.json', 'w') as f:
    json.dump(diffs, f, indent=4)

print("Diff testing results saved successfully!")

print("Identifying cases with differences...")
diff_indices = []
for i in diffs:
    diff_element = diffs[i]
    codes = [eval(response)[0] for response in diff_element[1]]
    if len(set(codes)) > 1:
        diff_indices.append(i)

diff_cases = {}
for i in diff_indices:
    diff_cases[i] = diffs[i]

with open('diff_cases.json', 'w') as f:
    json.dump(diff_cases, f, indent=4)




    