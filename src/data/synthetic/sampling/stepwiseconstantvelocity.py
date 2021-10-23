import numpy as np
from data.synthetic.sampling.constantvelocity import ConstantVelocitySimulator

class StepwiseConstantVelocitySimulator:
    '''
    Model using Newtonian dynamics in the form of constant velocities
    to model node pair interactions based on Euclidean distance in a latent space.
    '''
    def __init__(self, starting_positions:list, velocities:list, time_steps:int, beta:list, seed:int=42):
        '''
        :param starting_positions:     The 2d coordinates of each node starting position in the latent space
        :param velocities:             Velocities for each node. The velocities are constant over time
        :param T:                      The end of the time interval which the modelling runs over
        :param gamma:                  The gamma parameters used in the intensity function
        :param seed:                   The seed used to pseudo randomness of the code
        '''
        # Model parameters
        self.z0 = np.asarray(starting_positions)
        self.velocities = np.asarray(velocities)
        self.__time_steps = time_steps
        self.__beta = beta
        self.__num_of_nodes = self.z0.shape[0]

        self.__node_pair_indices = np.triu_indices(n=self.__num_of_nodes, k=1)
        np.random.seed(seed)

    def sample_interaction_times_for_all_node_pairs(self) -> list:
        '''
        Samples interactions between nodes in a dynamic temporal graph network
        based on a Non-homogeneous Poisson Process.
        The interactions are stored in a lower triangular matrix with rows
        and columns corresponding to node indecies e.g. networkEvents[3][0]
        would be a collection of floating point numbers indicating the time points 
        of node 3 and node 0 interacting.

        :returns:   A lower triangular matrix with rows and colums being node indecies
                    and entries [i][j] being a collection of time points indicating
                    the times where node j and node i interacts.
        '''
        # Upper triangular matrix of lists
        network_events = [[[] for _ in range(self.__num_of_nodes)] for _ in range(self.__num_of_nodes)]

        for t in range(len(self.__time_steps)):
            simulator =  ConstantVelocitySimulator(self.z0, self.velocities[t], self.__time_steps[t],
                                                    self.__beta, self.seed)
            network_events.append(simulator.sample_interaction_times_for_all_node_pairs())

        return network_events