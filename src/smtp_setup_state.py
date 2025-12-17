import json
from tqdm import tqdm

def find_all_input_sequences(transition_dict, dest_state):
    from collections import deque

    # Convert the keys from string representation of tuples to actual tuples
    transitions = {
        eval(key): value for key, value in transition_dict.items()
    }

    # Find the initial state
    initial_state = "INITIAL"

    # Queue for BFS: (current_state, input_sequence)
    queue = deque([(initial_state, [])])

    # List to store all possible sequences leading to dest_state
    all_sequences = []

    while queue:
        # print(f"Queue: {queue}")
        current_state, input_sequence = queue.popleft()
        # print(f"Current State: {current_state}, Input Sequence: {input_sequence}")
        # print(f"Destination State: {dest_state}")

        # If we reach the destination state, add the input sequence to results
        if current_state == dest_state:
            # print(f"Reached Destination State: {dest_state}")
            all_sequences.append(input_sequence)
            continue

        # Explore all possible transitions from the current state
        # print("Exploring all possible Transitions from the current state...")
        for (state, input_val), next_state in transitions.items():
            if state == current_state:
                # print(f"Transition: ({state}, {input_val}) --> {next_state}")
                queue.append((next_state, input_sequence + [input_val]))

    return all_sequences

# Load the transition dictionary
with open('smtp_transition_dict.json', 'r') as f:
    transition_dict = json.load(f)


############ Test the function with a destination state ############

# dest_state = "HELO_SENT"
# all_sequences = find_all_input_sequences(transition_dict, dest_state)
# print("All Input Sequences:")
# for seq in all_sequences:
#     print(seq)

##################################

with open("smtp_test_cases.json", "r") as f:
    tests = json.load(f) ## [[state, input, output], [state, input, output], ...]

complete_tests = []
for test in tqdm(tests):
    state, input, output = test[0], test[1], test[2]
    print(f"state: {state}, input: {input}, output: {output}")
    input_seqs = find_all_input_sequences(transition_dict, state)
    for seq in input_seqs:
        print(f"Input Sequence: {seq}")
        complete_tests.append([seq, state, input, output])

with open("smtp_complete_tests.json", "w") as f:
    json.dump(complete_tests, f, indent=4)
    

    

