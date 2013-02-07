#!/usr/bin/python

import argparse
import datetime
import operator
import os
import shutil
import subprocess
import sys


def main(argv):
    (destination_dir, search_paths, dry_run) = process_args(argv)
    print (destination_dir, search_paths, dry_run)

    jpeg_infos = build_jpeg_infos(search_paths)
    sorted_jpeg_infos = sort_by_name_and_date(jpeg_infos)
    (files_to_move_infos, duplicate_jpeg_infos) = \
        remove_duplicates(sorted_jpeg_infos,
	                  idfn=operator.attrgetter('name', 'date_taken'))
    print "Move:"
    print "\n".join(["%s" % ji for ji in files_to_move_infos])
    print "Duplicates:"
    print "\n".join(["%s" % ji for ji in duplicate_jpeg_infos])

    if dry_run:
        return

    create_destination_dirs_and_move_files(destination_dir,
                                           files_to_move_infos)


def _find_or_make_directories_for_date(destination_dir, date):
    if date is None:
        dirnames = ['Undated']
    else:
        dirnames = [date.strftime("%Y"), date.strftime("%m")]
    dir_path_for_date = os.path.join(destination_dir, *dirnames)
    if not os.path.isdir(dir_path_for_date):
        os.makedirs(dir_path_for_date)
    return dir_path_for_date


def create_destination_dirs_and_move_files(destination_dir, files_to_move_infos):
    # Create the destination dir if it doesn't already exist
    if not os.path.exists(destination_dir):
        os.mkdir(destination_dir)
    if not os.path.isdir(destination_dir):
        raise Exception("Directory %s could not be created" % destination_dir)

    # For each file, create a directory if necessary and move the photo
    # if there is not already a file of the same name there
    for info in files_to_move_infos:
        dirpath_for_date = _find_or_make_directories_for_date(destination_dir,
                                                              info.date_taken)
        destination_path = os.path.join(dirpath_for_date, info.name)
        if os.path.exists(destination_path):
            raise Exception("Could not move %s to %s. Destination file already exists" % (info.name, destination_path))
        shutil.copy(info.full_path, destination_path)
        


def remove_duplicates(seq, idfn):
    seen = {}
    unique = []
    duplicates = []
    for item in seq:
        marker = idfn(item)
        if marker in seen:
	    duplicates.append(item)
	else:
	    unique.append(item)
        seen[marker] = 1
    return (unique, duplicates)

def sort_by_name_and_date(jpeg_infos):
    return sorted(jpeg_infos, key=operator.attrgetter('name', 'date_taken'))

EXIF_EXE = 'exif'

def _get_date_taken_from_exif(full_path):
    """
    Read JPEG EXIF data from the given file and return a datetime date
    representing the time the image was created.  If no date and time can
    be found, return None
    """
    # Open file with exif executable with appropriate arguments
    # and capture output
    args = ["-t", "Date and Time (Original)",
            "-m",
	    full_path]

    # Grab the date from the captured output
    try:
        exif_output = subprocess.check_output([EXIF_EXE] + args)
        return datetime.datetime.strptime(exif_output.strip(), "%Y:%m:%d %H:%M:%S")
    except subprocess.CalledProcessError:
        return None


class JPEGInfo():
    def __init__(self, name, full_path):
        self.name = name
        self.full_path = full_path
	self.date_taken = _get_date_taken_from_exif(full_path)

    def __repr__(self):
        return "%s taken %s" % (self.name, self.date_taken)


def build_jpeg_infos(search_paths):
    """
    Return a list of objects each holding information about a JPEG file.
    """
    jpeg_infos = []
    for search_path in search_paths:
        for (dirpath, dirnames, filenames) in os.walk(search_path):
            def is_jpeg(filename):
                return filename.endswith('.JPG') or filename.endswith('.jpg')
            jpeg_filenames = filter(is_jpeg, filenames)
	    abs_dirpath = os.path.abspath(dirpath)
	    jpeg_full_paths = [os.path.join(abs_dirpath, f) for 
	                       f in jpeg_filenames]
            for name, path in zip(jpeg_filenames, jpeg_full_paths):
                jpeg_infos.append(JPEGInfo(name=name, full_path=path))

    return jpeg_infos


def process_args(argv):
    parser = argparse.ArgumentParser(
        description='Organise Jpeg photos with exif data')
    parser.add_argument('--destination', type=str,
                        help='Directory (to create) to move photos to',
                        action='store',
                        required=True)
    parser.add_argument('--source', type=str,
                        help='Directory to search for JPEGs',
                        action='append',
                        required=True)
    parser.add_argument('--dryrun',
                        help='Report what will be done without doing anything',
                        action='store_true')

    args = parser.parse_args()
    return (args.destination, args.source, args.dryrun)


if __name__ == '__main__':
    main(sys.argv[:])

