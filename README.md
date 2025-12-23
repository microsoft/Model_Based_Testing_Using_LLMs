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


# Test Generation

go to 'scripts/'

DNS: python dns.py -m <module> -n -r <runs>

BGP: python bgp.py -m <module> -n -r <runs>

SMTP: python smtp.py -m <module> -n -r <runs>

Tests are saved in tests/{bgp/dns/smtp}/NSDI/{model}

# Test Execution

go to 'tester/'

## DNS: 

go to 'dns'. 

usage: python3 -m Scripts.test_with_valid_zone_files [-h] [-path DIRECTORY_PATH]
                                                     [-id {1,2,3,4,5}] [-r START END] [-b]
                                                     [-n] [-k] [-p] [-c] [-y] [-m] [-t] [-e] [-l]

Runs tests with valid zone files on different implementations.
Either compares responses from mulitple implementations with each other or uses a
expected response to flag differences (only when one implementation is passed for testing).

optional arguments:
  -h, --help            show this help message and exit
  -path DIRECTORY_PATH  The path to the directory containing ZoneFiles and either Queries or
                        ExpectedResponses directories.
                        (default: Results/ValidZoneFileTests/)
  -id {1,2,3,4,5}       Unique id for all the containers (useful when running comparison in
                        parallel). (default: 1)
  -r START END          The range of tests to compare. (default: All tests)
  -b                    Disable Bind. (default: False)
  -n                    Disable Nsd. (default: False)
  -k                    Disable Knot. (default: False)
  -p                    Disable PowerDns. (default: False)
  -c                    Disable CoreDns. (default: False)
  -y                    Disable Yadifa. (default: False)
  -m                    Disable MaraDns. (default: False)
  -t                    Disable TrustDns. (default: False)
  -e                    Disable Technitium. (default: False)
  -l, --latest          Test using latest image tag. (default: False)

## BGP: 

go to 'bgp'

for each model {confed/rr/rmap_pl/rr_rmap} run `python diff_testing.py`. Results will be saved in test directory i.e. "../../../tests/bgp/NSDI/{model}"

## SMTP:

go to 'smtp'.

- Run `python server_smtpd.py` from a separate terminal (needs python 3.8)

for executing smtp server model test cases, run `python diff_testing.py`. Results will be saved in test directory i.e. "../../../tests/smtp/NSDI/SMTP"
