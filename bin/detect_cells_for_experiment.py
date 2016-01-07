import numpy
import caffe
import javabridge
import bioformats
from bioformats import log4j
from experiment_handling import io, data
from fisherman import detection
from argparse import ArgumentParser
from os import path, getcwd

FISHERMAN_ROOT = path.expanduser('/groups/gray/image_processing/build/fisherman')
VSI_PIXEL_SCALE = .64497 # in um

def configure_parser():
    parser = ArgumentParser(description='Detects cells in vsi images in an experiment')
    parser.add_argument('output_db_path', default=path.join(getcwd(), 'image_db'),
                        help='Path to save the database containing the output')
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
    parser.add_argument('-c', '--chunk_size', default=1000,
                        help='The width of chunks to split input vsis into. '
                        'This value should be as large as possible before memory issues are encounted. '
                        'Chunks are square so the height will equal the width. Default = 1000')
    
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

def compute_offset(vsi_shape):
    map_shape = numpy.asarray((320, 456), dtype=numpy.int32)
    atlas_scale = .64497/25.0
    offset = numpy.ceil((map_shape - vsi_shape*atlas_scale) * .5).astype(numpy.int32)
    offset[offset < 0] = 0
    return offset.astype(numpy.uint16)

def filter_duplicates(cells, chunk_row, chunk_col, chunk_size):
    chunk_boundries = numpy.asarray((chunk_row, chunk_col)) * chunk_size
    return (cell for cell in cells if cell.centroid[0] > chunk_boundries[0] and cell.centroid[1] > chunk_boundries[1])
    

def main():
    # Parse command line input
    parser = configure_parser()
    args = parser.parse_args()

    experiment_path = path.expanduser(args.experiment_path)
    net_path = path.expanduser(args.net_path)
    model_path = path.expanduser(args.model_path)

    # Configure io managers for the output database and for the metadata
    db_manager = io.ImageDbManager(args.output_db_path, readonly=False)
    metadata_manager = io.MetadataManager(experiment_path=args.experiment_path)

    # Configure fish_net.  This will be done internally when CellDetectors are initialized at some point....
    fish_net = caffe.Net(net_path, model_path, caffe.TEST)

    # Configure a cell detector
    # The cell_radius is important for processing the output of fish_net (ex. separating nearby cells)
    # The signal_channel specifies the channel in the input image that contains the relevant signal (i.e. the ISH stain)
    cell_detector = detection.CellDetector(net=fish_net, cell_radius=12, signal_channel=0)

    # Configure and start the JVM for loading vsi images with bioformats
    javabridge.start_vm(class_path=bioformats.JARS)
    log4j.basic_config()

    metadata = metadata_manager.load_metadata()

    for i, image_metadata in enumerate(metadata):
        print "Analyzing image %d of %d" % (i, len(metadata))
        try:
            # Load an image descriptor using an images metadata.  
            # The experiment path is necessary to locate files that are mentioned in the metadata
            image_descriptor = data.ImageDescriptor.from_metadata(image_metadata, experiment_path=args.experiment_path)

            # Load the vsi image that the metadata references, and pass it to the cell_detector
            vsi_path = path.join(args.experiment_path, image_metadata['vsiPath'])
            vsi_image = load_vsi(vsi_path)
            vsi_chunker = detection.ImageChunker(vsi_image.transpose(2,0,1), chunk_size=args.chunk_size)


            for chunk in vsi_chunker:
                cell_detector.set_image(chunk.transpose(1,2,0))
                detected_cells = filter_duplicates(cell_detector.detect_cells(), vsi_chunker.current_chunk_row, vsi_chunker.current_chunk_col, args.chunk_size)
                image_descriptor.cells += map(lambda cell: data.PhysicalCell.from_cell(cell, VSI_PIXEL_SCALE), detected_cells)

            # Compute and set the offset of the region map
            vsi_resolution = numpy.asarray(vsi_image.shape[:1], dtype=numpy.int32)
            image_descriptor.region_map_offset = compute_offset(vsi_resolution)

            # Send the image descriptor to the database
            db_manager.add_image(image_descriptor)
        except:
            print "Cell detection failed for %s" % image_metadata['vsiPath']

if __name__ == '__main__':
    main()
