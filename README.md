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

The NSP data stream is accessible via its open source API [CereLink](https://github.com/dashesy/CereLink) which includes a Python interface called `cerebus.cbpy`. These are maintained by Sachs Lab member [Dr. Chadwick Boulay](https://github.com/cboulay). Most of our Neuroport DBS software is written in Python and much of it uses `cerebus.cbpy` and a custom [cerebuswrapper](https://github.com/SachsLab/cerebuswrapper) to communicate with the NSP.

NeuroportDBS has 3 different applications for visualizing signals in real-time:
* *SweepGUI* - Plots continuous signals in sweeps, optional high-pass filter, and sonifies a channel.
* *RasterGUI* - Plots threshold crossing events in a raster plot, with spike rate displayed in the corner (up to 8 sec history)
* *WaveformGUI* - Plots the waveforms of the last N threshold crossing events.
![Image of vis apps](https://github.com/SachsLab/NeuroportDBS/blob/master/vis_apps_screenshot.PNG?raw=true)

*DDUGUI* visualizes the depth readout from the drive (including adjustable offset value), and sends that depth to the Blackrock NSP as a Comment and also pushes the depth to a [labstreaminglayer](https://github.com/sccn/labstreaminglayer) stream for other processes to retrieve.

*CommentGUI* is for simple text entry to send arbitrary comments to the Blackrock NSP.

*FeaturesGUI* is a much fuller application than the others. It monitors the signals and the depths, then for every new depth it stores a 4-sec segment to a database, and for each segment it calculates a set of predefined features. The depth history of raw segments or features are plotted and updated automatically. The database interaction occurs via a Django app called [SERF](https://github.com/cboulay/SERF) backed by a MySQL database.

[*CereStimDBS*](https://github.com/SachsLab/CereStimDBS) is a Matlab-based tool for controlling the Blackrock CereStim96 in a convenient manner for DBS surgeries.

## Getting Started

There are 3 different approaches to working with this software:
1. A simple all-in-one zip distribution.
2. For maintainers of the distribution - to reproduce the distribution from scratch;
3. Expert developers who want to work within their own environment, especially with their own MySQL database server.

Choose one of the approaches and follow the appropriate instructions below.

### 1 - Zip Distribution

* We have prepared a zip file for easy distribution. Please ask us for the link to download the file. (It's huge so we don't want unnecessary downloads.)
* Extract the zip onto a Windows computer that has a network connection to the NSP. The Blackrock PC should work. A lot of disk space is required because the data segments will be saved within.
* Jump ahead to [Usage Instructions](#usage-instructions) below.

### 2 - For Maintainers of the Zip Distribution

* Download the latest [WinPython release](https://github.com/winpython/winpython/releases/latest).
    * These instructions were tested with Winpython64-3.8.5.0
* Run the WinPython self-extracting executable. This will create a folder containing a full Python distribution with many useful packages installed (see full list [here](https://github.com/winpython/winpython/blob/master/changelogs/WinPython-64bit-3.8.5.0.md)).
* [Edit the `WPy64-3850\settings\winpython.ini` file](https://sourceforge.net/p/winpython/wiki/Environment/) and add the following line: `PATH = %WINPYDIR%\Lib\site-packages\PyQt5\Qt\bin;%PATH%`
* Download [MySQL Windows ZIP Archive](https://dev.mysql.com/downloads/mysql/)
    * Tested with mysql-8.0.2.1-win64.zip
* Next to the WinPython folder, extract the mysql zip and rename the extracted folder to `mysql`
* In the WinPython folder, run "WinPython Command Prompt". This will open a Command Prompt with all the paths configured to use this new Python distribution.
* Install all of the Python packages listed in the table below.
    * Version numbers may not be important. Please try the latest version and report to us if it does not work.
    * The method to install the packages isn't important. If you're on an internet-connected computer then you can use the pip commands. Otherwise you can first download the wheels then bring them to the development computer to pip install the wheels.
    * If you wish to be able to modify any of the SachsLab packages that are pure python (mspacman, cerebuswrapper, serf, **neuroport_dbs**) then you may do so by first cloning the repository to get the source and installing the package in-place: Using the WinPython command prompt, run `pip install -e .` from within the cloned directory.
    * The `cerebus` package may complain "DLL load failed". This happens when cerebus.cbpy can't find Qt5 or it finds the wrong version. This SHOULD be fixed by editing the path in the 3rd step, but I also found it necessary to copy Qt5Core.dll and Qt5Xml.dll from the above path directly into the site-packages\cerebus folder. We are trying to remove the qt dependency from cerebus to avoid this in the future.
* In the command prompt, `cd` into the `bin` subfolder of the unzipped mysql folder.
* Create a mysql\data folder along with the base databases: `mysqld --initialize-insecure --console`
    * You can change the default data directory, username, and password. See the section below "Configuring MySQL Database Server"
* Double-click on the `mysqld` executable in the bin folder.
* Back in the command prompt, run `mysqladmin --user=root create serf`
* Install the serf databases with the following commands:
    ```
    serf-makemigrations
    serf-migrate
    ```
* Jump ahead to [Usage Instructions](#usage-instructions) below.

#### Required Python Packages

| Package        | Version    | Wheel | pip command |
| -------        | -------    | ----- | ----------- |
| pyFFTW         | 0.12.0     | [Link](https://files.pythonhosted.org/packages/2b/e4/822d4cf12cd907fb8e80844db48aef7adf9e888c89256feb510fa81ae83f/pyFFTW-0.12.0-cp38-cp38-win_amd64.whl)
| mysqlclient    | 2.0.1      | [Link](https://files.pythonhosted.org/packages/b2/72/e205fcf877dd0ec05d71b975def8ecef3ae4bb7fee14434615140ebdc168/mysqlclient-2.0.1-cp38-cp38-win_amd64.whl)
| Django         | 3.1        | [Link](https://files.pythonhosted.org/packages/2b/5a/4bd5624546912082a1bd2709d0edc0685f5c7827a278d806a20cf6adea28/Django-3.1-py3-none-any.whl)
| quantities     | 0.12.4     | | |
| python-neo     | 0.9.0       | | `pip install git+https://github.com/NeuralEnsemble/python-neo.git`
| pylsl          | 1.13.6     | [Link](https://files.pythonhosted.org/packages/02/c2/7b58adda02dbfa8f76bf835879d36b83dfc1da2eaa50d124d13a515e148c/pylsl-1.13.6-py2.py3-none-win_amd64.whl)
| pytf           | 0.1        | [Link](https://github.com/SachsLab/pytf/releases/download/v0.1/pytf-0.1-py2.py3-none-any.whl) |`pip install git+https://github.com/SachsLab/pytf.git`|
| mspacman       | 0.1        | [Link](https://github.com/SachsLab/mspacman/releases/download/v0.1/mspacman-0.1-py2.py3-none-any.whl) |`pip install git+https://github.com/SachsLab/mspacman.git`|
| cerebus        | 0.0.4      | [Link](https://github.com/dashesy/CereLink/releases/download/v7.0.5/cerebus-0.0.4-cp38-cp38-win_amd64.whl) |N/A - must use wheel|
| cerebuswrapper | 0.1      | [Link](https://github.com/SachsLab/cerebuswrapper/releases/download/v0.1/cerebuswrapper-0.1.0-py3-none-any.whl) |`pip install git+https://github.com/SachsLab/cerebuswrapper.git`|
| serf           | 1.1        | [Link](https://github.com/cboulay/SERF/releases/download/v1.1/serf-1.1-py3-none-any.whl) | `pip install git+https://github.com/cboulay/SERF.git#subdirectory=python`|
| neurport_dbs   | 0.3        | TODO | `pip install git+https://github.com/SachsLab/NeuroportDBS.git`|

#### Configuring MySQL Database Server

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

### 3 - For experts who want to use their existing environment

We assume you know how to work with conda environments and that you have a MySQL database server running and configured to your liking.
* Install the Python packages from the table above.
* Adapt the instructions at [Segmented Electrophys Recordings and Features Database (SERF)](https://github.com/cboulay/SERF) to prepare the database server for these tools.
* If you have a hybrid distribution/system-MySQL environment (i.e., Guillaume) then you may also wish to use some of the MySQL DB config settings from above.

## Test Environment

* Run "C:\Program Files (x86)\Blackrock Microsystems\NeuroPort Windows Suite\runNPlayAndCentral.bat"
* Select a recording to play back
* Use Central's hardware configuration tool to enable continuous recording and spike extraction on the recorded channels.
* Follow the general Usage Instructions below.
    * When running `dbs-ddu`, choose "cbsdk playback" from the dropdown menu to reuse the depths from the recording. The value might not update until the file plays back a change in depth.

## Usage Instructions

The NSP must be on and Central must be running. If you are not connected to the NSP then follow the instructions above to setup a test environment.

The executables we want to run are all located in the `WPy64-3850\python-3.8.5.amd64\Scripts` folder. You probably want to make some shortcuts to these executables on your desktop.
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
* Click OK to start the GUI
* Click on the "Record" button.
    * Note: To change the default recording path, edit `WPy64-3850\python-3.8.5.amd64\Lib\site-packages\neuroport_dbs\FeaturesGUI.py` and change the `BASEPATH` value. (We hope to make this easier via a config file in the future.)
* After a new depth is entered and the depth remains constant for 4-8 seconds (depending on signal quality), a segment will be added to the database.
* The current trajectory that is visualized is by default synchronized with the Sweep GUI selection for audio. To change which trajectory is being visualized, you can change which channel you are listening to, or uncheck the synchronize box and set the channel manually.
