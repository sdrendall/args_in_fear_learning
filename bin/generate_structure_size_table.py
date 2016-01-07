import pandas
import numpy
from os import path
from experiment_handling import io, allen_atlas

class StructureAreaMapper:

    def __init__(self, struct_image, root_node):
        self.area_map = dict()
        self.struct_image = struct_image
        self.populate_structure_area_map(root_node)

    def populate_structure_area_map(self, start_node):
        """
        Populates an empty dict with a mapping of structure ids to 
        """
        if start_node['children']:
            map(self.populate_structure_area_map, start_node['children'])
            self.area_map[start_node['id']] = \
                sum((self.area_map[child['id']] for child in start_node['children'])) + \
                numpy.sum(self.struct_image == start_node['id'])
        else:
            self.area_map[start_node['id']] = numpy.sum(self.struct_image == start_node['id'])


def main():
    from sys import argv
    if len(argv) < 4:
        print "Insufficient Arguments!"
        print "Proper Usage: %s [structure_data_path] [structure_data_mhd] [output_path]" % argv[0]
        return

    structure_data_path, structure_mhd_path, output_path = map(path.expanduser, argv[1:4])
    
    struct_finder = allen_atlas.StructureFinder(structure_data_path)
    struct_image = io.load_mhd(structure_mhd_path)[0]
   
    # The second argment to numpy.split indictes the indicies to split at, so we exclude 0
    area_maps = [StructureAreaMapper(image, struct_finder.structureData).area_map 
        for image in numpy.split(struct_image, range(1, struct_image.shape[0]))]

    structure_size_table = pandas.DataFrame()

    for depth, area_map in enumerate(area_maps):
        regions, region_areas = zip(*area_map.iteritems())
        depths = [depth] * len(regions)
        slice_df = pandas.DataFrame({
            'depth': depths,
            'region': regions,
            'area': region_areas
        })

        structure_size_table = pandas.concat((structure_size_table, slice_df))

    structure_size_table.to_csv(output_path)


main()
