For easier running:
* Make a shortcut to `mysql\bin\mysqld.exe`.
* Make a shortcut to `WPy64-3850\scripts\NeuroportDBS.bat`

First run the `mysqld` binary by double-clicking its shortcut. Then do the same for the `NeuroportDBS` batch file.

Additional details follow.

## Blackrock NSP

The NSP must be on. Central should be running.
* If you are going to run this on the same computer that is configuring the hardware and that might run Central, Central must be running first. Central will not start after the NeuroportDBS software is already running.
* If you are going to run this on a separate computer connected to the NSP over the network, then Central is not technically required except for the FeaturesGUI app. If the FeaturesGUI requirement for Central is problematic for you then please let us know and we will try to remove that dependency.
* If you do not have the NSP available then follow the instructions above to setup a test environment.

## DDU

* Choose the COM port the depth digitizer is connected to then click Open.
    * Choosing the wrong serial port may cause the application to hang. Force close then try again. If you are using the batch file to launch then this might mean closing all of the GUI applications and running the batch file again.
    * You can probably identify the correct COM port in Windows Control Panel >Device Manager > Serial & LPT devices.
* By default, it will automatically stream the depth to both LSL and to the NSP (added to the .nev datafile as comments). You can change this behaviour by unchecking the boxes.
* If, like us, the depth readout isn't the same as your distance to target, then add an offset.
    * For example, when using a StarDrive with NexFrame, and distance to target it 85.3 mm, and the StarDrive places the microelectrodes 60 mm toward target when the drive reads depth=0, the remaining distance to target is 25.3 mm, so we add an offset of `-25.3`. As the drive descends the microelectrodes, and the depth reading increases, the reported distance to target approaches 0 until passes the target then reports positive values.

**For FHC motor controller V2**: It reports depth in um, so we have to scale the depth reading by 0.001 . The ability to detect which DDU is in use is not implemented in the DDU GUI so we manually edit DDUGUI.py to hard code the scaling.

## SweepGUI -- RasterGUI -- WaveformGUI

These 3 applications share the same simple instructions: First click "Connect" to open the NSP connection dialog then OK (assuming defaults are OK). Then click Add Plot to open the window.

The connection settings are ignored if Central is running on the same computer, because the default connection method first attempts to connect to Central's shared memory.

### Sweep Plot Audio

The SweepGUI has the ability to stream one of the visualized channels out over the computer's speaker system. You can select which channel is being streamed either by clicking on one of the radio buttons near the top or by using a number on the keyboard (0 for silence, 1-N for each visualized channel). For convenience when using a simple keyboard emulation (e.g. footpad), you may use left-arrow and right-arrow for cycling through the channels, and Space selects silence.  

## Features
Click connect, OK, Add Plot

Then you're presented with a settings window. 

* Under the Subject tab:
    * Type a patient Id or select from the drop-down list if resuming a previously-stored patient.
    * Enter the remaining information.
* Under the Procedure tab:
    * Target name (e.g. STN, GPi, Vim)
    * Type: DBS
    * Recording configuration: choose one that matches best.
    * Electrode configuration: This refers to the arrangement of the electrodes in the BenGun when using an array. Choose the one that matches best.
    * Enter Entry and Target coordinates. Also enter Distance to target to confirm.
    * If you record the Nexframe orientation by recordings its A and E locations then enter them here.
      * TODO: use perfectly-aligned values as defaults.
    * If you use an offset adapter you can specify the direction (A to H) and the offset size in mm.
        
* Click OK to start the GUI
* Click on the "Record" button.
    * Note: To change the default recording path, edit `WPy64-3850\python-3.8.5.amd64\Lib\site-packages\neuroport_dbs\settings\defaults.py` and change the `BASEPATH` value. (We hope to make this easier via a config file in the future.)
* After a new depth is entered and the depth remains constant for 4-8 seconds (depending on signal quality), a segment will be added to the database.
* The current trajectory that is visualized is by default synchronized with the Sweep GUI selection for audio. To change which trajectory is being visualized, you can change which channel you are listening to in SweepGUI, or uncheck the synchronize box and set the channel manually.
