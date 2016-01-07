#! /bin/bash

# Update environment
source /groups/gray/image_processing/env/activate.sh

# Run program
python ~/code/args_in_fear_learning/bin/detect_cells_for_experiment.py -e /groups/gray/sam/bigExperiment -m /groups/gray/image_processing/build/fisherman/models/median_normalized/fish_net_conv_deploy_weights.caffemodel -n /groups/gray/image_processing/build/fisherman/caffe/fish_net_conv_deploy.prototxt /groups/gray/sam/bigExperiment/big_experiment_image_db
