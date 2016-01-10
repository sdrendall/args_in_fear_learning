import numpy
import cPickle as pickle
import lmdb
import caffe
import fnmatch
import bioformats
import javabridge
from skimage import io, color
from bioformats import log4j
from fisherman import detection, math
from os import path, walk


def main():
    from sys import argv
    if len(argv) < 3:
        print "Insufficient Arguments!"
        print "Proper Usage: %s [vsi_images] [caffe_model]"
        return

    vsi_paths = get_matching_files(path.expanduser(argv[1]))
    model_path = path.expanduser(argv[2])
    net_path = path.expanduser('/groups/gray/image_processing/build/fisherman/caffe/fish_net_conv_deploy.prototxt')

    fish_net = caffe.Net(net_path, model_path, caffe.TEST)

    chunker_params = {
        'chunk_size': 954,
        'stride': 6,
        'window_size': 49,
        'num_classes': 2
    }

    detector = detection.CellDetector(
        net=fish_net,
        chunker_params=chunker_params,
        signal_channel=0,
        cell_radius=12
    )
    
    detector.set_compute_mask_on_signal_plane_only(True)
    detector.set_mode_cpu()

    javabridge.start_vm(class_path=bioformats.JARS)
    log4j.basic_config()

    for vsi_path in vsi_paths:
        print "Loading %s ....." % vsi_path
        reader = bioformats.ImageReader(vsi_path)
        cfos = reader.read(c=1, rescale=False)
        #dapi = reader.read(c=0, rescale=True).astype(numpy.uint8)

        print "vsi data type:", cfos.dtype;

        #image = numpy.dstack([cfos, dapi])
        image = cfos

        detector.set_image(image)

        raw_mask = detector.get_fish_net_mask(cleaned=False, scaled=False)
        cell_mask = detector.get_fish_net_mask(cleaned=True, scaled=True)
        io.imsave('/home/sam/Desktop/raw_mask_out.png', raw_mask)
        io.imsave('/home/sam/Desktop/clean_mask_out.png', cell_mask)
        del raw_mask

        cell_mask = detector.separate_cell_mask(cell_mask)

        image = crop_output(math.median_normalize(image) * 25)
        cell_mask = crop_output(cell_mask)

        output_base, _ = path.splitext(vsi_path)

        print "Saving image ....."

        for i in range(1,6):
            output_path = output_base + '_mask_out_%dx.png' % i
            io.imsave(output_path, color.label2rgb(cell_mask[..., 0], image=image.astype(numpy.uint8)*i, bg_label=0, alpha=0.15))
            io.imsave(output_base + '_no_labels_%dx.png' % i, image.astype(numpy.uint8)*i)

    javabridge.kill_vm()


def get_matching_files(expr):
    start, file_expr = path.split(expr)
    paths = list()
    for root, _, filenames in walk(start):
        for filename in fnmatch.filter(filenames, file_expr):
            paths.append(path.join(root, filename))

    return paths


def crop_output(image):
    return image[7256:9012, 7967:11407]


main()
