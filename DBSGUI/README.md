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
    * cerebus.cbpy
    
cerebus is a Python package to interface with the Neuroport over the network protocol.
See [CereLink](https://github.com/dashesy/CereLink/) for instructions on how to build cbsdk then install the Python package.
Note that we use our [Production_7.0 branch](https://github.com/SachsLab/CereLink/tree/Production_7.0).

There can be some tricks to connecting to the neuroport with this library.
Mac users, see [here](http://support.blackrockmicro.com/KB/View/168747-using-cbmex-on-osx).
