* Getting Started: https://github.com/batfish/batfish
* Analyzing Routing Policies Notebook: https://github.com/batfish/pybatfish/blob/master/jupyter_notebooks/Analyzing%20Routing%20Policies.ipynb

# How to get a test result?

* Pull image batfish allinone
* Install pybatfish: python -m pip install --upgrade pybatfish
* Run the docker container:

sudo docker run -d --name batfish -v batfish-data:/data -v /home/rathin/Desktop/BGP_Implementations/impl/batfish/:/notebooks/testing/ -p 8888:8888 -p 9997:9997 -p 9996:9996 batfish/allinone

* Enter into bash: sudo docker exec -it batfish bash

* cd notebooks/testing

* python3 main.py

* Result:
    - Find rmap config in "config.txt". 
    - Find batfish result output in "output.json"
    - Find test result in "result.txt" (expected,actual)

* Stop and remove the running container: 
    - sudo docker stop batfish
    - sudo docker rm batfish
* if container couldn't be stopped/removed by "sudo docker stop/rm batfish" and getting "permission denied" issue
    - sudo kill -9 $(ps aux | grep '[w]rapper.sh' | awk '{print $2}')
    - sudo docker rm batfish




