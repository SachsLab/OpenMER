%%
addpath('D:\Tools\Neurophys\CereStim\CereStim API');

%%
stimulator = cerestim96();
device_list = stimulator.scanForDevices();
if ~isempty(device_list)
    stimulator.selectDevice(0);
    stimulator.connect();
end

%%
STIM_PARAMS = struct(...
    'an_first', false,... % false for cathodic first
    'p1_width', 100,... % uS
    'p1_amp', 1000,... % uA
    'freq', 130.0052,... % Hz (130.0052)
    'max_dur', 30,...  % seconds
    'ramp_dur', 0,...  % seconds
    'monophasic_like', true,...
    'electrode', 13);  
%%
is_conn = stimulator.isConnected();
if is_conn
    hvals = stimulator.getHardwareValues();
    stimlims = stimulator.stimulusMaxValue();
    [min_amp, max_amp] = stimulator.getMinMaxAmplitude();
    
    % Calculate final waveform.
    full_cycle_us = 1E6 / STIM_PARAMS.freq;
    if STIM_PARAMS.monophasic_like
        min_interphase = 53;
        p2_max_width = full_cycle_us - STIM_PARAMS.p1_width - 2*min_interphase;
        p2_amp = (STIM_PARAMS.p1_width * STIM_PARAMS.p1_amp) / p2_max_width;
        p2_amp = max([p2_amp min_amp]);
        
        p2_width = (STIM_PARAMS.p1_width * STIM_PARAMS.p1_amp) / p2_amp;
        interphase = (full_cycle_us - STIM_PARAMS.p1_width - p2_width) / 2;
    else
        empty_us = full_cycle_us - STIM_PARAMS.p1_width * 2;
        interphase = floor(empty_us / 2);
        p2_width = STIM_PARAMS.p1_width;
        p2_amp = STIM_PARAMS.p1_amp;
    end
    
    % Configure final waveform
    n_final_pulses = ceil(STIM_PARAMS.max_dur * STIM_PARAMS.freq);
    if n_final_pulses > 255
        n_final_stims = ceil(n_final_pulses / 255);
        n_final_pulses = 255;
    else
        n_final_stims = 1;
    end
    stimulator.setStimPattern(...
        'waveform', 15,...
        'polarity', int16(STIM_PARAMS.an_first),...
        'pulses', n_final_pulses,...
        'amp1', STIM_PARAMS.p1_amp,...
        'amp2', p2_amp,...
        'width1', STIM_PARAMS.p1_width,...
        'width2', p2_width,...
        'interphase', interphase,...
        'frequency', STIM_PARAMS.freq);
    
    % TODO: Caclulate ramp
    
    stimulator.beginSequence();
    % TODO: Add ramp stims
    for final_ix = 1:n_final_stims
        stimulator.autoStim(STIM_PARAMS.electrode, 15);
    end
    stimulator.endSequence();
end
%%
stimulator.play(1);
%%
stimulator.stop();
%%
stimulator.disconnect();