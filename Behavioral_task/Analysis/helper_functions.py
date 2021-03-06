# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 16:22:54 2015

@author: Ian
"""

import numpy as np
import matplotlib.pyplot as plt
import pylab, lmfit
import random as r
from helper_classes import BiasPredModel

def track_runs(iterable):
    """
    Return the item with the most consecutive repetitions in `iterable`.
    If there are multiple such items, return the first one.
    If `iterable` is empty, return `None`.
    """
    track_repeats=[]
    current_element = None
    current_repeats = 0
    element_i = 0
    for element in iterable:
        if current_element == element:
            current_repeats += 1
        else:
            track_repeats.append((current_repeats,current_element, element_i-current_repeats))
            current_element = element
            current_repeats = 1
        element_i += 1
    track_repeats = track_repeats[1:]
    return track_repeats
    
def bar(x, y, title):
    plot = plt.bar(x,y,width = .5)
    plt.title(str(title))
    return plot

def moving_average(a, n=3) :
    ret = np.cumsum(a, dtype=float)
    ret[n:] = ret[n:] - ret[:-n]
    return ret[n - 1:] / n
    
def softmax(probs, inv_temp):
    return np.exp(probs*inv_temp)/sum(np.exp(probs*inv_temp))
    
def calc_posterior(data,prior,likelihood_dist):
    n = len(prior)
    likelihood = [dis.pdf(data) for dis in likelihood_dist]
    numer = np.array([likelihood[i] * prior[i] for i in range(n)])
    try:
        dinom = [np.sum(list(zip(*numer))[i]) for i in range(len(numer[0]))]
    except TypeError:
        dinom = np.sum(numer)
    posterior = numer/dinom
    return posterior

def genSeq(l,p):
    seq = [round(r.random())]
    for _ in range(l):
        if r.random() < p:
            seq.append(seq[-1])
        else:
            seq.append(abs(seq[-1]-1))
    return seq

def seqStats(l,p,reps):
    seqs=[]
    for _ in range(reps):
        tmp = genSeq(l,p)
        for i in track_runs(tmp):
            seqs.append(i[0])
    return (np.mean(seqs), np.std(seqs))
    
    
    
def fit_model(train_ts_dis, data, init_prior = [.5,.5], bias = True, mode = "biasmodel"):
    """
    Function to fit parameters to the bias model (recursive probability and
    task set bias) or the midline model (probability of random action)
    Mode must equal "biasmodel" or "midline". If mode == "biasmodel", bias
    can either be set to True or False. If False, tsb will be fixed at 1, 
    forcing the model to have no bias towards either task-set.
    """
    if mode == "biasmodel":
        #Fitting Functions
        def bias_fitfunc(rp, tsb, df):
            init_prior = [.5,.5]
            model = BiasPredModel(train_ts_dis, init_prior, ts_bias = tsb, recursive_prob = rp)
            model_likelihoods = []
            for i in df.index:
                c = df.context[i]
                trial_choice = df.subj_ts[i]
                conf = model.calc_posterior(c)
                model_likelihoods.append(conf[trial_choice])
            return np.array(model_likelihoods)
    
        def bias_errfunc(params,df):
            rp = params['rp']
            tsb = params['tsb']
            #minimize
            return abs(np.sum(np.log(bias_fitfunc(rp,tsb,df)))) #single value
            
        #Fit bias model
        #attempt to simplify:
        fit_params = lmfit.Parameters()
        fit_params.add('rp', value = .6, min = 0, max = 1)
        if bias == True:
            fit_params.add('tsb', value = 1, min = 0)
        else:
            fit_params.add('tsb', value = 1, vary = False, min = 0)
        out = lmfit.minimize(bias_errfunc,fit_params, method = 'lbfgsb', kws= {'df': data})
        lmfit.report_fit(out)
        return out.values
        
    elif mode == "midline":
         #Fitting Functions
        def midline_errfunc(params,df):
            eps = params['eps'].value
            context_sgn = np.array([max(i,0) for i in df.context_sign])
            choice = df.subj_ts
            #minimize
            return -np.sum(np.log(abs(abs(choice - (1-context_sgn))-eps)))
            
        #Fit bias model
        #attempt to simplify:
        fit_params = lmfit.Parameters()
        fit_params.add('eps', value = .1, min = 0, max = 1)
        midline_out = lmfit.minimize(midline_errfunc,fit_params, method = 'lbfgsb', kws= {'df': data})
        lmfit.report_fit(midline_out)
        return midline_out.values


#*********************************************
# Plotting
#*********************************************

def plot_run(sub,plotting_dict, exclude = [], fontsize = 16):
    #plot the posterior estimates for different models, the TS they currently select
    #and the vertical position of the stimulus
    sns.set_style("white")
    plt.hold(True)
    models = []
    displacement = 0
    #plot model certainty and task-set choices
    for arg in plotting_dict.values():
        if arg[2] not in exclude:
            plt.plot(sub.trial_count,sub[arg[0]]*2,arg[1], label = arg[2], lw = 2)
            plt.plot(sub.trial_count, [int(val>.5)+3+displacement for val in sub[arg[0]]],arg[1]+'o')
            displacement+=.15
            models.append(arg[0])
    plt.axhline(1, color = 'y', ls = 'dashed', lw = 2)
    plt.axhline(2.5, color = 'k', ls = 'dashed', lw = 3)
    #plot subject choices (con_shape = conforming to TS1)
    #plot current TS, flipping bit to plot correctly
    plt.plot(sub.trial_count,(sub.ts)-2, 'go', label = 'operating TS')
    plt.plot(sub.trial_count, sub.context/2-1.5,'k', lw = 2, label = 'stimulus height')
    plt.plot(sub.trial_count, sub.con_2dim+2.85, 'yo', label = 'subject choice')
    plt.yticks([-2, -1.5, -1, 0, 1, 2, 3.1, 4.1], [ -1, 0 , 1,'0%', '50%',  '100%', 'TS2 Choice', 'TS1 Choice'], size = fontsize-4 )
    plt.xticks(size = fontsize - 4)    
    plt.xlim([min(sub.index)-.5,max(sub.index)])
    plt.ylim(-2.5,5)
    #subdivide graph
    plt.axhline(-.5, color = 'k', ls = 'dashed', lw = 3)
    plt.axhline(-1.5, color = 'y', ls = 'dashed', lw = 2)
    #axes labels
    plt.xlabel('Trial Number', size = fontsize, fontweight = 'bold')
    plt.ylabel('Predicted P(TS1)', size = fontsize, fontweight = 'bold')
    ax = plt.gca()
    ax.yaxis.set_label_coords(-.1, .45)
    pylab.legend(loc='upper center', bbox_to_anchor=(0.5, 1.08),
              ncol=3, fancybox=True, shadow=True, prop={'size':fontsize}, frameon = True)
               