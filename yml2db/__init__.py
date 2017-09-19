import sys
import os.path

cur_dir = os.path.realpath(os.path.dirname(__file__))
sys.path.insert(0, cur_dir)

import yml2db_main
def main():
    yml2db_main.main()


