import pandas
from experiment_handling import allen_atlas
from os import path

def main():
    from sys import argv
    if len(argv) < 3:
        print "Insufficient Arguments!"
        print "Proper Usage: %s [csv_path] [structure_data_path]" % argv[0]
        return

    csv_path, structure_data_path = map(path.expanduser, argv[1:3])

    df = pandas.read_csv(csv_path)
    struct_finder = allen_atlas.StructureFinder(structure_data_path)

    df['region_names'] = map(struct_finder.get_name_from_id, df['region'])
    
    df.to_csv(csv_path)

main()
