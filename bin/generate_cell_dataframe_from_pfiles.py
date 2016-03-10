import cPickle as pickle
from glob import glob
from os import path
from experiment_handling import dataframes
from itertools import imap, chain

def main():
    from sys import argv:
        if len(argv) < 3:
            print "Insufficient Argumets!"
            print "Proper Usage: %s [output_path] [p_files]" % argv[0]
            return

    csv_path = path.expanduser(argv[1])
    path_exprs = imap(path.expanduser, argv[2:])
    p_file_paths = chain(imap(glob, path_exprs))
    image_iter = (open(file_path) for file_path in p_file_paths)

    df = dataframes.get_dataframe_from_image_sequence(image_iter)
    df.to_csv(csv_path)

    return
