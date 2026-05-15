% batchPlotAltitude.m
function results = batchPlotAltitude()
%BATCHPLOTALTITUDE Generate altitude vs. time for upward-climb scenarios.
%   results = batchPlotAltitude()
%   - No inputs required.
%   - Calls autopilotModel(X, 'R12.1') for multiple X configurations.
%   - Plots altitude vs. time for each scenario in its own figure.
%   - Returns a struct array `results` with fields:
%       .name, .X, .alt_out, .time

    % Requirement and time vector
    req  = 'R12.1';
    time = (0:0.025:25)';  % 1001×1

    % Define upward-climb scenarios: name and X vector
    scenarios = {
        'Autopilot climb (ALT Ref ramp)', buildX('altref', [7200, 8000, 9000]);
        'Manual throttle climb',           buildX('throttleManual', [1, 1, 1]);
        'Manual pitch+throttle climb',     buildX('manualClimb', [5,5,5], [1,1,1]);
    };

    n = size(scenarios,1);
    results(n) = struct();

    for k = 1:n
        name = scenarios{k,1};
        X    = scenarios{k,2};

        % Call model; autopilotModel returns 5 outputs
        [~, alt_out, ~, ~, ~] = autopilotModel(X, req);

        % Store results
        results(k).name    = name;
        results(k).X       = X;
        results(k).alt_out = alt_out;
        results(k).time    = time;

        % Plot altitude
        figure('Name',name);
        plot(time, alt_out, 'LineWidth',1.5);
        grid on;
        xlabel('Time (s)');
        ylabel('Altitude (ft)');
        title(['Scenario: ' name]);
    end
end

%% Helper function to build X vectors
function X = buildX(type, values, extra)
% BUILDX Construct X for specific climb scenarios.
%   type: 'altref', 'throttleManual', or 'manualClimb'
%   values: for 'altref' and 'manualClimb', values for ALT Ref or pitch wheel
%   extra: for 'manualClimb', the throttle values

    % Initialize zero vector: 8 inputs × 3 segments = 24
    X = zeros(1,8*3);

    switch type
        case 'altref'
            % Autopilot ON + ALT Mode ON + ramped ALT Ref
            X(1:3)   = 1;            % AP Eng on
            X(7:9)   = 1;            % ALT Mode on
            X(16:18) = values;       % ALT Ref segments
        case 'throttleManual'
            % Manual throttle: AP off, ALT Mode off
            X(22:24) = values;       % throttle segments
        case 'manualClimb'
            % Manual climb: AP off, ALT Mode off, pitch + throttle
            pitch = values(:)';      % X(19:21)
            thr   = extra(:)';       % X(22:24)
            X(19:21) = pitch;
            X(22:24) = thr;
        otherwise
            error('Unknown scenario type');
    end
end
