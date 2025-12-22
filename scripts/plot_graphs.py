import matplotlib.pyplot as plt
from argparse import ArgumentParser
import json
def plot_graphs(dns_model, num_runs):
    if dns_model == "cname":
        stats_dir = "CNAME"
    elif dns_model == "dname":
        stats_dir = "DNAME"
    elif dns_model == "wildcard":
        stats_dir = "Wildcard"
    elif dns_model == "ipv4":
        stats_dir = "IPv4"
    else:
        raise ValueError("Invalid DNS model specified.")
    
    markers = ['o', 's', '^', 'd']
    for i, temperature in enumerate([0.2, 0.4, 0.6, 0.8]):
        stats_file = stats_dir + '/' + str(temperature) + '/0/' + "stats_" + str(temperature) + ".json"
        with open(stats_file, 'r') as f:
            stats = json.load(f)
        x = []
        y = []
        for num_run in range(num_runs):
            x.append(num_run+1)
            y.append(stats[str(num_run)]['Total_Unique_Tests'])
        
        plt.plot(x, y, marker=markers[i], label=f'Temperature {temperature}')
    plt.xlabel('Number of Runs')
    plt.ylabel('Total Unique Tests')
    
    plt.title(f'Unique Tests vs Number of Runs for {dns_model.upper()} Model')
    plt.legend()
    plt.show()
        
        
parser = ArgumentParser(description="Plot DNS Model Graphs")
parser.add_argument('-m', '--model', type=str, required=True, help="DNS model to plot (cname, dname, wildcard, ipv4)")
parser.add_argument('-r', '--runs', type=int, required=True, help="Number of runs to plot")
args = parser.parse_args()
plot_graphs(args.model, args.runs)