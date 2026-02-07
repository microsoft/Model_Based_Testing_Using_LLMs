# Model-based Testing using LLMs

This repsitory contains the code for our paper **Eywa: Automating Model-based Testing using LLMs**. Our framework uses LLMs to automatically construct modular protocol models from natural-language specifications and applies symbolic execution and differential testing to generate high-coverage tests with minimal user effort.

## Installation
Please ensure that [Docker](https://www.docker.com/) is already installed on your system and accessible to non-root users. Pull the Klee Docker image (around 10GB).
```bash
$ docker pull klee/klee:3.0
```

Next, clone the repository onto your local machine.
```bash
$ git clone https://github.com/microsoft/Model_Based_Testing_Using_LLMs.git
$ cd Model_Based_Testing_Using_LLMs
```

We recommend setting up a conda virtual environment to avoid conficts with existing libraries. Create and activate a new conda environment with Python 3.12. (install miniconda if needed by following these [instructions](https://www.anaconda.com/docs/getting-started/miniconda/install))

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

### DNS test generation:

To generate test inputs for differential testing, run the following command. (you must be in the **scripts** directory). Available options for **DNS**, are shown below:

```bash
$ python3 dns.py -t -m {model} -r {no. of runs} --timeout {value}

usage: dns.py [-h] -m {cname,dname,wildcard,ipv4,full_lookup,loop_count,rcode,authoritative} [-t] [-r RUNS] [--timeout TIMEOUT]

options:
  -h, --help            show this help message and exit
  -m {cname,dname,wildcard,ipv4,full_lookup,loop_count,rcode,authoritative}, --module {cname,dname,wildcard,ipv4,full_lookup,loop_count,rcode,authoritative}
                        The DNS module to generate inputs for.
  -t, --test            Generate inputs for differential testing.
  -r RUNS, --runs RUNS  Number of runs to generate inputs for. (default: 10)
  --timeout TIMEOUT     Klee timeout in seconds for each run. (default: 300)
```

**Quick Run**: For example, if you want to generate test inputs for CNAME with `2` LLM-written models, and with a timeout of 10s, you must run the following command:
```bash
$ python3 dns.py -t -m cname -r 2 --timeout 10
```
Note that for the specific purpose of differential testing, the `-t` flag must be enabled at all times.

Test cases will be saved in `../tests/dns/NSDI/{model}` folder within `ZoneFiles` and `Queries`.

### BGP test generation:

For **BGP** test generation, run the following command (available options are shown below):

```bash
$ python3 bgp.py -m {model} -r {no. of runs} --timeout {value}

usage: bgp.py [-h] -m {confed,rr,rmap_pl,rr_rmap} [-r RUNS] [--timeout TIMEOUT]

options:
  -h, --help            show this help message and exit
  -m {confed,rr,rmap_pl,rr_rmap}, --module {confed,rr,rmap_pl,rr_rmap}
                        The BGP module to generate inputs for.
  -r RUNS, --runs RUNS  Number of runs to generate inputs for. (default: 10)
  --timeout TIMEOUT     Klee timeout in seconds for each run. (default: 300)
```

**Quick Run**: So for instance, if you want to generate test inputs for testing BGP confederations using `2` LLM-generated models, and with a timeout of 10s, you must run the following command:

```bash
$ python3 bgp.py -m confed -r 2 --timeout 10
```

Test cases will be saved in `../tests/bgp/NSDI/{model}/tests.json` file.

### SMTP test generation:

For SMTP, we have only one option for the model i.e. "server" (you can still select the number of runs and timeout value). To generate test inputs for SMTP, run the following command (available options are shown below):

```bash
$ python3 smtp.py -m server -r {no. of runs} --timeout {value}

usage: smtp.py [-h] -m {server} [-r RUNS] [--timeout TIMEOUT]
options:
  -h, --help            show this help message and exit
  -m {server}, --module {server}
                        The SMTP module to generate inputs for.
  -r RUNS, --runs RUNS  Number of runs to generate inputs for. (default: 10)
  --timeout TIMEOUT     Klee timeout in seconds for each run. (default: 300)
```

**Quick Run**: For example, if you want to generate test inputs for SMTP server using `2` LLM-generated models, and with a timeout of 10s, you must run the following command:

```bash
$ python3 smtp.py -m server -r 2 --timeout 10
```

Test cases will be saved in `../tests/smtp/NSDI/SMTP/full_test_cases.json` file.

## Differential Testing

Navigate to the **tester** directory.
```bash
$ cd ../tester
```

To prevent permission errors (from Docker creating files with root ownership), fix permissions with:
```bash
$ sudo chown -R $USER:$USER .
```
Note: The run scripts automatically fix permissions after each Docker run, so this is typically only needed once.

### DNS:
To run differential testing with the generated test inputs in the previous step, first navigate to the **DNS** directory:
```bash
$ cd dns
```

Build the required DNS implementation images by running the following command (it might take around 30 minutes time and around 15GB memory to build all the images):

```bash
$ python3 generate_docker_images.py -l 

To disable some implementations do this:

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

Note: TrustDNS is renamed to HickoryDNS in the latest versions, but we use the TrustDNS here although it runs HickoryDNS internally.

For differential testing, we have the following options:
```bash
$ python3 test_implementations.py --path ../../tests/dns/NSDI/{model} -i -s -o -d -j -a -u
```

The above command runs all the latest DNS implementations against the test inputs stored in the specified path and disables all the older versions. These flags disable the older versions, if you want to disable some of the latest versions, you can do that by using the flags mentioned below:

```bash
model options: {CNAME,DNAME,Wildcard,IPv4,FullLookup,LoopCount,RCODE,Authoritative}
```

```bash
usage: python3 test_implementations.py [-h] [--path DIRECTORY_PATH] [--id {1,2,3,4,5}] [-r START END] [-b] [-n] [-k] [-p] [-c] [-y] [-t] [-e] [-g] [-w] 

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
  -b                    Disable Bind latest. (default: False)
  -n                    Disable Nsd latest. (default: False)
  -k                    Disable Knot latest. (default: False)
  -p                    Disable PowerDns latest. (default: False)
  -c                    Disable CoreDns latest. (default: False)
  -y                    Disable Yadifa latest. (default: False)
  -t                    Disable TrustDns latest. (default: False)
  -e                    Disable Technitium latest. (default: False)
  -g                   Disable Gdnsd latest. (default: False)
  -w                   Disable TwistedNames latest. (default: False)
```

**Quick Run**: For example, if you want to run differential testing on the test inputs generated for CNAME module with only BIND and NSD latest versions and for the test case range [3,6]:
```bash
$ python3 test_implementations.py --path ../../tests/dns/NSDI/CNAME -r 3 6 -i -s -o -d -j -a -u -k -p -c -y -t -e -g -w
```

Responses from different implementations will be printed on the terminal and also stored in `../../tests/dns/NSDI/{model}/Responses` directory.

Final differential testing results will be stored in `../../tests/dns/NSDI/{model}/Differences`.

### BGP: 

For running differential testing with BGP test inputs, first navigate to the **bgp** directory.
```bash
$ cd bgp
```
Build the Docker images for BGP implementations following `tester/bgp/README.md` instructions in this repository. (All images will take around 3.5GB memory).

Now check if `docker compose` or `docker-compose` is installed on your system by running the following command:
```bash
$ docker compose version

or 

$ docker-compose --version
```

If one of them is installed, you can use it to run the BGP implementations. If not, you can install `docker-compose` with the following command:
```bash
$ sudo wget "https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-$(uname -s)-$(uname -m)" -O /usr/local/bin/docker-compose
$ sudo chmod +x /usr/local/bin/docker-compose
```

Check if `docker-compose` is installed correctly by running the following command:
```bash
$ docker-compose --version
```

If you see something like `docker-compose version 2.24.5`, then you are good to go.

Depending on which feature you want to test, you must `cd` to the corresponding directory. For example, if you want to test BGP confederations:
```bash
$ cd confed
```
Now, run the following command:
```bash
$ python3 diff_testing.py
```

**Quick Run**: You can optionally specify a range of test cases to run using the `-r START END` flag:
```bash
$ python3 diff_testing.py -r 2 5
```
This will run test cases from 2 to 5 (inclusive, and 0-indexed). If the `-r` flag is not provided, all test cases will be run.

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

Press Enter to continue when prompted after installing opensmtpd.

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

**Quick Run**: For a quick test, SMTP also supports the `-r START END` flag if test cases have been pre-generated:
```bash
$ sudo python3 diff_testing.py -r 2 5
```
This will run test cases from 2 to 5 (inclusive, and 0-indexed). If the `-r` flag is not provided, all test cases will be run.

Results will be saved in the file: `../../tests/smtp/NSDI/SMTP/diff_results.json`

## Visualization

To reproduce similar graphs on the number of runs versus the number of unique tests, as provided in the appendix of the paper, navigate to the **scripts** directory and run the following commands:
```bash
$ python3 dns.py -m {model} -r {number of runs} --timeout {value}
$ python3 plot_graphs.py --model {model} --runs {number of runs}
```

**Quick Run**: For example, if you want to plot the graph for CNAME module with `2` runs and timeout of `10s`, then you must run the following commands:

```bash
$ python3 dns.py -m cname -r 2 --timeout 10
$ python3 plot_graphs.py --model cname --runs 2
```

The available options for models are **cname**, **dname**, **ipv4** and **wildcard**.
