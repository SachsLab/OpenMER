# NeuroportDBS

A collection of software we use for DBS MER using Blackrock Neuroport. Skip ahead to the [Getting Started section](#getting-started) below for help installing this software on your own computer.

## Introduction

Dr. Adam Sachs is a neurosurgeon at the Ottawa Hospital where he and his team implant DBS electrodes to treat motor disorders such as Parkinson's Disease, dystonia, and tremor. Part of the surgical procedure includes microelectrode recording (MER) to map the tissue around the intended DBS target to correct for intrinsic error in the DBS targeting process (i.e., due to imaging, planning, stereotaxy, and brain shift) and to refine the target location.

MER requires specialized equipment and software. While all-in-one medical devices are recommended, Dr. Sachs' research requires a more bespoke solution with multipurpose equipment and custom software. The software and some documentation are made available here in hopes of helping other clinicial-scientists using the Blackrock Neuroport system for DBS.

### Equipment

* A variety of microelectrodes, but mostly [FHC Microtargeting Electrodes](https://www.fh-co.com/product-category/microtargeting/).
* [Blackrock Neuroport](https://www.blackrockmicro.com/neuroscience-research-products/neural-data-acquisition-systems/neuroport-daq-system/) for signal acquisition, processing, and digitization. 
* [Blackrock Cerestim](https://www.blackrockmicro.com/neuroscience-research-products/ephys-stimulation-systems/cerestim-96-neurostimulation-system/) for microstimulation.
* Either the [Medtronic Nexdrive](https://www.medicalexpo.com/prod/medtronic/product-70691-503248.html) or the [FHC STar Drive](https://www.fh-co.com/product/star-drive-motor-encoder-system/)
* An [FHC Depth Digitizing Unit (DDU)](https://www.fh-co.com/product/microtargeting-controller-power-assist-system-2-0/) - they have similar units for the Nexdrive and STar Drive.

### Software

The Blackrock NSP has its own [NeuroPort Central Suite](https://www.blackrockmicro.com/technical-support/software-downloads/) to manage the configuration of the device and to store data. However, its data visualization capabilities are rather limited and not suited for DBS MER.

The NSP data stream is accessible via its open source API [CereLink](https://github.com/dashesy/CereLink) which includes a Python interface called `cerebus.cbpy`. These are maintained by Sachs Lab member [Dr. Chadwick Boulay](https://github.com/cboulay). Most of our Neuroport DBS software is written in Python and much of it uses `cerebus.cbpy` to communicate with the NSP.

There are 3 different applications for visualizing signals in real-time:
* *SweepGUI* - Plots continuous signals in sweeps, optional high-pass filter, and sonifies a channel.
* *RasterGUI* - Plots threshold crossing events in a raster plot, with spike rate displayed in the corner (up to 8 sec history)
* *WaveformGUI* - Plots the waveforms of the last N threshold crossing events.
![Image of vis apps](https://github.com/SachsLab/NeuroportDBS/blob/master/vis_apps_screenshot.PNG?raw=true)

*DDUGUI* visualizes the depth readout from the drive (including adjustable offset value), and sends that depth to the Blackrock NSP as a Comment and also pushes the depth to a [labstreaminglayer](https://github.com/sccn/labstreaminglayer) stream for other processes to retrieve.

*CommentGUI* is for simple text entry to send arbitrary comments to the Blackrock NSP.

*FeaturesGUI* is a much fuller application than the others. It monitors the signals and the depths, then for every new depth it stores a 4-sec segment to a database, and for each segment it calculates a set of predefined features. The depth history of raw segments or features are plotted and updated automatically. The database interaction is a Django app called [SERF](https://github.com/cboulay/SERF) backed by a MySQL database.

[*CereStimDBS*](https://github.com/SachsLab/CereStimDBS) is a Matlab-based tool for controlling the Blackrock CereStim96 in a convenient manner for DBS surgeries.

## Getting Started

We have prepared a zip file for easy distribution. You have to extract it somewhere with ample space, not only for itself but for the database that will be created within.

* TODO: Download for zip
* Jump ahead to [Usage Instructions](#usage-instructions) below.

We also provide more detailed instructions on how to reproduce this environment from scratch. These instructions are useful for NeuroportDBS developers but can be skipped if you are only interested in running it and have access to the zip file.

### Collect Required Files

As NeuroportDBS is intended to be run on a computer that likely is never connected to the internet, we explain how to collect the required files first to be transferred to the clinical computer. Installation instructions on the clinical computer follow below.

We put all of the required software in a prepared [GDrive folder](https://drive.google.com/drive/folders/1bld_ZafpCxRCEPqtiGhGaozw24Uq94nI?usp=sharing). From there, download the WinPython self-extracting executable, all the Python wheel files (`*.whl`), the MySQL zip, and the my.cnf file. If the GDrive is unavailable then you can source them yourself:
* [WinPython](https://winpython.github.io/)
* [MySQL Windows ZIP Archive](https://dev.mysql.com/downloads/mysql/)
* Python wheels in the table below. (Versions provided in case something breaks with newer versions, but as far as we know the software will work with the latest version of each.)

| Package        | Version    | Wheel | pip command |
| -------        | -------    | ----- | ----------- |
| urllib3        | 1.25.8     | [Link](https://files.pythonhosted.org/packages/9f/f0/a391d1463ebb1b233795cabfc0ef38d3db4442339de68f847026199e69d7/urllib3-1.25.10-py2.py3-none-any.whl)
| requests       | 2.23.0     | [Link](https://files.pythonhosted.org/packages/45/1e/0c169c6a5381e241ba7404532c16a21d86ab872c9bed8bdcd4c423954103/requests-2.24.0-py2.py3-none-any.whl)
| pyserial       | 3.4        | [Link](https://files.pythonhosted.org/packages/0d/e4/2a744dd9e3be04a0c0907414e2a01a7c88bb3915cbe3c8cc06e209f59c30/pyserial-3.4-py2.py3-none-any.whl)
| pylsl          | 1.13.6     | [Link](https://files.pythonhosted.org/packages/02/c2/7b58adda02dbfa8f76bf835879d36b83dfc1da2eaa50d124d13a515e148c/pylsl-1.13.6-py2.py3-none-win_amd64.whl)
| pyFFTW         | 0.12.0     | [Link](https://files.pythonhosted.org/packages/b3/a4/7cfbc0b9488a55e35b835110916b8cea863e48a3da0f04e34dbc12ab043d/pyFFTW-0.12.0-cp37-cp37m-win_amd64.whl)
| mysqlclient    | 1.4.6      | [Link](https://files.pythonhosted.org/packages/4a/28/b08ede6cc8382179201455c3b9e5ed0d66aa5921e7c1888828dba48b832b/mysqlclient-2.0.1-cp37-cp37m-win_amd64.whl)
| idna           | 2.9        | [Link](https://files.pythonhosted.org/packages/a2/38/928ddce2273eaa564f6f50de919327bf3a00f091b5baba8dfa9460f3a8a8/idna-2.10-py2.py3-none-any.whl)
| Django         | 3.0.3      | [Link](https://files.pythonhosted.org/packages/2b/5a/4bd5624546912082a1bd2709d0edc0685f5c7827a278d806a20cf6adea28/Django-3.1-py3-none-any.whl)
| chardet        | 3.0.4      | [Link](https://files.pythonhosted.org/packages/bc/a9/01ffebfb562e4274b6487b4bb1ddec7ca55ec7510b22e4c51f14098443b8/chardet-3.0.4-py2.py3-none-any.whl)
| certifi        | 2019.11.28 | [Link](https://files.pythonhosted.org/packages/5e/c4/6c4fe722df5343c33226f0b4e0bb042e4dc13483228b4718baf286f86d87/certifi-2020.6.20-py2.py3-none-any.whl)
| asgiref        | 3.2.3      | [Link](https://files.pythonhosted.org/packages/d5/eb/64725b25f991010307fd18a9e0c1f0e6dff2f03622fc4bcbcdb2244f60d6/asgiref-3.2.10-py3-none-any.whl)
| python-neo     | 0.9        | | `pip install git+https://github.com/NeuralEnsemble/python-neo.git`
| pytf           | 0.1        | [Link](https://github.com/SachsLab/pytf/releases/download/v0.1/pytf-0.1-py2.py3-none-any.whl) |`pip install git+https://github.com/SachsLab/pytf.git`|
| mspacman       | 0.1        | [Link](https://github.com/SachsLab/mspacman/releases/download/v0.1/mspacman-0.1-py2.py3-none-any.whl) |`pip install git+https://github.com/SachsLab/mspacman.git`|
| cerebus        | 0.0.4      | [Link](https://github.com/dashesy/CereLink/releases/download/v7.0.4/cerebus-0.0.4-cp37-cp37m-win_amd64.whl) |`pip install git+https://github.com/dashesy/CereLink.git`|
| cerebuswrapper | 0.1      | [Link](https://github.com/SachsLab/cerebuswrapper/releases/download/v0.1/cerebuswrapper-0.1.0-py3-none-any.whl) |`pip install git+https://github.com/SachsLab/cerebuswrapper.git`|
| serf           | 2.0        | TODO | `pip install git+https://github.com/cboulay/SERF.git#subdirectory=python`|
| neurport_dbs   | 0.3        | TODO | `pip install git+https://github.com/SachsLab/NeuroportDBS.git`|

* For a DBS-friendly GUI to control the CereStim96, follow the instructions at the [CereStimDBS repository](https://github.com/SachsLab/CereStimDBS).

### Install on "Clinical" Windows Computer

Copy the collected files to a folder on the Blackrock computer (or any computer that has ethernet access to the NSP). Run the WinPython self-extracting executable. This will create a folder containing a full Python distribution with many useful packages installed (see full list [here](https://github.com/winpython/winpython/blob/master/changelogs/WinPython-64bit-3.7.6.0.md)).

Inside this new folder, run "WinPython Command Prompt". This will open a Command Prompt with all the paths configured to use this new Python distribution. Use `cd ..` (x2) to change to the directory containing the .whl files. Then type `pip install {packagename}.whl` for each. (Tip: Use tab-completion after typing the first few letters of each package name).

If using FeaturesGUI, then a MySQL database backend is required. If you are willing to install a full program suite and service onto the clinical computer then follow the instructions at [Segmented Electrophys Recordings and Features Database (SERF)](https://github.com/cboulay/SERF). This has the advantage of installing the server as a service and it comes with MySQL Workbench which is a useful tool to administer the database server.

For a less-intrusive solution, simply unzip mysql-8.0.21-winx64.zip and rename the folder `mysql`.

#### Configuring MySQL Database Server

* In the command prompt, `cd` into the `bin` subfolder of the unzipped mysql folder.
* Create a mysql\data folder along with the base databases: `mysqld --initialize-insecure --console`
    * If you wish to use a different datadir then you must first create a `my.cnf` file in the root `mysql` folder with the following contents (commented out lines aren't necessary, just keeping them here for reference):
        ```
        [mysqld]
        datadir=path/to/data
        #port = 3306
        #socket = /tmp/mysql.sock
        #pid-file = /Volumes/STORE/eerfdata/Chadwicks-MacBook-Pro.local.pid
        #default-storage-engine = MyISAM
        #default_tmp_storage_engine = MyISAM
        #query_cache_type = 1
        #key_buffer_size = 2G
        #query_cache_limit = 400M
        ```
    * If you wish to secure the database then you'll need to give the root account a password. Do so with `mysql_secure_installation`.
    * If you change from the default username (`root`) and password (none) then you will have to tell `serf` what the username and password are. Create a file named `my_serf.cnf` and put it in the path found with the following command: `python -c "import os; print(os.path.expanduser('~'))"` The file contents should be
        ```
        [client]
        user = root
        password = {password}
        #port = 3306
        #socket = /tmp/mysql.sock
        ```
* Double-click on the `mysqld` executable in the bin folder.
* `mysqladmin --user=root create serf`
* Install the serf databases with the following commands:
    ```
    serf-makemigrations
    serf-migrate
    ```

### Test

* Run "C:\Program Files (x86)\Blackrock Microsystems\NeuroPort Windows Suite\runNPlayAndCentral.bat"
* Select a recording to play back
* Use Central's hardware configuration tool to enable continuous recording and spike extraction on the recorded channels.
* Follow the general Usage Instructions below.
    * When running `dbs-ddu`, choose "cbsdk playback" from the dropdown menu.

## Usage Instructions

The executables we want to run are all located in the `WPy64-3760\python-3.7.6.amd64\Scripts` folder. You probably want to make some shortcuts to these executables on your desktop.
* `dbs-sweep`. Click connect, OK, Add Plot
* `dbs-raster`. Click connect, OK, Add Plot
* `dbs-waveform`. Click connect, OK, Add Plot
* `dbs-ddu`. Choose your serial port (or "cbsdk playback") then press Open.
    * Choosing the wrong serial port may cause the application to hang. Force close then try again.
* `mysql\bin\mysqld`
* `dbs-features`. See below. 

### Sweep Plot

### Raster Plot

### Waveforms Plot

### DDU

### Features
Click connect, OK, Add Plot

Then you're presented with a settings window. 

* Under the Subject tab:
    * Type a patient Id or select from the drop-down list if resuming a previously-stored patient.
    * Enter the remaining information.
* Under the Procedure tab:
    * Procedure name? (TODO: Tooltip)
    * Type: surgical
    * Recording configuration: choose one that matches best. (what's this used for again?)
    * Electrode configuration: This refers to the arrangement of the electrodes when using an array. Choose the one that matches best.
    * Enter Entry and Target coordinates. Also enter Distance to target to confirm.
    * If you record the Nexframe orientation by recordings its A and E locations then enter them here.
        * TODO: use perfectly-aligned values as defaults.