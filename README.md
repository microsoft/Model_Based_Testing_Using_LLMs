# Model-based Testing using LLMs

This repsitory contains the code for our paper **Eywa: Automating Model-based Testing using LLMs**. Our framework uses LLMs to automatically construct modular protocol models from natural-language specifications and applies symbolic execution and differential testing to generate high-coverage tests with minimal user effort.

## Installation
Please ensure that [Docker](https://www.docker.com/) is already installed on your system and accessible to non-root users. Pull the Klee Docker image. 
```bash
$ docker pull klee/klee:3.0
```

Next, clone the repository onto your local machine.
```bash
$ git clone https://github.com/microsoft/Model_Based_Testing_Using_LLMs.git
$ cd Model_Based_Testing_Using_LLMs
```

We recommend setting up a conda virtual environment to avoid conficts with existing libraries. Create and activate a new conda environment with Python 3.12.

```bash
$ conda create --name eywa_env python=3.12
$ conda activate eywa_env
```

Install the required libraries. The following command ensures that **eywa** is installed into your virtual environment as an importable library.
```bash
$ pip3 install -e .
```
Now, you need to add your OpenAI API key to the **scripts** folder. Follow the link "Create an API key" provided [here](https://platform.openai.com/docs/quickstart) to get one.

```bash
$ cd scripts
$ touch openai_key.txt
$ echo "<your_openai_api_key>" > openai_key.txt
```
## Test Generation

To generate test inputs for differential testing, you must be in the **scripts** directory. For **DNS**, the following options are available:
```bash
$ python3 dns.py -h
usage: dns.py [-h] -m {cname,dname,wildcard,ipv4,full_lookup,loop_count,rcode,authoritative} [-t] [-r RUNS]

options:
  -h, --help            show this help message and exit
  -m {cname,dname,wildcard,ipv4,full_lookup,loop_count,rcode,authoritative}, --module {cname,dname,wildcard,ipv4,full_lookup,loop_count,rcode,authoritative}
                        The DNS module to generate inputs for.
  -t, --test            Generate inputs for differential testing.
  -r RUNS, --runs RUNS  Number of runs to generate inputs for.
```

For example, if you want to generate test inputs for CNAME with `10` LLM-written models, you must run the following command:
```bash
$ python3 dns.py -t -m cname -r 10
```
Note that for the specific purpose of differential testing, the `-t` flag must be enabled at all times.

For **BGP** test generation, we have the following options:
```bash
$ python3 bgp.py -h
usage: bgp.py [-h] -m {confed,rr,rmap_pl,rr_rmap} [-r RUNS]

options:
  -h, --help            show this help message and exit
  -m {confed,rr,rmap_pl,rr_rmap}, --module {confed,rr,rmap_pl,rr_rmap}
                        The BGP module to generate inputs for.
  -r RUNS, --runs RUNS  Number of runs to generate inputs for.
```

So for instance, if you want to generate test inputs for testing BGP confederations using `10` LLM-generated models, you should be using the following command:
```bash
$ python3 bgp.py -m confed -r 10
```

For SMTP, we have only one option for the model i.e. "server" (you can still select the number of runs):
```bash
$ python3 smtp.py -m server -r 10
```

All the generated test cases are stored in `.../tests/{dns|bgp|smtp}/NSDI/{model}` folder as appropriate.

## Differential Testing

Navigate to the **tester** directory.
```bash
$ cd ../tester
```

### DNS:
To run differential testing with the generated test inputs in the previous step, first navigate to the **DNS** directory:
```bash
$ cd dns
```

Build the required DNS implementation images by running the following command:
```bash
$ python3 generate_docker_images.py -l 

To disable some implementations do this:
# parser.add_argument('-b', help='Disable Bind.', action="store_true")
#     parser.add_argument('-n', help='Disable Nsd.', action="store_true")
#     parser.add_argument('-k', help='Disable Knot.', action="store_true")
#     parser.add_argument('-p', help='Disable PowerDns.', action="store_true")
#     parser.add_argument('-c', help='Disable CoreDns.', action="store_true")
#     parser.add_argument('-y', help='Disable Yadifa.', action="store_true")
#     parser.add_argument('-m', help='Disable MaraDns.', action="store_true")
#     parser.add_argument('-t', help='Disable TrustDns.', action="store_true")
#     parser.add_argument('-g', help='Disable Gdnsd.', action="store_true")
#     parser.add_argument('-w', help='Disable TwistedNames.', action="store_true")
#     parser.add_argument('-e', help='Disable Technitium.', action="store_true")

-b : Disable Bind.
-n : Disable Nsd.
-k : Disable Knot.
-p : Disable PowerDns.
-c : Disable CoreDns.
-y : Disable Yadifa.
-t : Disable TrustDns.
-g : Disable Gdnsd.
-w : Disable TwistedNames.
-e : Disable Technitium.
```

For differential testing, we have the following options:
```bash
$ python3 test_implementations.py --path ../../tests/dns/NSDI/{model} -i -s -o -d -j -a -u
```

Runs all the latest DNS implementations against the test inputs stored in the specified path and disables all the older versions.

model: [CNAME|DNAME|Wildcard|IPv4|FullLookup|LoopCount|RCODE|Authoritative]

```bash
usage: python3 test_implementations.py [-h] [--path DIRECTORY_PATH]
                                                     [--id {1,2,3,4,5}] [-r START END] [-b]
                                                     [-n] [-k] [-p] [-c] [-y] [-m] [-t] [-e] 

Runs tests with valid zone files on different implementations.
Either compares responses from mulitple implementations with each other or uses a
expected response to flag differences (only when one implementation is passed for testing).

optional arguments:
  -h, --help            show this help message and exit
  --path DIRECTORY_PATH  The path to the directory containing ZoneFiles and either Queries or
                        ExpectedResponses directories.
                        (default: Results/ValidZoneFileTests/)
  --id {1,2,3,4,5}       Unique id for all the containers (useful when running comparison in
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
```
Results will be stored in `../../tests/dns/NSDI/{model}/Differences`.

### BGP: 

For running differential testing with BGP test inputs, first navigate to the **bgp** directory.
```bash
$ cd bgp
```
Build the Docker images for BGP implementations following this [README](https://github.com/microsoft/Model_Based_Testing_Using_LLMs/blob/main/tester/bgp/README.md).
Depending on which feature you want to test, you must `cd` to the corresponding directory. For example, if you want to test BGP confederations:
```bash
$ cd confed
```
Now, run the following command:
```bash
$ python3 diff_testing.py
```
Results will be saved in test directory i.e. `../../tests/bgp/NSDI/{model}`

### SMTP:
For running differential testing with SMTP test inputs, first navigate to the **smtp** folder.

```bash
$ cd smtp
```

To run the **smtpd** server, we need Python3.8. The other two implementations **aiosmtpd** and **opensmtpd** do not have these restrictions.

Open a new terminal and navigate to the current working directory.
Download the required libraries.
```bash
$ sudo apt-get install opensmtpd
$ sudo apt-get install python3-aiosmtpd
$ sudo apt-get install python3-tqdm
```
Next, run the following commands:
```bash
$ conda create --name smtp_env python=3.8
$ conda activate smtp_env
$ python3 server_smtpd.py
```
This will start the **smtpd** server. 
Keeping the process running on this terminal, go back to the previous terminal and run the following command. This starts the other two SMTP servers and performs differential testing on all three:
```bash
$ sudo python3 diff_testing.py
```

Results will be saved in the file: `../../tests/smtp/NSDI/SMTP/diff_results.json`

## Visualization

To reproduce similar graphs on the number of runs versus the number of unique tests, as provided in the appendix of the paper, navigate to the **scripts** directory and run the following commands:
```bash
$ python3 dns.py -m cname -r 12
$ python3 plot_graphs.py --model cname --runs 12
```
The available options for models are **cname**, **dname**, **ipv4** and **wildcard**.
