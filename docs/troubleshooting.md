## Connectivity

### ZeroMQ Ports

We use ZeroMQ sockets for inter-process communication using the pub-sub pattern. The following table lists the sockets'
ports, topics, and notes about the accompanying messages.

| Publisher            | Port  | Topic              | Message                                              | Subscribers          |
|----------------------|-------|--------------------|------------------------------------------------------|----------------------|
| ProcessGUI           | 60001 | procedure_settings | dict of settings dicts "procedure" and               | FeaturesGUI          |
| Depth_Process (SERF) | 60002 | snippet_status     | startup; notrecording; recording; accumulating; done | ProcessGUI           |
| SweepGUI             | 60003 | channel_select     | dict with channel, range, highpass                   | FeaturesGUI          |
| FeaturesGUI          | 60004 | features           | refresh                                              | FeaturesGUI          |
| DepthGUI             | 60005 | ddu                | float of depth                                       | Depth_Process (SERF) |

### LSL

| Origin   | Stream Name     | Stream Type | Content                 | Inlets               |
|----------|-----------------|-------------|-------------------------|----------------------|
| DepthGUi | electrode_depth | depth       | 1 float32 of elec depth | Depth_Process (SERF) |

### Blackrock NSP

If Central is running then these tools should attempt to connect to Central's shared memory, and the network settings are irrelevant. If Central is not running then you'll have to make sure the network settings are correct, and this may depend on how your PC and NSP are connected.

The NSP always has the same ip address: 192.168.137.128. I don't think this can be changed, but if it is then you'll have to change that setting in the connect dialog window.

If the PC is linked directly to the NSP, then we use the following network adapter settings. In the adapter properties,  double click on Internet Protocol Version 4 (TCP/IPv4). Set the IP address to be 192.168.137.1 and the Subnet mask 255.255.255.0.  If you require a different IP address then you'll have to change this in the connect dialog window.

The client (PC) port defaults to 51002
The client IP address is 192.168.137.1 on Windows, and Mac and Linux use netmasks: 255.255.255.255 on Mac, and 192.168.137.255 on Linux
The NSP IP address is 192.168.137.128 and port 51001 

## DDU numbers changing too fast!

Version 2 of FHC's DDU returns the depths in um, but the DDUGUI software is expecting numbers in mm. I have yet to figure out a reliable way to determine which drive is in use without crashing the serial port. The simple solution is to divide the value by 1000. For now, the way to do this is to uncomment a line in DDUGUI.py (search for "FHC DDU V2").
