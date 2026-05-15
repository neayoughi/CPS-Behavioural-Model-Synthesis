function [Xfitness, alt, termVec, termMin, termMax] = randomSearch( ...
        run, element, problem, req, evaluation)

    % Base directory
    p         = '../../Results/';
    data_path = fullfile(p, func2str(problem));
    replace_dot = strrep(req, '.', '_');
    high      = 0;

    % Ensure folder
    if ~isfolder(data_path)
        mkdir(data_path);
    end

    % 1) Run sim
    X = element;
    [FitnessVec, alt, termVec, termMin, termMax] = ...
        callSimulator(X, req, func2str(problem));
    label = labelPF(FitnessVec(1), high, replace_dot);

    % 2) Check length
    if numel(X) ~= 24
        error('Expected 24 elements, got %d.', numel(X));
    end

    % 3) Expand 3×8 → 1000×8
    X = reshape(X, [3, 8]);
    X_repeated = [
        repmat(X(1,:), 333, 1);
        repmat(X(2,:), 333, 1);
        repmat(X(3,:), 334, 1)
    ];

    % 4) Prepare output array: 17 original + 2 new = 19 cols
    num_rows = 1000;
    rows     = cell(num_rows, 19);

    for i = 1:num_rows
        % --- original 17 columns ---
        rows{i,1}  = FitnessVec(i);
        rows{i,2}  = label;
        rows{i,3}  = 0;      % Type
        rows{i,4}  = 0;      % TrainDelta
        rows{i,5}  = 0;      % TestDelta
        for j = 1:8
            rows{i,5+j} = X_repeated(i,j);
        end
        rows{i,14} = alt(i);
        rows{i,15} = termVec(i);
        rows{i,16} = termMin(i);
        rows{i,17} = termMax(i);

        % --- leave Pct and State empty ---
        rows{i,18} = "";
        rows{i,19} = "";
    end

    % 5) Write table
    headers = { ...
      'Fitness','Label','Type','TrainDelta','TestDelta', ...
      'AP_Eng','HDG_Mode','ALT_Mode','HDG_Ref','TurnK', ...
      'ALT_Ref','Pwheel','Throttle','alt', ...
      'term','termMin','termMax', ...
      'Pct','State'};

    T = cell2table(rows, 'VariableNames', headers);
    base_file = fullfile(data_path, ...
      sprintf('%s_%s_regression_%s_value_%s_set', ...
              func2str(problem), replace_dot, string(evaluation), string(run)));
    k = 1;
    while isfile(sprintf('%s%d.csv', base_file, k))
        k = k + 1;
    end
    path = sprintf('%s%d.csv', base_file, k);
    writetable(T, path);
    fprintf('Wrote %d-row set to: %s\n', num_rows, path);

    % 6) Return fitness
    Xfitness = FitnessVec;
end
