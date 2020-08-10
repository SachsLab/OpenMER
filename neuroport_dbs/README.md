# NeuroportDBS

## DBSGUI

This contains graphical user interfaces for signal visualization and interaction
using a Blackrock Microsystems Neuroport during DBS surgeries.

### Requirements

* Python 3
    * pyserial
    * pyqt5
    * qtpy
    * numpy
    * pyaudio
    * scipy
    * pyqtgraph
    * cerebus.cbpy (see below)
    * [cerebuswrapper](https://github.com/SachsLab/cerebuswrapper)
        * `pip install git+https://github.com/SachsLab/cerebuswrapper.git`
    
cerebus is a Python package to interface with the Neuroport over the network protocol.
Download the cerebus python wheel for your platform and Python version from [here](https://github.com/dashesy/CereLink/releases/tag/7.0)
If a matching wheel is not found, see [CereLink](https://github.com/dashesy/CereLink/) for instructions on how to build cbsdk then install the Python package.
Note that we use our [CereLink7.0 branch](https://github.com/dashesy/CereLink/tree/CereLink7.0).

There can be some tricks to connecting to the neuroport with this library.
Mac users, see [here](http://support.blackrockmicro.com/KB/View/168747-using-cbmex-on-osx).

## DBSGUI Usage instructions

TODO: More detailed instructions needed.

Try running one or more of SweepGUI.py, RasterGUI.py, WaveformGUI.py, DDUGUI.py
