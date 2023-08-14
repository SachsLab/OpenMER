The PC which runs our software is directly connected to the acquisition system but it is never connected to the internet. Thus, we copy everything we need to a thumb drive which we then copy to the clinical PC and install.

> For development or testing on an internet-connected computer, please look at the [For Developers](./for-developers.md) documentation.

## Installation

### Distribution

Copy the `<distribution>` folder from the thumb drive to the instrument PC. Be sure to choose a location with lots of disk space because many recording segments will be stored within this folder.

> If you do not have the `<distribution>` folder then follow the [Preparing Distribution](./preparing-distribution.md) instructions to create it.

### Configure

The `<distribution>` folder is ready to use as-is. However, with some additional steps it can be more useful on the target PC.

#### Shortcuts

* Make a desktop shortcut to `<distribution>\mysql\bin\mysqld.exe`.
* Make a desktop shortcut to `<distribution>\<python>\scripts\OpenMER.bat`

#### Settings files

Copy all of the .ini files from `<distribution>\<python>\<python-3.x.x.y>\Lib\site-packages\open_mer\resources\config`
to %HOME%\.open_mer\.

You can then edit these settings files to change some parameters. CbSkConnection.ini can be particularly important if not using Central.

## Using OpenMER

See [Usage Instructions](./usage-instructions.md)

## Test Environment - Without Hardware

Testing without the hardware is also possible using a signal generator source or a data playback source (see below for example).

### Emulate Blackrock NSP

* Run "C:\Program Files (x86)\Blackrock Microsystems\NeuroPort Windows Suite\runNPlayAndCentral.bat"
* Select a recording to play back
* Use Central's hardware configuration tool to enable continuous recording and spike extraction on the recorded channels.
* Follow the general [Usage Instructions](./usage-instructions.md) with one modification:
    * When running `dbs-ddu`, choose "cbsdk playback" from the dropdown menu to reuse the depths from the recording. The value might not update until the file plays back a change in depth.

### Playback XDF file

More instructions are needed. If you have a correctly formatted file, it may be enough to use [XDFStreamer](https://github.com/labstreaminglayer/App-XDFStreamer).
