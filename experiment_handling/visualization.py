import numpy
from skimage.color import label2rgb
from experiment_handling import analysis
from fisherman import math


def overlay_cells_on_image(image, boundries, cells, offset=(0,0)):
    """
    
    """
    mask = numpy.zeros(image.shape[:2])
    boundries -= numpy.asarray(tuple(offset) * 2)
    label = 1
    for cell in filter_cells_by_boundry(cells, boundries):
        math.modify_with_bounding_box(cell.bbox, mask, cell.mask.astype(numpy.uint16)*label)
        label += 1

    return label2rgb(mask, image=image, bg_label=0)
    

def filter_cells_by_boundry(cells, boundries):
    return (cell for cell in cells if (cell._bbox[:2] >= numpy.asarray(boundries[:2]).all()
                and cell._bbox[2:] <= numpy.asarray(boundries[2:]).all()))

def create_cell_mask_from_descriptor(descriptor):
    num_rows = descriptor.region_map_offset[0]*2 + descriptor.region_map.shape[2] - 1
    num_rows *= descriptor.region_map_scale

    num_cols = descriptor.region_map_offset[1]*2 + descriptor.region_map.shape[0] - 1
    num_cols *= descriptor.region_map_scale

    mask = numpy.zeros((num_rows, num_cols))

    for cell in descriptor.cells:
        first_row, first_col, last_row, last_col = cell.bbox
        mask[first_row:last_row, first_col:last_col] = cell.get_mask()[...]

    return mask
