function [PopObj, alt, termVec, termMin, termMax] = callSimulator(X,req,simModel)
    % pre-define in case some models don’t return them
    alt     = [];
    termVec = [];
    termMin = [];
    termMax = [];

    switch simModel
        case 'autopilot'
            %PopObj=autopilotModel(X,req);
            [PopObj, alt, termVec, termMin, termMax] = autopilotModel(X,req);
    end
end