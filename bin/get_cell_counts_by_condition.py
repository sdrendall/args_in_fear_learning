import json
from experiment_handling import io, analysis, allen_atlas
from os import path
from pprint import pprint
from itertools import islice

classes = [
    '1DRFC',
    '1DRFT',
    '1MRFC',
    '1MRFT',
    'Ctx',
    'FC',
    'Shock',
    'Tone'
]

mice = [
    '1DRFC(34)',
    '1DRFT(13)',
    '1MRFC(3)',
    '1MRFT(5)',
    'Ctx(19)',
    'FC(30)',
    'Shock(21)',
    'Tone(25)',
    '1DRFC(35)',
    '1DRFT(16)',
    '1MRFC(1)',
    '1MRFT(7)',
    'Ctx(17)',
    'FC(31)',
    'Shock(23)',
    'Tone(27)',
    '1DRFC(33)',
    '1DRFT(14)',
    '1MRFC(2)',
    '1MRFT(6)',
    'Ctx(18)',
    'FC(29)',
    'Shock(22)',
    'Tone(26)'
]

#counts = {mouse_name: dict() for mouse_name in mice}
counts = {image_class: dict() for image_class in classes}
counts[None] = dict()


def get_class(desc):
    for class_tag in classes:
        if class_tag in desc.source_path:
            return class_tag

    print "Could not determine class of %s" % desc.source_path
    return None

def get_mouse(desc):
    for mouse_tag in mice:
        if mouse_tag in desc.source_path:
            return mouse_tag

    print "Could not determine class of %s" % desc.source_path
    return None

def update_count(count, new_count):
    for region, num_cells in new_count.iteritems():
        if region in count:
            count[region] += num_cells
        else:
            count[region] = num_cells

def main():
    from sys import argv
    if len(argv) < 4:
        print "Insufficient Arguments!"
        print "Proper Usage: %s [db_path] [output_file] [structure_data]" % argv[0]
        return

    # Initialize readers
    db_path = path.expanduser(argv[1])
    db_man = io.ImageDbManager(db_path)

    output_path = path.expanduser(argv[2])
    output_file = open(output_path, 'w')

    structure_data_path = path.expanduser(argv[3])
    structure_finder = allen_atlas.StructureFinder(structure_data_path)

    # Get cell counts
    for image_descriptor in db_man.get_image_iter():
        print "Processing %s" % image_descriptor.source_path
        image_class = get_class(image_descriptor)
        print "Detected class: ", image_class
        update_count(counts[image_class], analysis.get_cell_counts_per_region(image_descriptor))

    pprint(counts)

    # Map ids to names
    output_counts = {
        image_class: 
            {structure_finder.get_name_from_id(struct_id): 
                count for struct_id, count in count_dict.iteritems()} 
        for image_class, count_dict in counts.iteritems()
    }

    json.dump(output_counts, output_file, indent=4, sort_keys=True)


main()
