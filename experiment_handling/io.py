import json
import os
import numpy
import lmdb
import hashlib
from warnings import warn
try:
    import cPickle as pickle
except ImportError:
    import pickle


class ImageDbManager(object):
    """
    Manages an database used to store metadata about images in an experiment, including cells that are found using fisherman.
    """
    
    def __init__(self, db_path, readonly=True, map_size=10**12, **kwargs):
        # Open the database
        self._db = lmdb.open(db_path, readonly=readonly, map_size=map_size, **kwargs)

    def add_image(self, image):
        """
        Add an image to the database, this will overwrite any existing image with the same source path
        """
        key = hashlib.sha256(image.source_path).hexdigest()
        data = pickle.dumps(image)
        with self._db.begin(write=True) as txn:
            txn.put(key, data)

    def add_image_sequence(self, image_seq):
        """
        Adds a sequence of images to the database in a single transaction
        """
        keys, data = zip(*[(hashlib.sha256(img.source_path).hexdigest(), pickle.dumps(img)) for img in image_seq])
        with self._db.begin(write=True) as txn:
            map(txn.put, keys, data)

    def get_image(self, source_path):
        """
        Get data for the image with the given source_path
        
        Returns None if the specified image could not be found
        """
        key = hashlib.sha256(source_path).hexdigest()
        with self._db.begin() as txn:
            image_data = txn.get(key, default=None)

        return pickle.loads(image_data)

    def get_image_iter(self):
        """
        Returns an iterator that returns images from the database.

        This opens a database transaction for the duration of the iterator 
            (i.e. until all images have been exhausted)
        """
        with self._db.begin() as txn:
            for _, data in txn.cursor():
                yield pickle.loads(data)


class MetadataManager():
    """
    A class to manage the metadata.json file used in the image registration pipeling

    I handle loading, and updating the data in metadata.json
    """

    metadata = None

    def __init__(self, experiment_path=os.getcwd()):
        self.experimentPath = experiment_path
        self.metadataPath = self.generate_metadata_path(experiment_path)
        self.load_metadata()

    def load_metadata(self):
        """
        Loads the metadata from metadata.json and stores it at self.json
        :return: Pointer to self.metadata
        """
        json_file = open(self.metadataPath, 'r')
        self.metadata = json.load(json_file)
        json_file.close()
        return self.metadata

    def update_metadata(self):
        """
        Updates the data stored at metadata.json with the data in self.metadata
        :return: zilch
        """
        json_file = open(self.metadataPath, 'w')
        json.dump(self.metadata, json_file, sort_keys=True, indent=4)
        json_file.close()

    def ensure_metadata_directory(self):
        """
        Creates self.experimentPath/.registrationData if it doesn't exist
        :return: nope
        """
        dir_path = os.path.join(self.experimentPath, '.registrationData')
        _ensure_dir(dir_path)

    @staticmethod
    def generate_metadata_path(experiment_path):
        """
        Generates the path the the metadata.json file
        :param experiment_path: root path for the experiment data.  Must contain the .registrationData directory
        :return: a string containing the path to the .metadata.json file: 'experimentPath/.registrationData.metadata.json'
        """
        return os.path.join(experiment_path, '.registrationData', 'metadata.json')

    def get_entry_by_attribute(self, attribute, value):
        """
        Searches self.metadata for the entry where entry[attribute] == value

        retuns None if no entry is found
        """
        for entry in self.metadata:
            try:
                if entry[attribute] == value:
                    return entry
            except KeyError:
                pass

        return None

    def get_entry_from_name(self, name):
        """
        Searches self.metadata for the entry where name in entry['vsiPath']

        retuns None if no entry is found
        """
        for entry in self.metadata:
            if name in entry['vsiPath']:
                return entry

        print "No Entry Found for image %s" % name
        return None



def _ensure_dir(dir_path):
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
    elif not os.path.isdir(dir_path):
        print "Warning! Non-directory file exists at:\n\t%s" % dir_path


## MHD FUNCTIONS

data_type_key = {
    'MET_CHAR': numpy.byte,
    'MET_UCHAR': numpy.ubyte,
    'MET_SHORT': numpy.short,
    'MET_USHORT': numpy.ushort,
    'MET_INT': numpy.intc,
    'MET_UINT': numpy.uintc,
    'MET_FLOAT': numpy.single,
    'MET_DOUBLE': numpy.double,
    numpy.byte: 'MET_CHAR',
    numpy.ubyte: 'MET_UCHAR',
    numpy.short: 'MET_SHORT',
    numpy.ushort: 'MET_USHORT',
    numpy.intc: 'MET_INT',
    numpy.uintc: 'MET_UINT',
    numpy.single: 'MET_FLOAT',
    numpy.double: 'MET_DOUBLE'}

# The order for these is important
accepted_tags = ('ObjectType','NDims','BinaryData','BinaryDataByteOrderMSB','CompressedData','CompressedDataSize',
                 'TransformMatrix','Offset','CenterOfRotation','AnatomicalOrientation','ElementSpacing','DimSize',
                 'ElementType','ElementDataFile','Comment','SeriesDescription','AcquisitionDate','AcquisitionTime',
                 'StudyDate','StudyTime')


def load_mhd_header(file_path):
    """ Return a dictionary of meta data from meta header file """
    header_file = open(file_path, "r")

    meta_dict = {}
    for line in header_file:
        tag, value = line.split(' = ')
        if tag in accepted_tags:
            meta_dict[tag.strip()] = value.strip()
        else:
            warn('Encountered unexpected tag: ' + tag)
    header_file.close()

    return meta_dict


def load_mhd(file_path):
    """
    Loads an mhd file at file_path.

    Returns a tuple: (image_data, meta_dict)
        containing a numpy array with the image data, and a dict
        containing the meta information in the mhd file
    """
    meta_dict = load_mhd_header(file_path)
    data_dimensions = map(int, meta_dict['DimSize'].split())

    image_dir = os.path.dirname(file_path)
    data_filepath = os.path.join(image_dir, meta_dict['ElementDataFile'])
    data_type = data_type_key[meta_dict['ElementType'].upper()]

    image_data = numpy.fromfile(data_filepath, dtype=data_type)
    image_data = numpy.reshape(image_data, data_dimensions, order='F')

    return image_data, meta_dict


def write_meta_header(file_path, meta_dict):
    header = ''
    # Tag order matters here so I can't just iterate through meta_dict.keys()
    for tag in accepted_tags:
        if tag in meta_dict.keys():
            header += '%s = %s\n'%(tag,meta_dict[tag])

    f = open(file_path,'w')
    f.write(header)
    f.close()


def dump_raw_data(file_path, data):
    """ Write the data into a raw format file. Big endian is always used. """
    # TODO: THIS
    rawfile = open(file_path,'wb')
    a = array.array('f')
    for o in data:
        a.fromlist(list(o))
    #if is_little_endian():
    #    a.byteswap()
    a.tofile(rawfile)
    rawfile.close()


def write_mhd(output_path, image_data, **kwargs):
     metadata = {'ObjectType': 'Image',
                 'BinaryData': 'True',
                 'BinaryDataByteOrderMSB': 'False',
                 'ElementType': data_type_key[image_data.dtype],
                 'NDims': str(image_data.ndim),
                 'DimSize': ' '.join(image_data.shape),
                 'ElementDataFile': os.path.basename(output_path).replace('.mhd','.raw')}

     write_meta_header(output_path, metadata)
     output_dir = os.path.dirname((output_path))
     data_filepath = os.path.join(output_dir, metadata['ElementDataFile'])
     dump_raw_data(data_filepath, image_data)


