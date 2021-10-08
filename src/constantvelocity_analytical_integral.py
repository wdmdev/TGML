
# Set device as cpu or gpu for pytorch
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Set device as cpu or gpu for pytorch
import torch
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f'Running with pytorch device: {device}')
torch.pi = torch.tensor(torch.acos(torch.zeros(1)).item()*2)

# Imports
import wandb
import numpy as np
from utils.nodes.positions import get_contant_velocity_positions 
from argparse import ArgumentParser
import utils.visualize as visualize
from traintestgyms.standardgym import TrainTestGym
from utils.visualize.positions import node_positions
from data.synthetic.builder import DatasetBuilder
from models.constantvelocity.standard import ConstantVelocityModel




if __name__ == '__main__':


    ### Parse Arguments for running in terminal
    arg_parser = ArgumentParser()
    arg_parser.add_argument('--max_time', '-MT', default=100, type=int)
    arg_parser.add_argument('--true_beta', '-TB', default=4., type=float)
    arg_parser.add_argument('--model_beta', '-MB', default=0.25, type=float)
    arg_parser.add_argument('--learning_rate', '-LR', default=0.01, type=float)
    arg_parser.add_argument('--num_epochs', '-NE', default=100, type=int)
    arg_parser.add_argument('--non_intensity_weight', '-NIW', default=0.2, type=float)
    arg_parser.add_argument('--train_batch_size', '-TBS', default=400, type=int)
    arg_parser.add_argument('--training_portion', '-TP', default=0.8, type=float)
    args = arg_parser.parse_args()


    ### Set all input arguments
    seed = 2
    max_time = args.max_time
    true_beta = args.true_beta
    model_beta = args.model_beta  # Model-initialized beta
    learning_rate = args.learning_rate
    num_epochs = args.num_epochs
    non_intensity_weight = args.non_intensity_weight
    train_batch_size = args.train_batch_size
    training_portion = args.training_portion


    ## Initialize data_builder for simulating node interactions from known Poisson Process
    z0 = np.asarray([[-5, 0], [4, 0], [0, 3], [0, -2]])
    v0 = np.asarray([[2, 0], [-2, 0], [0, -2], [0, 1]])
    data_builder = DatasetBuilder(starting_positions=z0, starting_velocities=v0,
                        max_time=max_time, common_bias=true_beta, seed=seed)

    ### Setup model
    num_nodes = z0.shape[0]
    model = ConstantVelocityModel(n_points=num_nodes, beta=true_beta)
    print('Model initial node start positions\n', model.z0)
    model = model.to(device)

    ### Train and evaluate model
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    metrics = {
        'train_loss': [],
        'test_loss': [],
        'Bias Term - Beta': []
    }
    dataset = torch.from_numpy(data_builder.build_dataset(num_nodes, time_column_idx=2))
    gym = TrainTestGym(dataset, model, device, 
                        batch_size=train_batch_size, 
                        training_portion=training_portion,
                        optimizer=optimizer, 
                        metrics=metrics, 
                        time_column_idx=2)
    gym.train_test_model(epochs=num_epochs)

    # Print model params
    model_z0 = model.z0.cpu().detach().numpy() 
    model_v0 = model.v0.cpu().detach().numpy()
    print(f'Beta: {model.beta.item()}')
    print(f'Z: {model_z0}')
    print(f'V: {model_v0}')

    ### Log metrics to Weights and Biases
    wandb_metrics = {'metric_final_beta': metrics['Bias Term - Beta'][-1],
                    'metric_final_testloss': metrics['test_loss'][-1],
                    'metric_final_trainloss': metrics['train_loss'][-1],
                    'beta': metrics['Bias Term - Beta'],
                    'test_loss': metrics['test_loss'],
                    'train_loss': metrics['train_loss']}
    wandb.log(wandb_metrics)

    ### Visualizations
    visualize.metrics(metrics)

    ## Learned Z and true Z
    latent_space_positions = [model_z0, z0]
    visualize.compare_positions(latent_space_positions, ['Predicted', 'Actual'])

    ## Animation of learned node movements
    node_positions = get_contant_velocity_positions(model_z0, model_v0, max_time, time_steps=100)
    visualize.node_movements(node_positions, 'Predicted Node Movements', trail=False)