classdef cerestim96 < handle
    % cerestim96 MATLAB class wrapper to an underlying C++ class
    %
    % This is the MATLAB interface for CereStim 96 Stimulators. 
    % In order to connect to a CereStim 96 device, instantiate a new object
    % of this class and read/write data using the control methods
    % provided below. 
    %
    % To access a method use: 
    %                           out = cerestim96_object.method(in)
    %
    % At any time, you can access the detailed method documentation using 
    % the following:
    %                           cerestim96_object.method('help')
    %
    % cerestim96 Methods:
	%    scanForDevices - Scans USB ports for attached stimulators
	%    selectDevice - Selects a stimulator from the list obtained from scanForDevices()
    %    connect - Connects to the CereStim 96 Stimulator
    %    disconnect - Disconnects the CereStim 96 Stimulator
    %    libraryVersion - Prints the current version of the API that is being used
    %    manualStim - Sends a single stimulus pulse of one of the stimulation waveforms to an electrode
    %    measureOutputVoltage - Measures the output voltage at five locations in a stimulus
    %    beginSequence - Defines the beginning of a stimulation sequence
    %    endSequence - Defines the end of a stimulation sequence
    %    beginGroup - Defines the beginning of a set of stimulations to occur simultaneously
    %    endGroup - Defines the end of a set of stimulations to occur simultaneously
    %    autoStim - Defines a stimulus to an electrode in a stimulation script
    %    wait - Tells the CereStim 96 to wait before executing the next command within a stimulation script
    %    play - Tells the CereStim 96 the number of times that it should run a stimulation script
    %    stop - Stops the currently running stimulation script
    %    pause - Pauses the currently running stimulation script
    %    maxOutputVoltage - Limits the maximum output voltage that can be delivered during stimulation and allows reading the output compliance voltage from the stimulator
    %    deviceInfo - Returns all the information about the CereStim 96 
    %    enableModule - Enables modules for stimulation
    %    disableModule - Disables modules that are installed in the CereStim
    %    setStimPattern - Creates a custom biphasic stimulation waveform
    %    getStimPattern - Reads the configuration of a specific stimulation waveform
    %    getSequenceStatus - Reads what state the stimulator is in
    %    stimulusMaxValue - Sets upper limits for stimulation parameters and reads current limits
    %    groupStimulus - Creates stimulation parameters in advance to perform simultaneous stimulations
    %    trigger - Sets the stimulator on trigger mode
    %    disableTrigger - Disables trigger mode
    %    updateMap - Maps the connection of each channel to its corresponding electrode number
    %    testElectrodes - Returns the impedance of the electrodes at 1kHz
    %    testModules - Reports the status of each module and the voltage measured
    %    getHardwareValues - Reads the hardware values that are set in the stimulator
    %    disableStimulus - Disables a stimulation waveform 
    %    isConnected - Tests whether the API is connected to a physical CereStim 96 device
    %    getInterface - Checks what interface type is being used for the connection to the CereStim 96
    %    getMinMaxAmplitude - Returns the min and max amplitudes that are allowed for stimulation
    %    usbAddress - Returns the USB address of the connected device
    %    isSafetyDisabled - Tests whether the safety limits in the CereStim 96 firmware are disabled
    %    isLocked - Tests whether the CereStim 96 device is locked


    
    
	
	methods(Static)
		function serials = scanForDevices()
			% Scans the USB ports and looks for CereStim 96 Stimulators plugged in
            % Format: 	cerestim96.scanForDevices()
			% Outputs:
			%	 		A list of serial numbers of the stimualtors plugged into the computer 
			% 		  	
			serials = stimmex('scan');
		end
    end
    
    properties (SetAccess = private, Hidden = true)
        objectHandle; % Handle to the underlying C++ class instance
    end
    methods
        %% Constructor - Create a new C++ class instance 
        function this = cerestim96(varargin)
            this.objectHandle = stimmex('init');
        end
        
        %% Destructor - Destroy the C++ class instance
        function delete(this)
            % Deletes a class object
            stimmex('delete', this.objectHandle);            
        end
		
		%% User Interface Functions
        function x = selectDevice(this, varargin)
			% Selects a CereStim 96 Stimulator out of all the stimulators plugged into the computer
            % Format: 	cerestim_object.selectDevice(index) 
			% Inputs:
			%	index: 	The stimulator index according to the list of serial numbers 
			% 		  	obtained from cerestim96.scanForDevices() call 

			if nargout
                [x] = stimmex('selectdevice', this.objectHandle, varargin{:});
            else
                stimmex('selectdevice', this.objectHandle, varargin{:});
            end
        end

        
        function x = connect(this, varargin)
            % Connects to the CereStim 96 Stimulator
            % Format: 	cerestim_object.connect() 
			%		 	cerestim_object.connect(interface)
			%		 	cerestim_object.connect(interface, usbparams)
			% Inputs:
			%	interface (optional): 0 (Default), 1 (USB)
			%	usbparams (optional): A three element array [pid timeout vid] where
			%					   	  pid is the product ID
			%					      timeout is the time in ms to try to connect before timeout
			%					      vid is the vendor ID
			
            if nargout
                [x] = stimmex('connect', this.objectHandle, varargin{:});
            else
                stimmex('connect', this.objectHandle, varargin{:});
            end
        end
        
        function x = disconnect(this, varargin)
            % Disconnects the CereStim 96 Stimulator
            % Format: 	cerestim_object.disconnect()
            
            if nargout
                [x] = stimmex('disconnect', this.objectHandle, varargin{:});
            else
                stimmex('disconnect', this.objectHandle, varargin{:});
            end
        end
        
        function x = libraryVersion(this, varargin)
            % Prints the current version of the API that is being used
            % Format:	cerestim_object.libraryVersion()
            
            if nargout
                [x] = stimmex('libver', this.objectHandle, varargin{:});
            else
                stimmex('libver', this.objectHandle, varargin{:});
            end
        end
        
        function x = manualStim(this, varargin)
            % Sends a single stimulus pulse of one of the stimulation waveforms to an electrode
            % Format: 		cerestim_object.manualStim(electrode, waveform)
			% Inputs:
			%	electrode:	The electrode that should be stimulated (1-96)
			%	waveform:	The stimulation waveform to use (1-15)
            if nargout
                [x] = stimmex('manualstim', this.objectHandle, varargin{:});
            else
                stimmex('manualstim', this.objectHandle, varargin{:});
            end
        end
        
        function x = measureOutputVoltage(this, varargin)
            % Sends a known stimulation configuration from the selected module to a specific electrode
            % The stimulator is capable of sending out a stimulus using known values and measure the
			% voltage that is returned at five locations during the course of that stimulation.
			% The returned five values are the voltages at: Just before the first phase, during the first
			% phase, in between phases, during the second phase, and just after the second phase.
			% Format: 		x = cerestim_object.measureOutputVoltage(module, electrode)
			% Inputs:
			% 	module:		The current module (0-15) that should send the stimulus (must be enabled)
			% 	electrode:	The electrode to send the stimulation (1-96)
			% Outputs:
			%	x:			Voltage measurements at five locations in stimulation cycle
            
            if nargout
                [x] = stimmex('measureoutv', this.objectHandle, varargin{:});
            else
                stimmex('measureoutv', this.objectHandle, varargin{:});
            end
        end
        
        function x = beginSequence(this, varargin)
            % Defines the beginning of a stimulation sequence
            % This is the first command that must be called when creating a stimulation script.
			% After calling this you are able to call 'wait', 'autostim', 'begofgroup', and
			% 'endofgroup' commands. The stimulation script can have up to 128 commands, excluding
			% 'begofseq' and 'endofseq'
			% Format: 	cerestim_object.beginSequence()
            
            if nargout
                [x] = stimmex('begofseq', this.objectHandle, varargin{:});
            else
                stimmex('begofseq', this.objectHandle, varargin{:});
            end
        end        

        function x = endSequence(this, varargin)
            % Defines the end of a stimulation sequence
            % Format: 	cerestim_object.endSequence()
            
            if nargout
                [x] = stimmex('endofseq', this.objectHandle, varargin{:});
            else
                stimmex('endofseq', this.objectHandle, varargin{:});
            end
        end       
        
        function x = beginGroup(this, varargin)
            % Defines the beginning of a set of stimulations to occur simultaneously
            % The only commands that are valid inside the block defined by 'begofgroup'
			% and 'endofgroup' are 'autostim' commands. The number of simultaneous 
			% stimulations depends on the number of modules installed.
			% Format: 	cerestim_object.beginGroup()
            
            if nargout
                [x] = stimmex('begofgroup', this.objectHandle, varargin{:});
            else
                stimmex('begofgroup', this.objectHandle, varargin{:});
            end
        end       
        
        function x = endGroup(this, varargin)
            % Defines the end of a set of stimulations to occur simultaneously
            % The only commands that are valid inside the block defined by 'begofgroup'
			% and 'endofgroup' are 'autostim' commands. The number of simultaneous 
			% stimulations depends on the number of modules installed.
			% Format: 	cerestim_object.endGroup()
            
            if nargout
                [x] = stimmex('endofgroup', this.objectHandle, varargin{:});
            else
                stimmex('endofgroup', this.objectHandle, varargin{:});
            end
        end       
        
        function x = autoStim(this, varargin)
            % Defines a stimulus to an electrode in a stimulation script
            % This command can be used as many times as needed so long as the total
			% number of commands does not exceed 128. It should also be used within
			% 'begofgroup' and 'endofgroup' commands to allow for simultaneous stimulations.
			% Format: 	cerestim_object.autoStim(electrode, waveform)
			% Inputs:
			%	electrode:	The electrode that should be stimulated (1-96)
			%	waveform:	The stimulation waveform to use (1-15)
            
            if nargout
                [x] = stimmex('autostim', this.objectHandle, varargin{:});
            else
                stimmex('autostim', this.objectHandle, varargin{:});
            end
        end       
        
        function x = wait(this, varargin)
            % Tells the CereStim 96 to wait before executing the next command within a stimulation script.
            % The maximum period of time to wait is 65,535 milliseconds
			% Format: 	cerestim_object.wait(millisecods)
			% Inputs:
			%	milliseconds: The number of milliseconds to wait before executing the next command
            
            if nargout
                [x] = stimmex('wait', this.objectHandle, varargin{:});
            else
                stimmex('wait', this.objectHandle, varargin{:});
            end
        end       
        
        function x = play(this, varargin)
            % Tells the CereStim 96 the number of times that it should run a stimulation script
            % A zero passed in will tell it to run indefinately until it is either stopped or
			% paused by the user. Other values include between 1 and 65,535 repetitions. Can not
			% be called during a 'begofseq' and 'endofseq' command call.
			% Format: 	cerestim_object.play(repetition)
			% Inputs:
			%	repetition: Number of times to execute the stimulation script.
            
            if nargout
                [x] = stimmex('play', this.objectHandle, varargin{:});
            else
                stimmex('play', this.objectHandle, varargin{:});
            end
        end       
        
        function x = stop(this, varargin)
            % Stops the currently running stimulation script and resets it
            % so when played again it will begin from the first command. 
            % It can only be called while the stimulator has a status of 
            % stimulating or paused.
			% Format: 	cerestim_object.stop()
            
            if nargout
                [x] = stimmex('stop', this.objectHandle, varargin{:});
            else
                stimmex('stop', this.objectHandle, varargin{:});
            end
        end       
        
        function x = pause(this, varargin)
            % Pauses the currently running stimulation script 
            % and keeps track of the next command that needs to be executed 
            % so if it receives a play command it can pick up where it left off.
			% Format: 	cerestim_object.pause()
            
            if nargout
                [x] = stimmex('pause', this.objectHandle, varargin{:});
            else
                stimmex('pause', this.objectHandle, varargin{:});
            end
        end 
        
        function x = maxOutputVoltage(this, varargin)
            % Limits the maximum output voltage that can be delivered during stimulation and allows reading the output compliance voltage from the stimulator
            % Format:	x = cerestim_object.maxOutputVoltage()
			%			x = cerestim_object.maxOutputVoltage(voltage)
			% Inputs:
			%	voltage: The voltage level that is being set when writing to the stimulator
			%			 chosen from the following list:
			%
			%		voltage level		output (V)
			%			7					4.7
			%			8					5.3
			%			9					5.9
			%			10					6.5
			%			11					7.1
			%			12					7.7
			%			13					8.3
			%			14					8.9
			%			15					9.5
			%
			% When used with no inputs it will read the currently set value in the stimulator.
			% Outputs:
			%	x:		Voltage level in millivolts
            
            if nargout
                [x] = stimmex('maxoutputv', this.objectHandle, varargin{:});
            else
                stimmex('maxoutputv', this.objectHandle, varargin{:});
            end
        end 
        
        function x = deviceInfo(this, varargin)
            % Returns all the information about the CereStim 96 that is connected to
            % Format: 	x = cerestim_object.deviceInfo()
			% Outputs:
			%	x: A struct containing the serial number, the firmware version that the
			%	   motherboard is using, the protocol version that the motherboards is using
			%	   with the current modules, the status of the modules and the firmware version
			%	   that the modules are using.
            
            if nargout
                [x] = stimmex('readdevinfo', this.objectHandle, varargin{:});
            else
                stimmex('readdevinfo', this.objectHandle, varargin{:});
            end
        end 
        
        function x = enableModule(this, varargin)
            % Enables modules for stimulation
            % Format: 	cerestim_object.enableModule(modules)
			% Inputs:
			%	modules: An array with the module numbers to be enabled (1-16)
            
            if nargout
                [x] = stimmex('enablemodule', this.objectHandle, varargin{:});
            else
                stimmex('enablemodule', this.objectHandle, varargin{:});
            end
            
        end 
        
        function x = disableModule(this, varargin)
            % Disables modules that are installed in the CereStim
            % Format: cerestim_object.disableModule(modules)
			% Inputs:
			%	modules: An array with the module numbers to be disabled (1-16)
            
            if nargout
                [x] = stimmex('disablemodule', this.objectHandle, varargin{:});
            else
                stimmex('disablemodule', this.objectHandle, varargin{:});
            end
        end 
        
        function x = setStimPattern(this, varargin)
            % Creates a custom biphasic stimulation waveform
            % Format: 	cerestim_object.setStimPattern(<parameter>, [arg],...)
			% Inputs: All parameters are required to create a waveform.
			%	'waveform' -	The stimulation waveform that is being configured (1-15)
			%	'polarity' -	Polarity of the first phase, 0 (cathodic), 1 (anodic)
			%	'pulses' -		Number of stimulation pulses in the waveform (1-255)
			%	'amp1' -		Amplitude of the first phase in uA
			%	'amp2' -		Amplitude of the second phase in uA
			%	'width1' -		Width of the first phase in uS
			%	'width2' -		Width of the second phase in uS
			%	'interphase' -	Period of time between the first and second phases (53 -65,535 uS)
			%	'frequency' -	Stimulating frequency (4 - 5000 Hz)
            
            if nargout
                [x] = stimmex('confpattern', this.objectHandle, varargin{:});
            else
                stimmex('confpattern', this.objectHandle, varargin{:});
            end
        end 
        
        function x = getStimPattern(this, varargin)
            % Reads the configuration of a specific stimulation waveform
            % Format: 		x = cerestim_object.getStimPattern(waveform)
			% Inputs:
			%	waveform:	The stimulation waveform to read (0-15)
			% Outputs:
			%	x:			A struct containing amplitudes in uA, widths in uS, the frequency in Hz
			%				the number of pulses, the time between phases in uS, and a parameter
			%				indicating if the first phase is anodic (1) or cathodic (0)
            
            if nargout
                [x] = stimmex('readpattern', this.objectHandle, varargin{:});
            else
                stimmex('readpattern', this.objectHandle, varargin{:});
            end
        end 
        
        function x = getSequenceStatus(this, varargin)
            % Reads what state the stimulator is in
            % It can be called anytime and does not interrupt other functions from executing
			% Format:	x = cerestim_object.getSequenceStatus()
			% Outputs:
			%	x:		Status of the stimulator
			% 
			% 		status code			stimulator
			%			0				stopped
			%			1				paused
			%			2				playing
			%			3				writing
			%			4				waiting for trigger
            
            if nargout
                [x] = stimmex('readseqstatus', this.objectHandle, varargin{:});
            else
                stimmex('readseqstatus', this.objectHandle, varargin{:});
            end
        end 
        
        function x = stimulusMaxValue(this, varargin)
            % Sets upper limits for stimulation parameters and reads current limits
            % Format:	x = cerestim_object.stimulusMaxValue()
			%			x = cerestim_object.stimulusMaxValue(voltage, amplitude, phaseCharge, frequency)
			%			cerestim_object.stimulusMaxValue(voltage, amplitude, phaseCharge, frequency)
			% Inputs:
			%	voltage:		Maximum compliance voltage
			%	amplitude:		Maximum amplitude to be used in stimulation
			%	phaseCharge:	Maximum charge per phase (charge = amplitude*width)
			%	frequency:		Maximum stimulation frequency
			% 
			% When no inputs are provided the current limits are read and returned
			% Outputs:
			%	x:				A struct containing the information described under Inputs
            
            if nargout
                [x] = stimmex('stimmaxvalue', this.objectHandle, varargin{:});
            else
                stimmex('stimmaxvalue', this.objectHandle, varargin{:});
            end
        end 
        
        function x = groupStimulus(this, varargin)
            % Creates stimulation parameters in advance to perform simultaneous stimulations
            % based on different electrodes and configured waveforms.
			% Format: 	cerestim_object.groupStimulus(beginSeq, play, times, number, electrode, pattern)
			% Inputs:
			%	beginSeq:		Boolean expression to signal the beginning of a sequence
			%	play:			Boolean expression to signal the beginning of stimulation after this call
			%	times:			Number of times to play stimulation
			%	number:			Number of stimuli that will occur simultaneously
			%	electrode:		Array of 16 elements (as number of modules) containing the electrode
			% 					number to be stimulated. Use zero to avoid module
			%	pattern:		Array of 16 elements (as number of modules) containing the configuration
			%					pattern (waveform) to use with the corresponding channel
            
            if nargout
                [x] = stimmex('groupstim', this.objectHandle, varargin{:});
            else
                stimmex('groupstim', this.objectHandle, varargin{:});
            end
        end 
        
        function x = trigger(this, varargin)
            % Sets the stimulator on trigger mode
            % Format: 	cerestim_object.trigger(edge)
			% Inputs:
			%	edge:	Type of digital event to trigger stimulation
			% 
			%		edge value		type
			%			0			trigger mode disabled
			%			1			rising (low to high)
			%			2			falling (high to low)
			%			3			any transition
            
            if nargout
                [x] = stimmex('triggerstim', this.objectHandle, varargin{:});
            else
                stimmex('triggerstim', this.objectHandle, varargin{:});
            end
        end 
        
        function x = disableTrigger(this, varargin)
            % Disables trigger mode
            % Format: 	cerestim_object.disableTrigger()
            
            if nargout
                [x] = stimmex('stoptrigger', this.objectHandle, varargin{:});
            else
                stimmex('stoptrigger', this.objectHandle, varargin{:});
            end
        end 
        
        function x = updateMap(this, varargin)
            % Maps the connection of each channel to its corresponding electrode number
            % Format: 	cerestim_object.updateMap(bankA, bankB, bankC)
			% Inputs:
			%	bankA:	Array of 32 elements where the index represents the channel (1-32)
			%			and the value at each position is the actual electrode number
			%	bankB:	Array of 32 elements where the index represents the channel (33-64)
			%			and the value at each position is the actual electrode number
			%	bankC:	Array of 32 elements where the index represents the channel (65-96)
			%			and the value at each position is the actual electrode number
            
            if nargout
                [x] = stimmex('updatemap', this.objectHandle, varargin{:});
            else
                stimmex('updatemap', this.objectHandle, varargin{:});
            end
        end 
        
        function x = testElectrodes(this, varargin)
            % Returns the impedance of the electrodes at 1kHz
            % and the voltage measured during stimulation with a known waveform 
            % at five locations. This is a diagnostic tool to identify bad channels
			% Format:	x = cerestim_object.testElectrodes()
			% Outputs:
			% 	x:		A struct containing the estimated impedance for each electrode and
			%			a 2D array with 5 voltage measurements in millivolts for each electrode
            
            if nargout
                [x] = stimmex('testelec', this.objectHandle, varargin{:});
            else
                stimmex('testelec', this.objectHandle, varargin{:});
            end
        end 
        
        function x = testModules(this, varargin)
            % Reports the status of each module and the voltage measured
			% during stimulation with a known stimulus to a known load at five locations.
			% This serves as a diagnostic tool to identify bad output voltage levels
			% Format:	x = cerestim_object.testModules()
			% Outputs:
			%	x:		A struct containing the status of each module (see table below) and
			%			a 2D array with 5 voltage measurements in millivolts for each module
			% 
			%			module status value		status
			%					0				unavailable
			%					1				enabled
			%					2				disabled
			%					3				normal voltage levels
			%					4				voltage levels below normal
            
            if nargout
                [x] = stimmex('testmodules', this.objectHandle, varargin{:});
            else
                stimmex('testmodules', this.objectHandle, varargin{:});
            end
        end
        
        function x = getHardwareValues(this, varargin)
            % Reads the hardware values that are set in the stimulator
            % The read values are: max phase amplitude (uA), max charge (pC), 
            % max interphase (uS), max compliance voltage, max frequency (Hz), minimum
			% compliance voltage, minimum frequency (Hz), number of modules 
            % installed, max phase width (uS)
			% Format: 	x = cerestim_object.getHardwareValues()
			% Outputs:
			%	x:		A struct containing all read hardware values
            
            if nargout
                [x] = stimmex('readhardval', this.objectHandle, varargin{:});
            else
                stimmex('readhardval', this.objectHandle, varargin{:});
            end
            
        end
        
        function x = disableStimulus(this, varargin)
            % Disables a stimulation waveform 
            % Format: 		cerestim_object.disableStimulus(waveform)
			% Inputs:
			%	waveform:	A scalar containing a waveform ID (0-15) to be disabled
            
            if nargout
                [x] = stimmex('disablestim', this.objectHandle, varargin{:});
            else
                stimmex('disablestim', this.objectHandle, varargin{:});
            end
            
        end
        
        function x = isConnected(this, varargin)
            % Tests whether the API is connected to a physical CereStim 96 device
            % Format:	x = cerestim_object.isConnected()
			% Outputs:
			%	x:		A logical value indicating whether connected (1) or not (0)
            
            if nargout
                [x] = stimmex('isconnected', this.objectHandle, varargin{:});
            else
                stimmex('isconnected', this.objectHandle, varargin{:});
            end
            
        end
        
        function x = getInterface(this, varargin)
            % Checks what interface type is being used for the connection to the CereStim 96
            % Format:	x = cerestim_object.getInterface()
			% Outputs:
			%	x:		Type of interface used. Possible values are 0 (Default) or 1 (USB)
            
            if nargout
                [x] = stimmex('interface', this.objectHandle, varargin{:});
            else
                stimmex('interface', this.objectHandle, varargin{:});
            end
            
        end
        
        function [x,y] = getMinMaxAmplitude(this, varargin)
            % Returns the min and max amplitudes that are allowed for stimulation 
            % Format:	[x,y] = cerestim_object.getMinMaxAmplitude()
			% Outputs:
			%	x:		The minimum amplitude allowed
			%	y:		The maximum amplitude allowed
            
            if nargout
                [x,y] = stimmex('minmaxamp', this.objectHandle, varargin{:});
            else
                stimmex('minmaxamp', this.objectHandle, varargin{:});
            end
            
        end
        
        function x = usbAddress(this, varargin)
            % Returns the USB address of the connected device
            % Format:	x = cerestim_object.usbAddress()
			% Outputs:
			%	x:		The USB address that the stimulator is attached to
            
            if nargout
                [x] = stimmex('usb', this.objectHandle, varargin{:});
            else
                stimmex('usb', this.objectHandle, varargin{:});
            end
            
        end
        
        function x = isSafetyDisabled(this, varargin)
            % Tests whether the safety limits in the CereStim 96 firmware are disabled
            % Use only to test hardware.
			% Format:	x = cerestim_object.isSafetyDisabled()
			% Outputs:
			%	x:		A logical value indicating whether safety limits are disabled (1) or not (0)
            
            if nargout
                [x] = stimmex('safetydisabled', this.objectHandle, varargin{:});
            else
                stimmex('safetydisabled', this.objectHandle, varargin{:});
            end
            
        end
        
        function x = isLocked(this, varargin)
            % Tests whether the CereStim 96 device is locked
            % If the detected number of current modules doesn't match the hardware
			% configuration or if the hardware configuration is not setup, the device
			% will be locked down preventing any stimulation from occuring
			% Format:	x = cerestim_object.isLocked()
			% Outputs:
			%	x:		A logical value indicating whether locked (1) or not (0)
            
            if nargout
                [x] = stimmex('devicelocked', this.objectHandle, varargin{:});
            else
                stimmex('devicelocked', this.objectHandle, varargin{:});
            end
        end
        
     
    end
end