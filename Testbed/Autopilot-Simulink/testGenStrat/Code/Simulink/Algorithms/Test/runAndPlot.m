function runAndPlot()
% runAndPlot  Build forced‐climb input, simulate, and plot alt & elevator‐cmd.

    % 1) Build X
    X = zeros(1,24);
    X(1:3)    = 1;    % AP on
    X(4:6)    = 0;    % HDG off
    X(7:9)    = 1;    % ALT hold on
    X(16:18) = 8000;  % ALT_Ref > start
    X(19:21)=  +30; %pitchwheel
    X(22:24) = 1;     % 100% throttle

    % 2) Load model
    mdl = 'do178b_dhc2_rev_new';
    load_system(mdl);

    % 3) Simulate with logging
    simOut = sim(mdl, ...
        'ReturnWorkspaceOutputs','on', ...
        'SaveFormat','Dataset', ...
        'SignalLogging','on', ...
        'SignalLoggingName','logsout', ...
        'StopTime','25');

    % 4) Extract dataset
    ds = simOut.logsout;

    % 4a) Debug: list what's in ds
    names = ds.getElementNames();
    fprintf('Logged signals:\n');
    disp(names);

    % 5) Grab the correct element name for altitude:
    %     Change 'alt' below if your model used a different name.
    altSig = ds.getElement('alt').Values;       % e.g. 'alt'
    ailSig = ds.getElement('AilCmd').Values;    % elevator command

    % 6) Plot
    t = altSig.Time;
    figure('Name','Altitude & Elevator Cmd');
    subplot(2,1,1)
      plot(t, altSig.Data,'LineWidth',1.5)
      ylabel('Altitude (ft)'); title('Altitude vs Time')
      grid on

    subplot(2,1,2)
      plot(t, ailSig.Data,'LineWidth',1.5)
      ylabel('Elevator Cmd'); xlabel('Time (s)')
      grid on

    % 7) Print start/end
    fprintf('Initial alt = %.1f ft\n', altSig.Data(1));
    fprintf('Final   alt = %.1f ft\n', altSig.Data(end));
end
