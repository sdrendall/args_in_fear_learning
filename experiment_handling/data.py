import numpy
import conversion, io
from os import path, getcwd
from fisherman import detection


class ImageDescriptor(object):
    
    def __init__(self, 
                 source_path, 
                 region_map,
                 hemisphere_map,
                 depth, 
                 region_map_scale=conversion.atlas_scale, 
                 region_map_offset=(0,0),
                 cells=None):

        self.source_path = source_path
        self.region_map = region_map
        self.hemisphere_map = hemisphere_map
        self.region_map_scale = region_map_scale
        self.region_map_offset = region_map_offset
        self.depth = depth
        self.vsi_resolution = (0, 0)

        if cells is not None:
            self.cells = cells
        else:
            self.cells = list()

    @classmethod
    def from_metadata(cls, 
                      metadata, 
                      region_map_scale=conversion.atlas_scale, 
                      region_map_offset=(0,0), 
                      cells=None, 
                      experiment_path=getcwd(),
                      flip=False,
                      flop=False):
        """
        Instantiate an image from the given metadata dict (from a fishRegistration experiment's metadata.json file)
        """

        region_map = io.load_mhd(path.join(experiment_path, metadata['registeredAtlasLabelsPath']))[0]
        hemisphere_map = io.load_mhd(path.join(experiment_path, metadata['registeredHemisphereLabelsPath']))[0]

        if flip:
            region_map = numpy.flipud(region_map)
            hemisphere_map = numpy.flipud(hemisphere_map)

        if flop:
            region_map = numpy.fliplr(region_map)
            hemisphere_map = numpy.fliplr(hemisphere_map)
        
        return cls(
            source_path=metadata['vsiPath'],
            depth=metadata['atlasCoord'],
            region_map=region_map,
            hemisphere_map=hemisphere_map,
            region_map_scale=region_map_scale,
            region_map_offset=region_map_offset,
            cells=cells
        )

    @property
    def source_path(self):
        """
        Get the path to the source image file
        """
        return self._source_path

    @source_path.setter
    def source_path(self, source_path):
        """
        Set the path to the source image file
        """
        self._source_path = source_path

    @property
    def region_map(self):
        """
        Get the region map for the given image

        The region map is a 2d image that maps onto the original vsi image
         (padding is required, see region_map_scale and region_map_offset)
         the pixel values of the region map correspond to the ids of allen brain atlas regions
        """
        return self._region_map

    @region_map.setter
    def region_map(self, region_map):
        """
        Sets the region map for this image
        """
        self._region_map = region_map

    @property
    def hemisphere_map(self):
        """
        Get the hemisphere map for the given image

        The hemisphere_map is a 2d image that maps onto the vsi image, labelling each hemisphere
        """
        # TODO: Which is right, which is left?
        return self._hemisphere_map

    @hemisphere_map.setter
    def hemisphere_map(self, hemisphere_map):
        self._hemisphere_map = hemisphere_map

    @property
    def region_map_scale(self):
        """
        The scale of pixels in the region map in um
        """
        return self._region_map_scale

    @region_map_scale.setter
    def region_map_scale(self, scale):
        """
        The scale of pixels in the region map in um
        """
        self._region_map_scale = scale

    @property
    def region_map_offset(self):
        """
        The padding that is applied to the original downsampled image so that it it's dimensions are similar to the region map.  This is required to determine corresponding points in the region map and original vsi image.
        """
        return self._region_map_offset

    @region_map_offset.setter
    def region_map_offset(self, offset):
        """
        The padding that is applied to the original downsampled image
        """
        self._region_map_offset = numpy.asarray(offset ,dtype=numpy.uint16)

    # TODO Docs for coordinate system!!
    @property
    def depth(self):
        """
        The depth in the allen brain atlas that the image is located at in physical coordinates in um from the front of the brain
        """
        return self._depth

    @depth.setter
    def depth(self, depth):
        """
        Set the depth that this slice is located at, in physical coordinates
        """
        self._depth = depth

    @property
    def depth_as_index(self):
        """
        The depth in the allen brain atlas that the image is located as an index to the allen brain atlas
        """
        return conversion.physical_to_index(self.depth)

    @depth_as_index.setter
    def depth_as_index(self, index):
        """
        Set the depth that this slice is located at, as an index to the allen brain atlas
        """
        self._depth = conversion.index_to_physical(index)

    @property
    def cells(self):
        """
        Gets the list of cells that are in this image
        """
        return self._cells

    @cells.setter
    def cells(self, cells):
        """
        Specifies a list of cells that are in this image
        """
        if type(cells) is not list:
            self._cells = list(cells)
        else:
            self._cells = cells

    def add_cells(self, cells):
        """
        Adds cells to the current list of cells
        """
        self._cells += list(cells)

    @property
    def vsi_resolution(self):
        """
        Gets the vsi resolution of the corresponding image as a tuple
        """
        return tuple(self._vsi_resolution)

    @vsi_resolution.setter
    def vsi_resolution(self, resolution):
        """
        Sets the vsi resolution of the corresponding image
        """
        self._vsi_resolution = tuple(resolution)


class PhysicalCell(detection.Cell):
    """
    A fisherman.detection.Cell whose centroid is in physical coordinates.

    Has a pixel_scale property that allows conversions from physical cordinates to image indices
    """

    def __init__(self, image, mask, centroid, pixel_scale, **kwargs):
        detection.Cell.__init__(self, image, mask, centroid, **kwargs)
        self.pixel_scale = pixel_scale

    @classmethod
    def from_cell(cls, cell, pixel_scale):
        """
        Constructer that creates physical cells from cells
        """
        return cls(
            image=cell.image,
            mask=cell.mask,
            centroid=(numpy.asarray(cell.centroid) * pixel_scale),
            bounding_box=(cell.bbox),
            pixel_scale=pixel_scale
        )

    def set_pixel_scale(self, scale):
        """
        Sets the physical size of pixels in this cell's images (in um)
        """
        self._pixel_scale = scale

    def get_pixel_scale(self):
        """
        The scale of pixels in this cell's images (in um)
        """
        return self._pixel_scale

    def get_centroid_as_index(self, scale=None, pixel_offset=(0,0)):
        """
        Returns the cell's centroid as an index to an image with pixels of size `scale`

        If scale is not specified, self.pixel_scale is used
        pixel_offset represents the number of pixels the row and column indicies of the centroid should be shifted, once the centroid has been rescaled to an index.  Use this to compensate for padded images.
        """
        if scale is None:
            scale = self.pixel_scale

        pixel_offset = numpy.asarray(pixel_offset, dtype=numpy.int64)

        # Centroids are stored internally as float32 numpy arrays, 
        #  indicies must be ints, so we cast to a uint32 before conversion to tuple
        return tuple(numpy.round(self._centroid/scale + pixel_offset).astype(numpy.uint32))

    # Using the old property interface to stay consistent with the Cell and ImageSlice
    #  classes that this inherits from.
    pixel_scale = property(get_pixel_scale, set_pixel_scale)
