import os
import sys

# Locate all sources
if "__file__" in locals():
	root_path = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
else:
	root_path = os.path.realpath(os.path.join(os.getcwd(), '..'))

data_path = os.path.realpath(os.path.join(root_path, '..', '..', '..', 'data_collected', '20170817-120131'))

sys.path.append(root_path)
sys.path.append(data_path)
