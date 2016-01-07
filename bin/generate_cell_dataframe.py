from experiment_handling import dataframes, io
from os import path

def main():
    from sys import argv
    if len(argv) < 3:
        print "Insufficient Arguments!"
        print "Proper Usage: %s [image_db_path] [output_csv_path]"
        return

    db_path, csv_path = map(path.expanduser, argv[1:3])
    
    db_man = io.ImageDbManager(db_path)
    df = dataframes.get_dataframe_from_image_sequence(db_man.get_image_iter())
    df.to_csv(csv_path)

main()
