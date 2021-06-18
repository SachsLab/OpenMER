Our primary method of distributing the full NeuroportDBS Suite is as a giant zip file. TODO: Link!

If you want to setup the individual pieces on an internet-connected computer (e.g., for development or testing) then please look at the [For Developers](./for-developers.md) documentation. 

It is expected that the target computer is a Windows computer that has a dedicated network connection to the NSP, such as the Blackrock-provided PC. Testing without the NSP is also possible (see below).

Extract the zip file to the target computer. A lot of disk space is required because the data segments will be saved within.

Updates may come in the form of a smaller zip file to extract within a specific subfolder of the extracted distribution.

Proceed with the [Usage Instructions](./usage-instructions.md)

## Test Environment - Without NSP

* Run "C:\Program Files (x86)\Blackrock Microsystems\NeuroPort Windows Suite\runNPlayAndCentral.bat"
* Select a recording to play back
* Use Central's hardware configuration tool to enable continuous recording and spike extraction on the recorded channels.
* Follow the general Usage Instructions in the next section with one modification:
    * When running `dbs-ddu`, choose "cbsdk playback" from the dropdown menu to reuse the depths from the recording. The value might not update until the file plays back a change in depth.
