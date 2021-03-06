#! /usr/bin/env python

import json
from experiment_handling import io, parallelization
from argparse import ArgumentParser
from os import path, getcwd

FISHERMAN_ROOT = '/groups/gray/image_processing/build/fisherman'

def configure_parser():
    parser = ArgumentParser(description='Detects cells in vsi images in an experiment')
    parser.add_argument('-e', '--experiment_path', default=getcwd(),
                        help='The root directory containing the data to be processed.'
                             '  Defaults to the current directory.')
    parser.add_argument('-m', '--model_path', 
                        default=path.join(FISHERMAN_ROOT, 'models/original_and_qc/fish_net_conv_deploy_weights.caffemodel'),
                        help='Path to the caffemodel to be used for cell detection'
                             'Default: $FISHERMAN/models/original_and_qc/fish_net_conv_deploy_weights.caffemodel')
    parser.add_argument('-n', '--net_path',
                        default=path.join(FISHERMAN_ROOT, 'caffe/fish_net_conv_deploy.prototxt'),
                        help='Path to the net prototxt file to use for cell detection'
                             'Default: $FISHERMAN/caffe/fish_net_conv_deploy.prototxt')
    parser.add_argument('-c', '--chunk_size', default=1800,
                        help='The width of chunks to split input vsis into. '
                        'This value should be as large as possible before memory issues are encounted. '
                        'Chunks are square so the height will equal the width. Default = 1800')
    parser.add_argument('--flip', default=False, action='store_true',
                        help='Corrects for vsi files that have been flipped vertically')
    parser.add_argument('--flop', default=False, action='store_true',
                        help='Corrects for vsi files that have been flipped horizontally')
   
    return parser

def compose_output_path(im_data, suffix):
    # removes '_downsampled' from the downsampled image path and appends a suffix
    return im_data['downsampledImagePath'].rsplit('_', 1)[0] + suffix

def create_process(args, entry):
    experiment_path = path.expanduser(args.experiment_path)
    entry['detectionLog'] = compose_output_path(entry, u'_detectionOutputLog.txt')
    entry['detectedCellsPath'] = compose_output_path(entry, u'_detectedCells.p')
    arg_list = ['pickle_cells_from_metadata.py', 
        '-i', json.dumps(entry),
        '-e', args.experiment_path,
        '-m', args.model_path,
        '-n', args.net_path,
        '-c', str(args.chunk_size)
    ]

    if args.flip:
        arg_list += ['--flip']

    if args.flop:
        arg_list += ['--flop']

    arg_list += [path.join(experiment_path, entry['detectedCellsPath'])]

    log_path = path.join(experiment_path, entry['detectionLog'])
    return parallelization.BatchProcess(*arg_list, cwd=args.experiment_path, log_path=log_path, run_time='6:00')

def main():
    parser = configure_parser()
    args = parser.parse_args()

    experiment_path = path.expanduser(args.experiment_path)
    metadata_handler = io.MetadataManager(experiment_path)

    scheduler = parallelization.Scheduler(max_threads=75)
    for entry in metadata_handler.metadata:
        if not entry['exclude']:
            scheduler.add_process(create_process(args, entry))
        else:
            print "Entry %s is marked for exclusion" % entry['vsiPath']

    print "Launching Cell Detection Jobs"

    scheduler.run_processes()

    print "Detection Jobs Launched. Run bjobs command for job status"

if __name__ == '__main__':
    main()
