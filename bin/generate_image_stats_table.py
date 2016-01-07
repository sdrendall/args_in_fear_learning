import pandas
import numpy
from os import path
from experiment_handling import io, allen_atlas, dataframes


class StructureAreaMapper:

    def __init__(self, struct_image, root_node):
        self.area_map = dict()
        self.struct_image = struct_image
        self.populate_structure_area_map(root_node)

    def populate_structure_area_map(self, start_node):
        """
        Populates an empty dict with a mapping of structure ids to the area of those structures
            in the self.struct_image
        """
        if start_node['children']:
            map(self.populate_structure_area_map, start_node['children'])

            # We only care about the finest grain structures in this case
            # self.area_map[start_node['id']] = \
            #   sum((self.area_map[child['id']] for child in start_node['children']))
        else:
            self.area_map[start_node['id']] = numpy.sum(self.struct_image == start_node['id'])


def main():
    from sys import argv
    if len(argv) < 4:
        print "Insufficient Arguments!"
        print "Proper Usage: %s [experiment_path] [structure_data_path] [output_path]" % argv[0]
        return

    experiment_path, structure_data_path, output_path = map(path.expanduser, argv[1:4])

    struct_finder = allen_atlas.StructureFinder(structure_data_path)
    meta_man = io.MetadataManager(experiment_path)
    
    image_stats_table = pandas.DataFrame()

    for entry in meta_man.metadata:
        print "Importing data from %s ..." % entry['vsiPath']
        try:
            region_map = io.load_mhd(path.join(experiment_path, entry['registeredAtlasLabelsPath']))[0]
            hemisphere_map = io.load_mhd(path.join(experiment_path, entry['registeredHemisphereLabelsPath']))[0]
        except:
            print "Could not load registration results for %s.  Registration probably failed" % entry['vsiPath']
            continue

        for hemisphere in (1, 2):
            lateral_region_map = region_map * (hemisphere_map == hemisphere)
            lateral_area_map = StructureAreaMapper(lateral_region_map, struct_finder.structureData).area_map
            regions, region_areas = zip(*lateral_area_map.iteritems())

            image_names = [path.basename(entry['vsiPath'])] * len(regions)
            animals = [dataframes.get_animal(entry['vsiPath'])] * len(regions)
            slides = [dataframes.get_slide(entry['vsiPath'])] * len(regions)
            conditions = [dataframes.get_class(entry['vsiPath'])] * len(regions)
            hemispheres = [hemisphere] * len(regions)

            depths = [entry.get('atlasIndex', None)] * len(regions)
            usabilities = [entry.get('sliceUsable', None)] * len(regions)

            disqualifications = [(region, hemisphere) in entry.get('regionIdsToExclude', []) 
                                    for region in regions]

            update_df = pandas.DataFrame({
                'image': image_names,
                'animal': animals,
                'slide': slides,
                'condition': conditions,
                'depth': depths,
                'slice_usable': usabilities,
                'disquaified': disqualifications,
                'region': regions,
                'hemisphere': hemispheres,
                'area': region_areas
            })

            image_stats_table = pandas.concat((image_stats_table, update_df))

    
    image_stats_table.to_csv(output_path)


main()
