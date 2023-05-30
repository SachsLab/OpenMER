Our primary method of distributing the full OpenMER Suite is as a giant zip file. TODO: Link!

If you want to setup the individual pieces on an internet-connected computer (e.g., for development or testing) then please look at the [For Developers](./for-developers.md) documentation. 

It is expected that the target computer is a standalone computer that has a dedicated connection to the data acquisition system, such as a manufacturer-provided PC which is usually not connected to the internet. Testing without the hardware is also possible using a signal generator source or a data playback source (see below for example).

Extract the zip file to the target computer. Choose a destination with a lot of disk space because the data segments will be saved within.

Updates may come in the form of a smaller zip file to extract within a specific subfolder of the extracted distribution.

Proceed with the [Usage Instructions](./usage-instructions.md)

## Test Environment - Without Hardware

### Emulate Blackrock NSP

* Run "C:\Program Files (x86)\Blackrock Microsystems\NeuroPort Windows Suite\runNPlayAndCentral.bat"
* Select a recording to play back
* Use Central's hardware configuration tool to enable continuous recording and spike extraction on the recorded channels.
* Follow the general [Usage Instructions](./usage-instructions.md) with one modification:
    * When running `dbs-ddu`, choose "cbsdk playback" from the dropdown menu to reuse the depths from the recording. The value might not update until the file plays back a change in depth.

### Playback XDF file

More instructions are needed. If you have a correctly formatted file, it may be enough to use [XDFStreamer](https://github.com/labstreaminglayer/App-XDFStreamer).
