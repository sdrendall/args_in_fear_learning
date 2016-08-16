#! /usr/bin/env python

import numpy
import caffe
import json
import javabridge
import bioformats
from bioformats import log4j
from experiment_handling import data, conversion, dataframes
from fisherman import detection, math
from argparse import ArgumentParser
from skimage import io, measure
from os import path, getcwd

VSI_PIXEL_SCALE = .64497 # in um/pixel

def configure_parser():
    parser = ArgumentParser(description='Summarize a set of labelled images in a dataframe.')
    parser.add_argument('label_dir', help='Path to the directory containing label files')
    parser.add_argument('output_path', help='Path where the output dataframe should be saved.')
    parser.add_argument('-e', '--experiment_path', default=getcwd(),
                        help='Path to the vsi experiment root')
    parser.add_argument('--flip', help='Corrects for vertically flipped vsi images')
    parser.add_argument('--flop', help='Corrects for horizontally flipped vsi images')

    return parser


def load_vsi(vsi_path):
    with bioformats.ImageReader(vsi_path) as reader:
        cfos = reader.read(c=1, rescale=False).astype(numpy.uint16)

    return cfos


def compute_offset(vsi_shape, map_shape=numpy.asarray((320, 456), dtype=numpy.int32)):
    vsi_shape = numpy.asarray(vsi_shape, dtype=numpy.int32)
    map_shape = numpy.asarray(map_shape, dtype=numpy.int32)
    atlas_scale = VSI_PIXEL_SCALE/conversion.atlas_scale
    offset = numpy.ceil((map_shape - vsi_shape*atlas_scale) * .5).astype(numpy.int32)
    offset[offset < 0] = 0
    return offset.astype(numpy.uint16)


def get_label_path(vsi_path, args):
    label_name = path.splitext(path.basename(vsi_path))[0] + '_fish_labels.tif'
    return path.join(args.label_dir, label_name)


def get_image_descriptor(entry, args):
    label_path = get_label_path(entry['vsi_path'], args)
    label_image = io.imread(label_path)
    vsi_image = load_vsi(path.join(args.experiment_path, entry['vsi_path']))

    vsi_res = numpy.asarray(vsi_image.shape[:2], dtype=numpy.int32)
    lab_res = numpy.asarray(label_image.shape[:2], dtype=numpy.int32)
    window_correction = (vsi_res - lab_res) // 2

    # The offset produced by the convolution window needs to be accounted for
    corrected_view = vsi_image[window_correction[0]:, window_correction[1]:, ...]

    cells = [
        Cell(
            image=math.crop_from_bounding_box(props.bbox, corrected_view),
            mask=props.image,
            centroid=props.centroid,
            bounding_box=props.bbox
        ) for props in measure.regionprops(label_image)
    ]

    image_descriptor = data.ImageDescriptor.from_metadata(
        entry,
        experiment_path=args.experiment_path,
        cells=cells,
        flip=args.flip,
        flop=args.flop
    )

    image_descriptor.vsi_resolution = vsi_res
    image_descriptor.region_map_offset = offset = compute_offset(
        image_descriptor.vsi_resolution,
        map_shape=image_descriptor.region_map.shape
    )
    
    return image_descriptor


def main():
    parser = configure_parser()
    args = parser.parse_args()

    metadata_path = path.join(args.experiment_path, '.registrationData', 'metadata.json')
    metadata = json.load(open(metadata_path))

    javabridge.start_vm(class_path=bioformats.JARS)
    log4j.basic_config()

    image_descriptors = (get_image_descriptor(entry, args) for entry in metadata)
    df = dataframes.get_dataframe_from_image_sequence(image_descriptors)
    df.to_csv(args.output_path)

    javabridge.kill_vm()
