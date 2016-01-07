import numpy
import pandas
from itertools import imap, izip
from experiment_handling import io
from skimage.io import imread
from os import path, mkdir
from pylab import figure, imshow, scatter, savefig, close, cm


def generate_output_path(output_dir, entry):
    output_base = path.splitext(path.basename(entry['vsiPath']))[0]
    return path.join(output_dir, output_base + '_cell_overlay.png')


def centroid_to_index(centroid, scale, offset):
    return numpy.round(centroid/scale + offset).astype(numpy.uint16)
    

def main():
    from sys import argv
    if len(argv) < 4:
        print "Insufficient Arguments!"
        print "Proper Usage: %s [db_path] [csv_path] [experiment_path] [output_dir]"
        return

    db_path = path.expanduser(argv[1])
    csv_path = path.expanduser(argv[2])
    experiment_path = path.expanduser(argv[3])

    if len(argv) < 5:
        output_dir = path.join(experiment_path, 'detected_cell_overlays')
        print "Output dir not specified!"
        print "Saving output images to %s" % output_dir
    else:
        output_dir = path.expanduser(argv[4])

    if not path.exists(output_dir):
        mkdir(output_dir)

    db_man = io.ImageDbManager(db_path)
    metadata_man = io.MetadataManager(experiment_path)
    df = pandas.read_csv(csv_path)
    df = df[numpy.logical_not(df.disqualified)]
    df = df[df.region > 0]
    df = df[(df.number_of_pixels > 350) & (df.number_of_pixels < 7000)]
    df = df[df['95th percentile'] > 2**-8.5]

    for image in db_man.get_image_iter():
        # Get corresponding metadata
        entry = metadata_man.get_entry_by_attribute('vsiPath', image.source_path)
        rows = df[df['image'] == path.basename(image.source_path)]

        # Load downsampled image
        ds_im_path = path.join(experiment_path, entry['downsampledImagePath'])
        ds_im = io.load_mhd(ds_im_path)[0]

        figure()
        imshow(ds_im, cmap=cm.Greys)

        if not rows.empty:
            # Plot cells
            centroids = [centroid_to_index(centroid, image.region_map_scale, image.region_map_offset) 
                for centroid in imap(numpy.asarray, izip(rows['centroid_row'], rows['centroid_col']))]
            rows, cols = zip(*centroids)

            scatter(cols, rows, color='b', s=2, alpha=.3)

        # Save image
        output_path = generate_output_path(output_dir, entry)
        savefig(output_path)
        close()


main()
