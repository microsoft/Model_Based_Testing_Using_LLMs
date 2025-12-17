
from eywa.llm import GPT4
import json

with open('smtp_code.c', 'r') as f:
    code = f.read()

## extract the code between line containing "smtp_server_response" and "int main()"
start = code.find("smtp_server_response")
end = code.find("int main()")
code = code[start:end]

print(code)

gpt4 = GPT4()
user_prompt = f"""
Create a python dictionary that maps the state transitions: (state,input) --> state for the following C code snippet:

{code}

Output format:

1. A python dictionary like {{ (state1, input1): state2, (state3, input2): state4, ...}}

2. Output within a json block.
""" 

gpt4_response = gpt4.query_openai_endpoint(user_prompt)

print("\n\n***** GPT-4 response *****\n\n")
print(gpt4_response)

## parse the json response
parsed_response = gpt4_response.split("```json")[1].split("```")[0]

print("\n\n***** Parsed response *****\n\n")
print(parsed_response)

with open('smtp_transition_dict.json', 'w') as f:
    json.dump(json.loads(parsed_response), f, indent=4)