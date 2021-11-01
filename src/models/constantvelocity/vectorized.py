import torch
import torch.nn as nn
from utils.nodes.distances import vec_squared_euclidean_dist, old_vec_squared_euclidean_dist
from utils.integrals.analytical import vec_analytical_integral as evaluate_integral


class VectorizedConstantVelocityModel(nn.Module):
    '''
    Model for predicting initial conditions of a temporal dynamic graph network.
    The model predicts starting postion z0, starting velocities v0, and starting background node intensity beta
    using a Euclidean distance measure in latent space for the intensity function.
    '''
    def __init__(self, n_points:int, beta:float, device):
            '''
            :param n_points:                Number of nodes in the temporal dynamics graph network
            :param intensity_func:          The intensity function of the model
            :param integral_approximator:   The function used to approximate the non-event intensity integral
            '''
            super().__init__()
    
            self.device = device
            self.beta = nn.Parameter(torch.tensor([[beta]]), requires_grad=True)
            self.z0 = nn.Parameter(torch.rand(size=(n_points,2))*0.5, requires_grad=True) 
            self.v0 = nn.Parameter(torch.rand(size=(n_points,2))*0.5, requires_grad=True) 
    
            self.num_of_nodes = n_points
            self.n_node_pairs = n_points*(n_points-1) // 2
            self.node_pair_idxs = torch.triu_indices(row=self.num_of_nodes, col=self.num_of_nodes, offset=1)

    def old_steps(self, times:torch.Tensor) -> torch.Tensor:
        '''
        Increments the model's time by t by
        updating the latent node position vector z
        based on a constant velocity dynamic.

        :param t:   The time to update the latent position vector z with

        :returns:   The updated latent position vector z
        '''
        Zt = self.z0 + self.v0 * times.unsqueeze(1).unsqueeze(1)
        return Zt

    def steps(self, times:torch.Tensor) -> torch.Tensor:
        '''
        Increments the model's time by t by
        updating the latent node position vector z
        based on a constant velocity dynamic.

        :param t:   The time to update the latent position vector z with

        :returns:   The updated latent position vector z
        '''
        Zt = self.z0.unsqueeze(2) + self.v0.unsqueeze(2) * times
        return Zt

    def old_log_intensity_function(self, times:torch.Tensor):
        '''
        The log version of the  model intensity function between node i and j at time t.
        The intensity function measures the likelihood of node i and j
        interacting at time t using a common bias term beta


        :param t:   The time to update the latent position vector z with

        :returns:   The log of the intensity between i and j at time t as a measure of
                    the two nodes' log-likelihood of interacting.
        '''
        z = self.old_steps(times)
        d = old_vec_squared_euclidean_dist(z)
        #Only take upper triangular part, since the distance matrix is symmetric and exclude node distance to same node
        return self.beta - d

    def log_intensity_function(self, times:torch.Tensor):
        '''
        The log version of the  model intensity function between node i and j at time t.
        The intensity function measures the likelihood of node i and j
        interacting at time t using a common bias term beta


        :param t:   The time to update the latent position vector z with

        :returns:   The log of the intensity between i and j at time t as a measure of
                    the two nodes' log-likelihood of interacting.
        '''
        z = self.steps(times)
        d = vec_squared_euclidean_dist(z)
        #Only take upper triangular part, since the distance matrix is symmetric and exclude node distance to same node
        return self.beta - d


    def forward(self, data:torch.Tensor, t0:torch.Tensor, tn:torch.Tensor) -> torch.Tensor:
        '''
        Standard torch method for training of the model.

        :param data:    Node pair interaction data with columns [node_i, node_j, time_point]
        :param t0:      Start of the interaction period
        :param tn:      End of the interaction period

        :returns:       Log liklihood of the model based on the given data
        '''
        log_intensities = self.log_intensity_function(times=data[:,2])
        t = list(range(data.size()[0]))
        i = torch.floor(data[:,0]).tolist() #torch.floor to make i and j int
        j = torch.floor(data[:,1]).tolist()

        event_intensity = torch.sum(log_intensities[i,j,t])
        non_event_intensity = torch.sum(evaluate_integral(t0, tn, 
                                                        z0=self.z0, v0=self.v0, 
                                                        beta=self.beta, device=self.device).triu(diagonal=1))


        # old_log_intensities = self.old_log_intensity_function(times=data[:,2])
        # old_event_intensity = torch.sum(old_log_intensities[t, i, j])
        # old_non_event_intensity = torch.sum(evaluate_integral(t0, tn, 
        #                                                 z0=self.z0, v0=self.v0, 
        #                                                 beta=self.beta, device=self.device).triu(diagonal=1))

        # Log likelihood
        return event_intensity - non_event_intensity