import numpy
from experiment_handling import data, io, allen_atlas, conversion
from argparse import ArgumentParser
from os import path


def get_cell_counts_per_region(image_descriptor):
    """
    Tallies the number of cells in each region in this image.  Outputs a dict of the form {region_id: num_cells}.  Regions with no cells are not included.
    """
    reg_map = image_descriptor.region_map
    cell_counts = dict()

    for cell in image_descriptor.cells:
        region_id = get_region_containing_cell(cell, image_descriptor)
        # Add to region count
        if region_id in cell_counts:
            cell_counts[region_id] += 1
        else:
            cell_counts[region_id] = 1

    return cell_counts


def get_region_containing_cell(cell, image_descriptor, with_hemisphere=True):
    # Get index in region map
    region_map_scale = 25
    region_map_index = cell.get_centroid_as_index(scale=region_map_scale, pixel_offset=image_descriptor.region_map_offset)

    # Get region map key
    try:
        region_id = image_descriptor.region_map[region_map_index]
        if with_hemisphere:
            hemisphere_id = image_descriptor.hemisphere_map[region_map_index]
            return (region_id, hemisphere_id)
        else:
            return region_id

    # Return 0 if out of bounds. 0 corresponds to no region
    except IndexError:
        print "Centroid {} out of image boundries".format(region_map_index)
        if with_hemisphere:
            return (0, 0)
        else:
            return 0


def get_cell_counts_from_image_descriptor_sequence(imd_seq):
    """
    TODO
    """
    cell_counts = map(get_cell_counts_per_region, imd_seq)
    return reduce(_dict_sum, cell_counts)


def point_in_boundries(point, boundries):
    """
    Returns True if the given centroid is within the given boundries
    :param point: A tuple, list, or numpy array in (row, column) format
    :param boundries: A tuple, list, or numpy array in (min_row, min_col, max_row, max_col) format
    """
    point = numpy.asarray(point)
    top_left, bottom_right = map(numpy.asarray, (boundries[:2], boundries[2:]))
    return numpy.all(point > top_left) and numpy.all(point < bottom_right)


def _dict_sum(d1, d2):
    """
    Returns a dict with an elementwise sum of the items in d1 and d2.
    """
    d1_keys = set(d1.iterkeys())
    d2_keys = set(d2.iterkeys())
    return {key: d1.get(key, 0) + d2.get(key, 0) for key in d1_keys.union(d2_keys)}
