"""
Example illustrating abstracting a 2-mode switched system, and mode-counting synthesis on the abstraction graph
"""

import numpy as np
from numpy.linalg import norm
from scipy.linalg import expm

import sys
import time

sys.path.append('../')
from counting import *
from abstraction import *
from rounding import *
from itertools import product
from random_cycle import random_cycle
from random import choice 

import matplotlib.pyplot as plt

cycle_set_size = 200
horizon = 10

# Define a vector fields
vf1 = lambda x : [-2*(x[0]-1.0) + x[1], -(x[0]-1.0) - 2*x[1] - x[1]**3]
vf2 = lambda x : [-2*(x[0]+1.0) + x[1], -(x[0]+1.0) - 2*x[1] - x[1]**3]
 
# Define a KL function beta(r,s) s.t. || phi(t,x) - phi(t,y) || <= beta(||x-y||, t)
kl1 = lambda r,s : np.sqrt(2) * r * norm( expm(s*np.array([[-2,  1], [-1, -2]])) , 2)

# Abstraction parameters
lb = [-2, -1.5] # lower bounds
ub = [2, 1.5]		 # upper bounds
eta = 0.05		 # space discretization
tau = 0.32		 # time discretization

eps = 0.1

# Random seed
np.random.seed(0)

if False:
    # plot bisimilarity curves
    tt = np.arange(0,2,0.01)
    vec = np.zeros(tt.shape)
    for i, t in enumerate(tt):
    	vec[i] = kl1(eps, t)
    plt.plot(tt, vec + eta/2)
    plt.plot(tt, np.ones(tt.shape)*eta/2)
    plt.plot(tt, eps*np.ones(tt.shape))
    plt.plot(tau, kl1(eps, tau) + eta/2, marker='o')
    plt.show()

# Verify that abstraction is eps-approximate bisimulation
# with respect to both KL functions
assert(verify_bisim(kl1, tau, eta, eps, 0, 1))

# Initiate abstraction
ab = Abstraction(lb, ub, eta, tau)
# add modes to abstraction
ab.add_mode(vf1, 'on')
ab.add_mode(vf2, 'off')

# extract abstraction graph
G = ab.graph
print "abstraction has ", len(G), " states"

# Set up discrete counting problem
cp = MultiCountingProblem(1)
cp.graphs[0] = G

# Counting constraint sets
cc1 = CountingConstraint(1)  # mode counting
set1 = set([node for node,attr in G.nodes_iter(data=True) if attr['mid'][0]<eps])
cc1.X[0] = set(product(set1, ['on', 'off']))

cc2 = CountingConstraint(1)  # mode counting
set2 = set([node for node,attr in G.nodes_iter(data=True) if attr['mid'][0]>-eps])
cc2.X[0] = set(product(set2, ['on', 'off']))

cc3 = CountingConstraint(1)  # mode counting
cc3.X[0] = set(product(G.nodes(), ['on']))

cc4 = CountingConstraint(1)  # mode counting
cc4.X[0] = set(product(G.nodes(), ['off']))

# Horizon
cp.T = horizon

# Loop over N
Nvec = [10**i for i in range(2,10)]
tvec = np.zeros(len(Nvec))

for i,N in enumerate(Nvec):
    t_avg = 0
    j = 1
    while j < 11:
        # Sample init condition
        cp.inits[0] = np.random.multinomial(N, [1./len(ab)]*len(ab))

        # Cycle sets
        cycle_set = []
        num = 0
        while len(cycle_set) < cycle_set_size:
            # print "sampling cycle %d" % num
            c = random_cycle(G, set([]), 2, 0.8)
            num += 1
            if (set(c) - set1) and (set(c) - set2):
                c = augment(G, c)
                cycle_set.append(c)

        cp.cycle_sets[0] = cycle_set

        # Add counting constraints
        cc1.R = 0.55 * N
        cc2.R = 0.55 * N
        cc3.R = 0.55 * N
        cc4.R = 0.55 * N

        cp.constraints = [cc1, cc2, cc3, cc4]

        start = time.time()
        print "solving N={:d}".format(N)
        stat = cp.solve_prefix_suffix(solver='gurobi', output=True, integer=True)
        end = time.time()
        print "solved N={:d} in {:f}".format(N, end-start)
        # cp.test_solution()

        if stat == 2:
            # only time the feasible ones
            t_avg = (j * t_avg + end-start)/(j+1)
            j = j+1

    tvec[i] = t_avg

# Save timing data
if True:
    np.savetxt('data_time.txt', np.vstack([Nvec, tvec]).transpose(), fmt=['%d', '%0.2f'], delimiter=',')

# Save count data
if False:
    tt = np.arange(50)
    count1 = np.zeros(tt.shape)
    count2 = np.zeros(tt.shape)
    count3 = np.zeros(tt.shape)
    count4 = np.zeros(tt.shape)

    for t in tt:
    	count1[t] = float(cp.mode_count(cc1.X, t))/sum(cp.inits[0])
    	count2[t] = float(cp.mode_count(cc2.X, t))/sum(cp.inits[0])
    	count3[t] = float(cp.mode_count(cc3.X, t))/sum(cp.inits[0])
    	count4[t] = float(cp.mode_count(cc4.X, t))/sum(cp.inits[0])

    np.savetxt('data_cc.txt', np.vstack([tt, count1, count2, count3, count4]).transpose(), fmt=['%d', '%0.2f', '%0.2f', '%0.2f', '%0.2f'], delimiter=',')

if False:
    # Save example cycle coordinates
    for cyclenum in range(len(cp.cycle_sets[0])):
        
        if sum(cp.assignments[0][cyclenum]) > 1:

            cycle = cp.cycle_sets[0][cyclenum]
            cycle_coords = np.array([G.node[v]['mid'] for v,_ in cycle])
            np.savetxt('cycle%d.txt' % cyclenum, cycle_coords, delimiter=',')
    