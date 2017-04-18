# Just some chunks of code to help with development.

from cerebus import cbpy


def compare_chan_configs(d1, d2):
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    intersect_keys = d1_keys.intersection(d2_keys)
    modified = {o: (d1[o], d2[o]) for o in intersect_keys if d1[o] != d2[o]}
    return modified


cbpy.open()
ix = 0
d1 = cbpy.get_channel_config(ix+1)[1]
# Do something in Central
d2 = cbpy.get_channel_config(ix+1)[1]
print(compare_chan_configs(d1, d2))
