import numpy
import pandas
from os import path
from experiment_handling import io, allen_atlas
from itertools import imap

def main():
    from sys import argv
    if len(argv) < 3:
        print "Insufficient Arguments!"
        print "Proper Usage: %s [structure_data_path] [output_csv_path]" % argv[0]
        return

    structure_data_path, output_path = map(path.expanduser, argv[1:])

    struct_finder = allen_atlas.StructureFinder(structure_data_path)
    output_file = open(output_path, 'w')

    all_structures = struct_finder.get_all_structures_as_list()

    structure_rows = {key: [structure[key] for structure in all_structures] 
        for key in all_structures[0].keys() if key != 'atlas_id'} # atlas_id is confusing and useless

    structure_parents = (struct_finder.get_parents_by_attribute('id', id_no) for id_no in structure_rows['id'])
    parent_acronyms = ((parent['acronym'] for parent in parents) for parents in structure_parents)
    child_acronyms = ((child['acronym'] for child in children) for children in structure_rows.pop('children'))

    delim = '\t'
    structure_rows['parent_acronyms'] = map(delim.join, parent_acronyms)
    structure_rows['child_acronyms'] = map(delim.join, child_acronyms)

    df = pandas.DataFrame(structure_rows)
    df.to_csv(output_file)


main()
