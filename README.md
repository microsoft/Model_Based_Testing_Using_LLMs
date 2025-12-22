# Model-based Testing using LLMs

This repsitory contains the code for our paper **Eywa: Automating Model-based Testing using LLMs**. Our framework uses LLMs to automatically construct modular protocol models from natural-language specifications and applies symbolic execution and differential testing to generate high-coverage tests with minimal user effort.

## Installation
First clone the repository onto your local machine.
```bash
$ git clone https://github.com/microsoft/Model_Based_Testing_Using_LLMs.git
$ cd Model_Based_Testing_Using_LLMs
```

We recommend setting up a virtual environment in Python to avoid conficts with pre-installed libraries.
```bash
$ python3 -m venv eywa_env
$ source eywa_env/bin/activate
```
Alternatively, you could use a **conda** virtual environment.

```bash
$ conda create --name eywa_env python=3.10
$ conda activate eywa_env
```

Install the required libraries. The following command ensures that **eywa** is installed into your virtual environment as an importable library.
```bash
$ pip3 install -e .
```
Now, you need to add your OpenAI API key to the **scripts** folder.
```bash
$ cd scripts
$ touch openai_key.txt
$ echo "sk..." > openai_key.txt
```

## Test generation

To generate test inputs for DNS, you can run the following command(s) from the **scripts** directory. Select any one of the options provided below as appropriate:
```bash
$ python3 dns.py --nsdi -m [ cname | dname | ipv4 | wildcard | full_lookup | rcode | authoritative | loop_count ]
```

** Add BGP and SMTP and write the names of the folders (containing the tests) that are created. I haven't written it for DNS because the code currently creates a folder named SIGCOMM. So I would have to make changes to the code itself and that can create merge conflicts. If possible, you could do it too.**
## Differential testing

To perform differential testing, using the generated test cases, navigate to the **tests** directory.

```bash
$ cd ../tests
```

** Add bash commands for running differential testing. Results must be saved in a particular folder/file for easy readability and comparison **
### DNS
### BGP
### SMTP

## Visualization

To reproduce similar graphs on the number of runs versus the number of unique tests, as provided in the appendix of the paper:
```bash
$ cd ../scripts
$ python3 dns.py -m cname -r 12
$ python3 plot_graphs.py --model cname --runs 12
```
The available options for models are **cname**, **dname**, **ipv4** and **wildcard**.
