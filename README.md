# Repository setup required :wave:
    
Please visit the website URL :point_right: for this repository to complete the setup of this repository and configure access controls.

# Model-based Testing using LLMs

This repsitory contains the code for our paper **Eywa: Automating Model-based Testing using LLMs**

First clone the repository onto your local machine.
```bash
$ git clone https://github.com/microsoft/Model_Based_Testing_Using_LLMs.git
```

We recommend setting up a virtual environment first.
```bash
$ cd Model_Based_Testing_Using_LLMs
$ python3 -m venv eywa_env
$ source eywa_env/bin/activate
```

Install the required libraries.
```bash
$ pip3 install -e .
```

Now, you need to add the OpenAI API key to the current folder.
```bash
$ cd scripts
$ touch openai_key.txt
$ echo "sk..." > openai_key.txt
```

To generate test inputs for DNS, select any one of the options provided below as appropriate:
```bash
$ python3 dns.py --nsdi -m [ cname | dname | ipv4 | wildcard | full_lookup | rcode | authoritative | loop_count ]
```

To generate graphs on the number of runs versus the number of unique tests, as provided in the appendix of the paper:
```bash
$ python3 dns.py -m cname -r 12
$ python3 plot_graphs.py --model cname --runs 12
```
The available options for models are **cname**, **dname**, **ipv4** and **wildcard**.
