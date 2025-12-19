# Model-based Testing using LLMs

This repsitory contains the code for our paper **Eywa: Automating Model-based Testing using LLMs**

First clone the repository onto your local machine.
```bash
$ git clone https://github.com/microsoft/Eywa.git
```

We recommend setting up a virtual environment first.
```bash
$ cd eywa
$ python3 -m venv eywa_env
$ source eywa_env/bin/activate
```

Navigate to the **src** directory and install the required libraries.
```bash
$ cd src
$ pip3 install -r requirements.txt
```

Now, you need to add the OpenAI API key to the current folder.
```bash
$ touch openai_key.txt
$ echo "sk..." > openai_key.txt
```

To generate test inputs for DNS, select any one of the options provided below as appropriate:
```bash
$ python3 dns.py --nsdi -m [ cname | dname | wildcard | full_lookup | rcode | authoritative | loop_count ]
```
