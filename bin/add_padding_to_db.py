import json
import numpy
from experiment_handling import io
from os import path

def main():
    from sys import argv
    if len(argv) < 4:
        print "Insufficient arguments!"
        print "Proper Usage: %s [db_path] [experiment_path] [offset_file]"
        return

    db_path = path.expanduser(argv[1])
    db_man = io.ImageDbManager(db_path, readonly=False)

    experiment_path = path.expanduser(argv[2])
    meta_man = io.MetadataManager(experiment_path)

    offset_path = path.expanduser(argv[3])
    offsets = json.load(open(offset_path))

    for i, offset in enumerate(offsets):
        print "Updating image %d/%d" % (i, len(offsets))
        key = offset['vsi_path'][2:]

        try:
            image = db_man.get_image(key)
            image.region_map_offset = offset['pad_size']

            metadata = meta_man.get_entry_by_attribute('vsiPath', key)
            region_map = io.load_mhd(path.join(experiment_path, metadata['registeredAtlasLabelsPath']))[0]
            hemisphere_map = io.load_mhd(path.join(experiment_path, metadata['registeredHemisphereLabelsPath']))[0]

            image.region_map = numpy.rot90(region_map, k=2)
            image.hemisphere_map = numpy.rot90(hemisphere_map, k=2)

            db_man.add_image(image)

        except:
            print "Failed to update image with key: %s" % key

main()
