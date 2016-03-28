import numpy
import json
import bioformats
import javabridge
import argparse
import os
from bioformats import log4j
from experiment_handling import io


def configure_parser():
    parser = argparse.ArgumentParser(description='Generates a histogram of intensity values for vsis in an experiment')
    parser.add_argument('--experiment_path', '-e', type=os.path.expanduser, default=os.getcwd(), 
        help='The experiment path where vsi files are located. Defaults to CWD')
    parser.add_argument('--vsi_filename', '-v', default=1.0, type=float, 
        help='Vsi file name used to locate vsi image in the metadata')
    parser.add_argument('--pixel_fraction', '-p', default=1.0, type=float, 
        help='Fraction of vsi pixels to extract stats from. Must be a number between 0 and 1. Defaults to 1')
    parser.add_argument('--output_file', '-o', type=os.path.expanduser, default='histogram.json',
        help='Output file to store histogram bins and counts as comma separated values')
    parser.add_argument('--number_of_bins', '-n', type=int, default=10, 
        help='Number of histogram bins')
    #parser.add_argument('--channel_of_interest', '-c', type=list, default=None)

    return parser


def load_vsi(vsi_path):
    """
    Load a vsi image at the given path.  The channels that are loaded, 
     and the order in which they are loaded are currently hard coded

    Note: This requires an active jvm via javabridge 
     (i.e. javabridge.start_vm(class_path=bioformats.JARS) must have been called prior to using this function)
    """
    print "Loading %s" % vsi_path
    with bioformats.ImageReader(vsi_path) as reader:
        #dapi = reader.read(c=0, rescale=False).astype(numpy.uint16)
        cfos = reader.read(c=1, rescale=False).astype(numpy.uint16)

    #return numpy.dstack((cfos, dapi))
    return cfos


def main():
    parser = configure_parser()
    args = parser.parse_args()

    meta_man = io.MetadataManager(experiment_path=args.experiment_path)
    output_file = open(args.output_file, 'w')

    entry = meta_man.get_entry_from_name(os.path.basename(args.vsi_filename))

    javabridge.start_vm(class_path=bioformats.JARS)
    log4j.basic_config()

    if entry is not None:
        image = load_vsi(os.path.join(args.experiment_path, entry['vsiPath']))
        number_of_samples = numpy.ceil(image.size * args.pixel_fraction)
        samples = numpy.random.choice(image.flatten(), number_of_samples, replace=False)

        histogram, bins = numpy.histogram(samples, bins=args.number_of_bins, range=(0.0, 2**16 - 1))
        percentiles = map(float, range(0, 101))
        percentile_values = numpy.percentile(image, percentiles)
    else:
        print "Could not locate %s in metadata!" %s args.vsi_filename
        javabridge.kill_vm()
        return

    javabridge.kill_vm()
    
    output_obj = {
        'bins': list(bins),
        'histogram': list(histogram),
        'n': number_of_samples,
        'percentiles': percentiles,
        'percentile_values': list(percentile_values)
    }

    json.dump(output_obj, output_file)
    output_file.close()


if __name__ == '__main__':
    main()
