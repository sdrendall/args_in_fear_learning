#! /usr/bin/env python

import json
from os import path
from argparse import ArgumentParser
from experiment_handling import parallelization


def configure_argument_parser():
    parser = ArgumentParser(description='Launches fish net jobs for the specified vsi files')
    # Positional Args
    parser.add_argument('vsi_files', nargs='+', type=path.expanduser, 
        help='vsi file paths to read from. use (find . -name "*.vsi") from the experiment directory')
    # Flagged Args
    parser.add_argument('-N', '--net_path', type=path.expanduser, 
        help='Path to the net prototxt file defining the net architecture to deploy')
    parser.add_argument('-M', '--model_path', type=path.expanduser,
        help='Path to the caffemodel file containing the network weights to deploy with')
    parser.add_argument('-o', '--output_dir', type=path.expanduser,
        help='Path to the directory to store output files')

    # Hail Satan - They pass a string, you get a dict
    open_vsi_stats = lambda p: json.load(open(path.expanduser(p)))
    parser.add_argument('-S', '--vsi_stats', type=open_vsi_stats,
        help='Path to the vsi_stats.json file')

    return parser


def get_vsi_name(vsi_path):
    return path.splitext(path.basename(vsi_path))[0]


def generate_mask_path(vsi_path, args):
    mask_name = get_vsi_name(vsi_path) + '_fish_net_output.tif'
    return path.join(args.output_dir, mask_name)


def generate_hdf5_path(vsi_path, args):
    hdf5_name = get_vsi_name(vsi_path) + '_fish_net_output.hdf5'
    return path.join(args.output_dir, hdf5_name)


def generate_log_path(vsi_path, args):
    log_name = get_vsi_name(vsi_path) + '_fish_net_log.txt'
    return path.join(args.output_dir, log_name)


def get_normalization_offset(vsi_path, args):
    stats_elem = args.vsi_stats[vsi_path]
    return stats_elem['channel_stats'][0]['median'], stats_elem['channel_stats'][1]['median']


def create_process(vsi_path, args):
    log_path = generate_log_path(vsi_path, args)
    try:
        offset = map(str, get_normalization_offset(vsi_path, args))
    except:
        print "Could not load vsi stats for {}".format(vsi_path)
        return

    arg_list = [
        'export', 'CUDA_VISIBLE_DEVICES=`gpu_env.sh`;',
        'cast_fish_net.py',
        vsi_path,
        '-o', generate_mask_path(vsi_path, args),
        '-O', generate_hdf5_path(vsi_path, args),
        '-N', args.net_path,
        '-M', args.model_path,
        '--offset', offset[0], offset[1],
        '--scale', '0.00325218', '0.00021881',
        '--chunk_size', '6500',
        '--gpu',
        '--vsi'
    ]

    return parallelization.BatchProcess(
        *arg_list,
        log_path=log_path,
        run_time='5:00',
        queue='gpu',
        memory=16000,
        ngpus=1
    )


def main():
    parser = configure_argument_parser()
    args = parser.parse_args()

    scheduler = parallelization.BatchScheduler(max_threads=10, queue='gpu')
    processes = (create_process(vsi_path, args) for vsi_path in args.vsi_files if not path.isfile(generate_mask_path(vsi_path, args)))
    map(scheduler.add_process, filter(lambda p: p is not None, processes)) 

    scheduler.run_processes()


if __name__ == '__main__':
    main()
