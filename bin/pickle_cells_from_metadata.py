#! /usr/bin/env python

import numpy
import caffe
import json
import cPickle as pickle
import javabridge
import bioformats
from bioformats import log4j
from experiment_handling import io, data, conversion
from fisherman import detection
from argparse import ArgumentParser
from os import path, getcwd
from itertools import izip
from skimage import io

FISHERMAN_ROOT = path.expanduser('/groups/gray/image_processing/build/fisherman')
VSI_PIXEL_SCALE = .64497 # in um/pixel

def configure_parser():
    parser = ArgumentParser(description='Detects cells in vsi images in an experiment')
    parser.add_argument('output_path', help='Path to save the pickled output file')
    parser.add_argument('-i', '--input_metadata', 
                        help='The path to the vsi file to be processed.')
    parser.add_argument('-e', '--experiment_path', default=getcwd(),
                        help='The root directory containing the data to be processed.'
                             '  Defaults to the current directory.')
    parser.add_argument('-m', '--model_path', 
                        default=path.join(FISHERMAN_ROOT, 'models/median_normalized/fish_net_conv_deploy_weights.caffemodel'),
                        help='Path to the caffemodel to be used for cell detection'
                             'Default: $FISHERMAN/models/median_normalized/fish_net_conv_deploy_weights.caffemodel')
    parser.add_argument('-n', '--net_path',
                        default=path.join(FISHERMAN_ROOT, 'caffe/fish_net_conv_deploy.prototxt'),
                        help='Path to the net prototxt file to use for cell detection'
                             'Default: $FISHERMAN/caffe/fish_net_conv_deploy.prototxt')
    parser.add_argument('-c', '--chunk_size', default=1800, type=int,
                        help='The width of chunks to split input vsis into. '
                        'This value should be as large as possible before memory issues are encounted. '
                        'Chunks are square so the height will equal the width. Default = 1800')
    
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
        dapi = reader.read(c=0, rescale=False).astype(numpy.uint16)
        cfos = reader.read(c=1, rescale=False).astype(numpy.uint16)

    return numpy.dstack((cfos, dapi))


def compute_offset(vsi_shape, map_shape=numpy.asarray((320, 456), dtype=numpy.int32)):
    atlas_scale = VSI_PIXEL_SCALE/conversion.atlas_scale
    offset = numpy.ceil((map_shape - vsi_shape*atlas_scale) * .5).astype(numpy.int32)
    offset[offset < 0] = 0
    return offset.astype(numpy.uint16)


def filter_duplicates(cells, prev_end_row, prev_end_col):
    """
    Since we are detecting cells in chunks, this will filter cells out that occur in 
     regions that have already been detected. The conditions for inclusion depend on the
     fact that the image_chunker iterates over columns, and then rows
    """
    return (cell for cell in cells if cell.centroid[0] > prev_end_row or 
        (cell.centroid[0] < prev_end_row and cell.centroid[1] > prev_end_col))


def shift_cells(cells, offset_row, offset_col):
    for cell in cells:
        bbox = numpy.asarray(cell.bbox, dtype=numpy.float32)
        cell.bbox = bbox + numpy.asarray((offset_row, offset_col, offset_row, offset_col), dtype=numpy.float32)

        centroid = numpy.asarray(cell.centroid, dtype=numpy.float32)
        cell.centroid = centroid + numpy.asarray((offset_row, offset_col), dtype=numpy.float32)

    return cells


def main():
    # Parse command line input
    parser = configure_parser()
    args = parser.parse_args()

    metadata = json.loads(args.input_metadata)
    experiment_path = path.expanduser(args.experiment_path)
    vsi_path = path.join(experiment_path, metadata['vsiPath'])

    net_path = path.expanduser(args.net_path)
    model_path = path.expanduser(args.model_path)
    output_path = path.expanduser(args.output_path)

    # Configure fish_net.  This will be done internally when CellDetectors are initialized at some point....
    fish_net = caffe.Net(net_path, model_path, caffe.TEST)

    # Configure a cell detector
    # The cell_radius is important for processing the output of fish_net (ex. separating nearby cells)
    # The signal_channel specifies the channel in the input image that contains the relevant signal (i.e. the ISH stain)
    detector_chunker_params = {
        'chunk_size': args.chunk_size,
        'stride': 6,
        'window_size': 49,
        'num_classes': 2
    }

    vsi_chunker_params = {
        'chunk_size': args.chunk_size,
        'stride': 6,
        'window_size': 43,
        'num_classes': 1
    }

    cell_detector = detection.CellDetector(net=fish_net, cell_radius=12, signal_channel=0, chunker_params=detector_chunker_params)
    cell_detector.set_mode_cpu()

    # Configure and start the JVM for loading vsi images with bioformats
    javabridge.start_vm(class_path=bioformats.JARS)
    log4j.basic_config()

    image_descriptor = data.ImageDescriptor.from_metadata(metadata, experiment_path=experiment_path)
    vsi_image = load_vsi(vsi_path)
    javabridge.kill_vm() # Caffe will segfault if the jvm is running...

    vsi_chunker = detection.ImageChunkerWithOutput(vsi_image.transpose(2,0,1), **vsi_chunker_params)
    vsi_chunker.allocate_output()

    prev_end_row = prev_end_col = -1
    for chunk, _ in vsi_chunker:
        cell_detector.set_image(chunk.transpose(1,2,0))
        detected_cells = cell_detector.detect_cells()
        start_row, start_col = vsi_chunker.current_chunk_bounds[:2]

        detected_cells = shift_cells(detected_cells, start_row, start_col)
        detected_cells = filter_duplicates(detected_cells, prev_end_row, prev_end_col)

        physical_cells = map(lambda cell: data.PhysicalCell.from_cell(cell, VSI_PIXEL_SCALE), detected_cells)
        print "Adding %d cells to descriptor" % len(physical_cells)
        image_descriptor.cells += physical_cells

        prev_end_row, prev_end_col = vsi_chunker.current_chunk_bounds[2:]


    # Compute and set the offset of the region map
    vsi_resolution = numpy.asarray(vsi_image.shape[:2], dtype=numpy.int32)
    image_descriptor.vsi_resolution = vsi_resolution
    image_descriptor.region_map_offset = compute_offset(
        vsi_resolution,
        map_shape=image_descriptor.region_map.shape
    )

    # pickle the image descriptor
    output_file = open(output_path, 'w')
    pickle.dump(image_descriptor, output_file)
    output_file.close()

if __name__ == '__main__':
    main()
