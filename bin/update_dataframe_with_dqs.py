import pandas
from os import path
from experiment_handling import io
from itertools import islice, izip

def get_entry_from_name(name, metadata):
    for entry in metadata:
        if name in entry['vsiPath']:
            return entry

    print "No Entry Found for image %s" % name
    return {}


def main():
    from sys import argv
    if len(argv) < 4:
        print "Insufficient Arguments!"
        print "Proper Usage: %s [in_path] [out_path] [experiment_path]"
        return

    in_path = path.expanduser(argv[1])
    out_path = path.expanduser(argv[2])
    exp_path = path.expanduser(argv[3])

    df = pandas.read_csv(in_path)
    meta_man = io.MetadataManager(exp_path)

    unique_ims = set(df['image'])
    entry_map = {im_name: get_entry_from_name(im_name, meta_man.metadata) for im_name in unique_ims}
    zipped = izip(df['image'], df['region'], df['hemisphere'])

    dqs = [[region, hemisphere] in entry_map[im_name].get('regionIdsToExclude', list()) for im_name, region, hemisphere in zipped]
    slice_usabilities = [entry_map[im_name].get('sliceUsable', None) for im_name in df['image']]

    df['disqualified'] = dqs
    df['slice_usable'] = slice_usabilities
    df.to_csv(out_path)


main()
