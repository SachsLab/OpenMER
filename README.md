# NeuroportDBS

A collection of software we use for DBS MER using Blackrock Neuroport. Skip ahead to the Getting Started section below if you are interested in installing this software on your own computer.

## Introduction

Dr. Adam Sachs is a neurosurgeon at the Ottawa Hospital and he and his team implant DBS electrodes to treat motor disorders such as Parkinson's Disease, dystonia, and tremor. Part of the surgical procedure includes microelectrode recording (MER) to map the tissue around the intended DBS target to correct for intrinsic error in the DBS targeting process (i.e., due to imaging, planning, stereotaxy, and brain shift) and to refine the target location.

MER requires specialized equipment and software. While some medical device manufacturers sell all-in-one systems (maybe the most popular is the Alpha Omega Neuromega), we use a more bespoke solution with multipurpose equipment and custom software.

### Equipment

* We've used a variety of microelectrodes, but mostly [FHC Microtargeting Electrodes](https://www.fh-co.com/product-category/microtargeting/).
* [Blackrock Neuroport](https://www.blackrockmicro.com/neuroscience-research-products/neural-data-acquisition-systems/neuroport-daq-system/) for signal acquisition, processing, and digitization. 
* [Blackrock Cerestim](https://www.blackrockmicro.com/neuroscience-research-products/ephys-stimulation-systems/cerestim-96-neurostimulation-system/) for microstimulation.
* Either the [Medtronic Nexdrive](https://www.medicalexpo.com/prod/medtronic/product-70691-503248.html) or the [FHC STar Drive](https://www.fh-co.com/product/star-drive-motor-encoder-system/)
* An [FHC Depth Digitizing Unit (DDU)](https://www.fh-co.com/product/microtargeting-controller-power-assist-system-2-0/) - they have similar units for the Nexdrive and STar Drive.

### Software

The Blackrock NSP has its own [NeuroPort Central Suite](https://www.blackrockmicro.com/technical-support/software-downloads/) to manage the configuration of the device and to store data. However, its data visualization capabilities are rather limited and not suited for DBS MER.

The NSP data stream is accessible via its open source API [CereLink](https://github.com/dashesy/CereLink) which includes a Python interface called `cbpy`. These are maintained by our very own [Dr. Chadwick Boulay](https://github.com/cboulay). Most of our software is written in Python and much of it uses `cbpy` to communicate with the NSP.

We have 3 different applications for visualizing signals in real-time.
* *SweepGUI* - Plots continuous signals in sweeps, optional high-pass filter, and sonifies a channel.
* *RasterGUI* - Plots threshold crossing events in a raster plot, with spike rate displayed in the corner (up to 8 sec history)
* *WaveformGUI* - Plots the waveforms of the last N threshold crossing events.

Our *DDUGUI* visualizes the depth readout from the drive (including adjustable offset value), and sends that depth to the Blackrock NSP as a Comment and also pushes the depth to a [labstreaminglayer](https://github.com/sccn/labstreaminglayer) stream for other processes to retrieve.

*CommentGUI* is for simple text entry to send arbitrary comments to the Blackrock NSP.

*CereStimGUI* is a Matlab-based tool for controlling the Blackrock CereStim96 in a convenient manner for our surgeries.

*FeaturesGUI* is a much fuller application than the others. It monitors the signals and the depths, then for every new depth it stores a 4-sec segment to a database, and for each segment it calculates a set of predefined features. The depth history of raw segments or features are plotted and updated automatically. The database interaction is a Django app called [NeuroportDBS_eerfapp_DB](https://github.com/SachsLab/NeuroportDBS_eerfapp_DB) backed by a MySQL database.

## Getting Started

Almost all of our software is written in Python. It is thus necessary to install a Python interpreter. I would normally recommend to install miniconda to manage your Python environment, but as this software is intended to be run on a computer that likely is never connected to the internet, it is easier to install a more complete Python distribution and supplement it with the missing packages.

### Collect Required Files

From our prepared [GDrive folder](https://drive.google.com/drive/folders/1bld_ZafpCxRCEPqtiGhGaozw24Uq94nI?usp=sharing), download the WinPython executable and all the Python wheel files (`*.whl`).
TODO - Continue instructions...
