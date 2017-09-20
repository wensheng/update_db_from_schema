#!/usr/bin/env python

import os
import shutil
import argparse
from pkg_resources import Requirement, resource_filename

import db_from_schema_yaml

desc = """yml2db:
Update database schema with an YAML file
"""

def main():
    argp = argparse.ArgumentParser(description=desc)
    argp.add_argument('-f', '--force',
                      action='store_true',
                      default=False,
                      help="write to database, without this database will not be changed")
    argp.add_argument('-s', '--schema',
                      action='store',
                      default="schema.yml",
                      help="specify a schemal YAML file, default is `schema.yml`")
    argp.add_argument('-e', '--example',
                      action='store_true',
                      default=False,
                      help="create a db_config.ini sample file")
    args = argp.parse_args()

    if args.example:
        sample_config = resource_filename(Requirement.parse("yml2db"),
                                          "yml2db/db_config.ini.sample")
        shutil.copy(sample_config, "./")
        exit()

    if not os.path.isfile("db_config.ini"):
        exit("No db_config.ini found, use -e to create an example")

    db_from_schema_yaml.update_db(args)


if "__main__" == __name__:
    main()
