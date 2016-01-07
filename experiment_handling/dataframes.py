import pandas
import numpy
import re
from os import path
from experiment_handling import io, analysis


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


def get_class(path):
    for class_tag in classes:
        if class_tag in path:
            return class_tag

    print "Could not determine class of %s" % path
    return None


def get_animal(path):
    for cls in classes:
        exp = r'{}\(([0-9]+)\)'.format(cls)
        match = re.search(exp, path)
        if match:
            return match.group(1)

    print "Could not determine animal of %s" % path
    return None


def get_slide(path):
    exp = r'[Ss]lide_([0-9]+)'
    try:
        return re.search(exp, path).group(1)
    except AttributeError:
        print "Could not determine slide of %s" % path
        return None


def get_rows_from_image(image):
    centroids = [cell.centroid for cell in image.cells]
    regions, hemispheres = zip(*map(lambda cell: analysis.get_region_containing_cell(cell, image), image.cells))
    region_sizes = [(image.region_map == region_id).sum() for region_id in regions]
    means = [cell.image[..., 0].mean() for cell in image.cells]
    image_sizes = [cell.mask.sum() for cell in image.cells]
    percentiles = {
        '{}th percentile'.format(p): [numpy.percentile(cell.image[..., 0], p) for cell in image.cells]
        for p in range(0, 105, 5)
    }

    row_dict = {
        'image': path.basename(image.source_path),
        'condition': get_class(image.source_path),
        'animal': get_animal(image.source_path),
        'slide': get_slide(image.source_path),
        'image_depth': image.depth,
        'centroid': centroids,
        'region': regions,
        'hemisphere': hemispheres,
        'region_size': region_sizes,
        'mean': means,
        'number_of_pixels': image_sizes
    }
    row_dict.update(percentiles)
    return pandas.DataFrame(row_dict)


def get_dataframe_from_image_sequence(im_seq):
    rows = map(get_rows_from_image, im_seq)
    return pandas.concat(rows)


def _concatenate_dicts(d1, d2):
    for key, value in d1.iteritems():
        value += d2[key]

    return d1
