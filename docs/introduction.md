Dr. Adam Sachs is a neurosurgeon at the Ottawa Hospital where he and his team implant DBS electrodes to treat motor disorders such as Parkinson's Disease, dystonia, and tremor. Part of the surgical procedure includes microelectrode recording (MER) to map the tissue around the intended DBS target to correct for intrinsic error in the DBS targeting process (i.e., due to imaging, planning, stereotaxy, and brain shift) and to refine the target location.

MER requires specialized equipment and software. While all-in-one medical devices are recommended, Dr. Sachs' research requires a more bespoke solution with multipurpose equipment and custom software. The software and some documentation are made available here with the goal of helping other clinician-scientists to use custom systems for DBS MER.

## Equipment

Here is the list of equipment we use. It may be possible to use this software with other equipment.

* A variety of microelectrodes, but mostly [FHC Microtargeting Electrodes](https://www.fh-co.com/product-category/microtargeting/).
* We use the [Blackrock Neuroport](https://www.blackrockmicro.com/neuroscience-research-products/neural-data-acquisition-systems/neuroport-daq-system/) for signal acquisition, processing, and digitization. Other devices are possible.
* An [FHC Depth Digitizing Unit (DDU)](https://www.fh-co.com/product/microtargeting-controller-power-assist-system-2-0/) - they have similar units for the Nexdrive and STar Drive.
* A drive compatible with the DDU, such as the [Medtronic Nexdrive](https://www.medicalexpo.com/prod/medtronic/product-70691-503248.html) or the [FHC STar Drive](https://www.fh-co.com/product/star-drive-motor-encoder-system/)
* The [Blackrock Cerestim](https://www.blackrockmicro.com/neuroscience-research-products/ephys-stimulation-systems/cerestim-96-neurostimulation-system/) for microstimulation. The Cerestim is not required.

## Software

NeuroportDBS is a Suite of 6 different applications for visualizing signals in real-time:

![Image of vis apps](https://github.com/SachsLab/NeuroportDBS/blob/master/vis_apps_screenshot.PNG?raw=true)

* *SweepGUI* - Plots continuous signals in sweeps, optional high-pass filter, and sonifies a channel.
* *RasterGUI* - Plots threshold crossing events in a raster plot, with spike rate displayed in the corner (up to 8 sec history)
* *WaveformGUI* - Plots the waveforms of the last N threshold crossing events.
* *DDUGUI* visualizes the depth readout from the drive (including adjustable offset value), and sends that depth to the Blackrock NSP as a Comment and also pushes the depth to a [labstreaminglayer](https://github.com/sccn/labstreaminglayer) stream for other processes to retrieve.
* *FeaturesGUI* is a much fuller application than the others. It monitors the signals and the depths, then for every new depth it stores a 4-sec segment to a database, and for each segment it calculates a set of predefined features. The depth history of raw segments or features are plotted and updated automatically. The database interaction occurs via a Django app called [SERF](https://github.com/cboulay/SERF) backed by a MySQL database.
* *CommentGUI* (not shown) is for simple text entry widget to send arbitrary comments to the Blackrock NSP.

We also use a GUI application we developed called [*CereStimDBS*](https://github.com/SachsLab/CereStimDBS) for controlling the Blackrock CereStim96 in a convenient manner for DBS surgeries.

### Dependencies

When using Blackrock hardware, the following tools and SDKs are needed.

The Blackrock NSP has its own [NeuroPort Central Suite](https://www.blackrockmicro.com/technical-support/software-downloads/) to manage the configuration of the device and to store data. However, its data visualization capabilities are rather limited and not suited for DBS MER.

The NSP data stream is accessible via an open source API [CereLink](https://github.com/CerebusOSS/CereLink) which includes a Python interface called `cerebus.cbpy`. These are maintained by Sachs Lab member Chadwick Boulay. Most of our Neuroport DBS software is written in Python and much of it uses `cerebus.cbpy` and a custom [cerebuswrapper](https://github.com/SachsLab/cerebuswrapper) to communicate with the NSP.
