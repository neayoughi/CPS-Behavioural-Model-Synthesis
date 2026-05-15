function [FR, alt_out, termVec, termMin, termMax] = autopilotModel(X,req)

    t = 0:0.025:25; %%%%
    if strcmp(req,'R12.1')
        nbrInputs = 8;
    else
        nbrInputs = 7;
    end

    TimeSteps = 1001; %%%%
    apin.time = t';
    
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%    Open Models 
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%   
    curPath=fileparts(which('autopilot.m'));
    addpath(curPath);
    modelpath = strrep(curPath,'Code/Simulink/Models','Benchmark/Simulink Models/autopilot/aprevised/');
    addpath(modelpath);
    if strcmp(req,'R12.1')
        models = {strcat(modelpath,'roll_ap_rev.slx'),strcat(modelpath,'yaw_damper_rev.slx'),strcat(modelpath,'pitch_ap_rev.slx'),strcat(modelpath,'Autopilot_rev.slx'),strcat(modelpath,'AP_Lib_rev.slx'),strcat(modelpath,'Heading_Mode_rev.slx'),strcat(modelpath,'attitude_controller_rev.slx'),strcat(modelpath,'Altitude_Mode_rev.slx'),strcat(modelpath,'do178b_dhc2_rev_new.slx')};
    else
        models = {strcat(modelpath,'roll_ap_rev.slx'),strcat(modelpath,'yaw_damper_rev.slx'),strcat(modelpath,'pitch_ap_rev.slx'),strcat(modelpath,'Autopilot_rev.slx'),strcat(modelpath,'AP_Lib_rev.slx'),strcat(modelpath,'Heading_Mode_rev.slx'),strcat(modelpath,'attitude_controller_rev.slx'),strcat(modelpath,'Altitude_Mode_rev.slx'),strcat(modelpath,'do178b_dhc2_rev.slx')};
    end
    open_system(models);
       % load data file
    save apin_ap.mat apin;
    load('apin_ap.mat', 'apin');
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%    Signals building 
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
    for j = 1:nbrInputs
        apin.signals(j).values = zeros(TimeSteps,1);
        apin.signals(j).dimensions =  1;
    end

        d=1;
        for j = 1:nbrInputs
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%    Specific for performance requirement  
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%            
%             a1(1:100) = X(1,d)*ones(1,100);
%             a1(101:200) = X(1,d+1)*ones(1,100);
%             a1(201:1001) = X(1,d+2)*ones(1,801);
%             apin.signals(j).values = a1';
%             d=d+3;
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%    Else
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
            i=1;
            while i <= 901
                a=X(1,d);
                a1(i:i+332) = a*ones(1,333);
                i = i + 333;
                d = d+1;
            end
            a1(1,1001)= a; 
            apin.signals(j).values = a1';
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
        end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%    Scenarios: Fixing inputs 
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%         apin.signals(1).values = ones(TimeSteps,1);
%         apin.signals(2).values = zeros(TimeSteps,1);
%         apin.signals(3).values = zeros(TimeSteps,1);
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

        % solving the prob of unrecognized inputs
        if strcmp(req,'R12.1')
            hws = get_param('do178b_dhc2_rev_new', 'modelworkspace');
        else
            hws = get_param('do178b_dhc2_rev', 'modelworkspace');
        end
        list = whos;       
        N = length(list);
        for  i = 1:N
            hws.assignin(list(i).name,eval(list(i).name));
        end
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%    Run Simulation 
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
        if strcmp(req,'R12.1')
            simOut = sim(fullfile(modelpath,'do178b_dhc2_rev_new.slx'),'ReturnWorkspaceOutputs','on','SaveOutput','on','OutputSaveName','apsOut');
    
        %%%%%%%
            rollOut= simOut.get('apsOut');
            AP_Eng      = apin.signals(1).values;
            HDG_Mode    = apin.signals(2).values;
            ALT_Mode    = apin.signals(3).values;
            HDG_Ref     = apin.signals(4).values;
            TurnK       = apin.signals(5).values;
            ALT_Ref     = apin.signals(6).values;
            Pwheel      = apin.signals(7).values;
            Throttle    = apin.signals(8).values;
            
            Ail_cmd     = simOut.get('AilCmd');
            inertial    = simOut.get('inert');
            Phi_Ref     = simOut.get('PhiRef');
            isRoll     = simOut.get('isRoll');
            AirDataa     = simOut.get('AirDataa');
            alt = AirDataa.alt.Data;
            tout = apin.time;
        else
            simOut = sim(fullfile(modelpath,'do178b_dhc2_rev.slx'),'ReturnWorkspaceOutputs','on','SaveOutput','on','OutputSaveName','apsOut');
            rollOut= simOut.get('apsOut');
            AP_Eng      = apin.signals(1).values;
            HDG_Mode    = apin.signals(2).values;
            ALT_Mode    = apin.signals(3).values;
            HDG_Ref     = apin.signals(4).values;
            TurnK       = apin.signals(5).values;
            ALT_Ref     = apin.signals(6).values;
            Pwheel      = apin.signals(7).values;

            Ail_cmd     = simOut.get('AilCmd');
            inertial    = simOut.get('inert');
            Phi_Ref     = simOut.get('PhiRef');
            isRoll     = simOut.get('isRoll');
            tout = apin.time;
        end
        
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%    Assumptions 
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%        
        Roll_Mode = zeros(TimeSteps,1);
        for t =1:1001
            if (HDG_Mode(t)==0)&&(ALT_Mode(t)==0)
                Roll_Mode(t) = 1;
            else
                Roll_Mode(t) = 0;
            end 
        end
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
        TkDiff = zeros(1000,1);
        for i = 2:1001
            TkDiff(i) = TurnK(i) - TurnK(i-1);
        end
       % TkDiffMax = max(TkDiff);
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 

        Ft = 1000 * ones(TimeSteps,1); 
        termVec  = nan(1001,1);
        termMin  = nan(1001,1);
        termMax  = nan(1001,1);
        
        switch req
            case 'R12.1'
                [Ft, termVec, termMin, termMax] = ...
                R121Obj(AP_Eng(1:1001), alt(1:1001), ALT_Ref(1:1001));
        end
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        FR=  Ft;
        disp(FR);
        
        alt_out = alt(1:1001);

end

function [R121, termVec, termMin, termMax] = R121Obj(AP_Eng, alt, ALT_Ref)


    n = numel(AP_Eng);

    % ensure ALT_Ref is an Nx1 vector
    if isscalar(ALT_Ref)
        ALT_Ref = repmat(ALT_Ref, n, 1);
    end

    % preallocate
    termVec = nan(n,1);
    termMin = nan(n,1);
    termMax = nan(n,1);
    R121    =  1e6 * ones(n,1);    % default: AP off → +1e6

    % find first time AP engages
    [maxval, startIdx] = max(AP_Eng);
    if maxval == 1
        windowEnd = min(startIdx + 500, n);

        % compute term / suffix-min / suffix-max / R121 in window
        for i = startIdx : windowEnd
            termVec(i)  = alt(i) - ALT_Ref(i) + 0.05;
            suffix      = termVec(i:windowEnd);
            termMin(i)  = min(suffix);
            termMax(i)  = max(suffix);
            R121(i)     = termMax(i);
        end

        % beyond the 500-step horizon, AP still on → –1e6
        if windowEnd < n
            R121(windowEnd+1:end) = -1e6;
        end
    end
end
