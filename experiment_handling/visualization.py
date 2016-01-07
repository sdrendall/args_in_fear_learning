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
