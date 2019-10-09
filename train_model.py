#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 10 19:16:35 2019

@author: Rodrigo Castro
"""

import numpy as np
import torch
from torch.autograd import Variable
import torch.nn.functional as F

import matplotlib.pyplot as plt


'''
Form of the data [ E , S ]:
E is a tensor containing all of the sequences of conditioning events (the chord progression of each note sequence)
Each event should be a row vector
The shape of E should be [# event sequences, # events in each example , event embedding size]
S is the list of tensors each epresenting a signal sequence (note sequences)
The signal sequence S[i] is conditioned to the event sequence E[i,:,:]
Each signal should be a row vector
i-th signal sequence length = S[i].size(0)
z_size denotes the hidden layer size for event sequence E
Z_size denotes the hidden layer size for signal sequence S
'''


def dimensions(E,S): 
    
    num_event_examples, num_events , event_emb_size  = E.shape    
    num_seq_examples = len(S)
    signal_emb_size = S[0].size(1)
    
    dims = [num_event_examples, num_events , event_emb_size, num_seq_examples, signal_emb_size ]
    
    return dims


def create_parameters(z_size, Z_size):
    
    W_ze = Variable(torch.randn( event_emb_size , z_size ), requires_grad = True)
    W_zz = Variable(torch.randn( z_size , z_size ), requires_grad = True)
    b_z = Variable(torch.randn( 1 , z_size ), requires_grad = True)
    
    W_update_ze = Variable(torch.randn( event_emb_size , z_size ), requires_grad = True)
    W_update_zz = Variable(torch.randn( z_size , z_size ), requires_grad = True)
    b_update_z = Variable(torch.randn( 1 , z_size ), requires_grad = True)
    
    W_forget_ze = Variable(torch.randn( event_emb_size , z_size ), requires_grad = True)
    W_forget_zz = Variable(torch.randn( z_size , z_size ), requires_grad = True)
    b_forget_z = Variable(torch.randn( 1 , z_size ), requires_grad = True)
    
    W_output_ze = Variable(torch.randn( event_emb_size , z_size ), requires_grad = True)
    W_output_zz = Variable(torch.randn( z_size , z_size ), requires_grad = True)
    b_output_z = Variable(torch.randn( 1 , z_size ), requires_grad = True)
    
    W_Zz = Variable(torch.randn( z_size , Z_size ), requires_grad = True)
    W_ZZ = Variable(torch.randn( Z_size , Z_size ), requires_grad = True)
    W_Zs = Variable(torch.randn( signal_emb_size , Z_size ), requires_grad = True)
    b_Z = Variable(torch.randn( 1 , Z_size ), requires_grad = True)
    
    W_update_ZZ = Variable(torch.randn( Z_size , Z_size ), requires_grad = True)
    W_update_Zs = Variable(torch.randn( signal_emb_size , Z_size ), requires_grad = True)
    b_update_Z = Variable(torch.randn( 1 , Z_size ), requires_grad = True)
    
    W_forget_ZZ = Variable(torch.randn( Z_size , Z_size ), requires_grad = True)
    W_forget_Zs = Variable(torch.randn( signal_emb_size , Z_size ), requires_grad = True)
    b_forget_Z = Variable(torch.randn( 1 , Z_size ), requires_grad = True)
    
    W_output_ZZ = Variable(torch.randn( Z_size , Z_size ), requires_grad = True)
    W_output_Zs = Variable(torch.randn( signal_emb_size , Z_size ), requires_grad = True)
    b_output_Z = Variable(torch.randn( 1 , Z_size ), requires_grad = True)
    
    W_yZ = Variable(torch.randn(  Z_size , signal_emb_size ), requires_grad = True)
    b_y = Variable(torch.randn( 1 , signal_emb_size ), requires_grad = True)
    
    
    net_parameters = [ W_ze , W_zz , b_z ,\
                      W_update_ze , W_update_zz , b_update_z ,\
                      W_forget_ze , W_forget_zz , b_forget_z ,\
                      W_output_ze , W_output_zz , b_output_z ,\
                      W_Zz , W_ZZ , W_Zs , b_Z,\
                      W_update_ZZ , W_update_Zs , b_update_Z ,\
                      W_forget_ZZ , W_forget_Zs , b_forget_Z ,\
                      W_output_ZZ , W_output_Zs , b_output_Z ,\
                      W_yZ , b_y ]
    
    return net_parameters


def count_parameters(parameters):
    count = 0
    for item in parameters:
        count += item.size(0)*item.size(1)
        
    return count


def get_durations_vector(durations_list, signal_emb_size, min_pitch, max_pitch, rest=True):
    
    assert signal_emb_size == max_pitch - min_pitch + 1 + rest + len(durations_list)
    idx_ini = max_pitch - min_pitch + 1 + rest
    durations_vector = torch.zeros(signal_emb_size,1)   
    for duration_idx, duration in enumerate(durations_list):
        durations_vector[idx_ini + duration_idx] = float(duration)
   
    return durations_vector, idx_ini


def forward_pass(e,s):
    #e is one sequence of e.size(1) events
    #s is one sequence of s.size(1) signals
    
    W_ze , W_zz , b_z ,\
    W_update_ze , W_update_zz , b_update_z ,\
    W_forget_ze , W_forget_zz , b_forget_z ,\
    W_output_ze , W_output_zz , b_output_z ,\
    W_Zz , W_ZZ , W_Zs , b_Z,\
    W_update_ZZ , W_update_Zs , b_update_Z ,\
    W_forget_ZZ , W_forget_Zs , b_forget_Z ,\
    W_output_ZZ , W_output_Zs , b_output_Z ,\
    W_yZ , b_y ,\
    = net_parameters
    
    z_initial_hidden_state  = torch.zeros(1,z_size)
    Z_initial_hidden_state  = torch.zeros(1,Z_size)
    initial_memory_cell_z   = torch.zeros(1,z_size)
    initial_memory_cell_Z   = torch.zeros(1,Z_size)

    event_steps = e.size(0)
    
    z            = torch.zeros( event_steps , z_size )    
    z_prev       = z_initial_hidden_state
    cell_z_prev  = initial_memory_cell_z    
    for i in reversed(range(0,event_steps)):
        event = torch.unsqueeze(e[i,:],0)
        
        pre_cell_z_step  = torch.tanh( torch.mm( z_prev , W_zz ) + torch.mm( event , W_ze ) + b_z )
        update_z         = torch.sigmoid( torch.mm( z_prev , W_update_zz ) + torch.mm( event , W_update_ze ) + b_update_z )
        forget_z         = torch.sigmoid( torch.mm( z_prev , W_forget_zz ) + torch.mm( event , W_forget_ze ) + b_forget_z )
        output_z         = torch.sigmoid( torch.mm( z_prev , W_output_zz ) + torch.mm( event , W_output_ze ) + b_output_z )
        cell_z_next      = torch.mul( update_z , pre_cell_z_step ) + torch.mul( forget_z , cell_z_prev )
        z_next           = torch.mul( output_z , torch.tanh( cell_z_next ) )
        
        z[i,:]       = z_next   
        cell_z_prev  = cell_z_next
        z_prev       = z_next

        
    signal_steps = s.size(0)
        
    Z                    = torch.zeros(signal_steps, Z_size)       
    Z_prev               = Z_initial_hidden_state
    cell_Z_prev          = initial_memory_cell_Z
    signal_prev          = torch.zeros( 1 , signal_emb_size )
    dynamic_idx          = 0
    for i in range(0,signal_steps):
        
        dynamic_idx         += int( torch.mm( signal_prev , durations_vector ) )
        conditioning_hidden  = torch.unsqueeze(z[dynamic_idx,:], 0)
    
        pre_cell_Z_step  = torch.tanh( torch.mm( Z_prev , W_ZZ ) + torch.mm( signal_prev , W_Zs ) + torch.mm(conditioning_hidden , W_Zz) + b_Z )
        update_Z         = torch.sigmoid( torch.mm( Z_prev , W_update_ZZ ) + torch.mm( signal_prev , W_update_Zs ) + b_update_Z )
        forget_Z         = torch.sigmoid( torch.mm( Z_prev , W_forget_ZZ ) + torch.mm( signal_prev , W_forget_Zs ) + b_forget_Z )
        output_Z         = torch.sigmoid( torch.mm( Z_prev , W_output_ZZ ) + torch.mm( signal_prev , W_output_Zs ) + b_output_Z )
        cell_Z_next      = torch.mul( update_Z , pre_cell_Z_step ) + torch.mul( forget_Z , cell_Z_prev )
        Z_next           = torch.mul( output_Z , torch.tanh( cell_Z_next ) )
        
        Z[i,:]       = Z_next  
        cell_Z_prev  = cell_Z_next
        Z_prev       = Z_next
        signal_prev = torch.unsqueeze(s[i,:], 0)
    
    y_hat_pre     = torch.mm(Z, W_yZ ) + b_y
    y_hat_pitch   = F.softmax( y_hat_pre[:,0:rythym_idx_ini] , dim=1 )
    y_hat_rhythm  = F.softmax( y_hat_pre[:,rythym_idx_ini:] , dim=1 )
    y_hat         = torch.cat((y_hat_pitch , y_hat_rhythm ), dim = 1)
    
    return y_hat_pre

#stochastic GD:
def train_parameters_stoch( loss_func, optimizer ):
    
    J_hist=[]
    for epoch in range(1,epochs+1):
        for j in range(num_seq_examples):
            optimizer.zero_grad()
            e = E[j,:,:]
            s = S[j]
            y_hat = forward_pass(e,s)
            J = loss_func(y_hat,s)           
            J.backward()
            optimizer.step()
            J_hist.append(J)
            if j%50 == 0:
              print('Epoch: '+str(epoch)+', examples trained: ' + str(j) + ', Cost: ' + str(J))
        #print('Epoch ' + str(epoch) + ', Cost: ' + str(J))
    
    plt.plot(J_hist[5:])
    plt.xlabel('Gradient steps')
    vert_label=plt.ylabel('Loss')
    vert_label.set_rotation(0)


def loss_sum():
    SUM = torch.Tensor([0])
    for j in range(num_seq_examples):
        e = E[j,:,:]
        s = S[j]
        y_hat = forward_pass(e,s)
        J = loss_func(y_hat,s)
        SUM = SUM + J
        if j%50 == 0:
             print('Examples processed for loss: ' + str(j))
    SUM = SUM/num_seq_examples
             
    return SUM
    
#Batch GD:    
def train_parameters_batch( loss_func, optimizer ):
    
    J_hist=[]
    for epoch in range(1,epochs+1):
        optimizer.zero_grad()
        J = loss_sum()
        J.backward()
        optimizer.step()
        J_hist.append(J.item())               
        print('Epoch ' + str(epoch) + ', Cost: ' + str(J))
    
    plt.plot(J_hist)
    plt.xlabel('Epochs')
    vert_label=plt.ylabel('Loss')
    vert_label.set_rotation(0)



#------------------------------------- UNDER CONSTRUCTION --------------------------------------------#

torch.manual_seed(12)

E, S, durations_list, min_pitch, max_pitch = torch.load('Datasets/Parker_Dataset.pt')

z_size = 16       #hidden layer dimension of event LSTM
Z_size = 48       #hidden layer dimension of signal LSTM

num_event_examples, num_events, event_emb_size, num_seq_examples, signal_emb_size = dimensions(E,S)
durations_vector, rythym_idx_ini = get_durations_vector(durations_list, signal_emb_size, min_pitch, max_pitch, rest=True)


net_parameters = create_parameters(z_size, Z_size)
num_parameters = count_parameters(net_parameters)
print(f'There are {num_parameters} parameters to train.')


LR          = 0.0005
epochs      = 10
WeightDecay = 0 #1e-6
Momentum    = 0.5

#loss_func = torch.nn.MSELoss()    #if used, return y_hat instead of y_hat_pre
loss_func = torch.nn.BCEWithLogitsLoss()
optimizer = torch.optim.RMSprop(net_parameters,lr=LR, alpha=0.99, eps=1e-8, weight_decay = WeightDecay, momentum = Momentum, centered=True)
scheduler  = torch.optim.lr_scheduler.StepLR(optimizer, step_size=100, gamma=0.1, last_epoch=-1)


train_parameters_stoch( loss_func, optimizer )
#train_parameters_batch( loss_func, optimizer )


#Importing parameters from file and testing:
#net_parameters = torch.load('net_parameters_cpu.pt')
#solo, solo_prediction , raw_prediction = predict_new()
#solo.write('midi', 'midi_prueba.mid')