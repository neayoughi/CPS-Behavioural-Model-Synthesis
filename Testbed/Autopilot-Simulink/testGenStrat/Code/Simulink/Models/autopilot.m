function varargout = autopilot(Operation,Global,element) 
    switch Operation
        case 'init'
            if strcmp(Global.requirement,"R12.1")
                urangeTurnKmax      = 45;
                urangeTurnKmin      = 0;
                urangeHDGRefmax     = 180;
                urangeHDGRefmin     = -180;
                urangeALTRefmin     = 7260;
                urangeALTRefmax     = 7260;

                urangePitchWmax     = 30;
                urangePitchWmin     = -30;

                urangethrottlemin   = 0;
                urangethrottlemax   = 1;

                Global.D        = 24;
                Global.lower    = [zeros(1,9), ...
                                   urangeHDGRefmin*ones(1,3), ...
                                   urangeTurnKmin*ones(1,3), ...
                                   urangeALTRefmin*ones(1,3), ...
                                   urangePitchWmin*ones(1,3), ...
                                   urangethrottlemin*ones(1,3)];
                Global.upper    = [ones(1,9), ...
                                   urangeHDGRefmax*ones(1,3), ...
                                   urangeTurnKmax*ones(1,3), ...
                                   urangeALTRefmax*ones(1,3), ...
                                   urangePitchWmax*ones(1,3), ...
                                   urangethrottlemax*ones(1,3)];
                Global.operator = @AutopilotMutation;
                Global.localop  = 35;
                Global.law      = 47;

                PopDec = rand(1,Global.D);

                PopDec(1:2) = 1;
                PopDec(3)   = 0;
                PopDec(4:6) = 0;
                PopDec(7:9) = 0;

                for i = 10:12
                    PopDec(i) = urangeHDGRefmin + PopDec(i) * (urangeHDGRefmax - urangeHDGRefmin);
                end
                for i = 13:15
                    PopDec(i) = urangeTurnKmin + PopDec(i) * (urangeTurnKmax - urangeTurnKmin);
                end
                for i = 16:18
                    PopDec(i) = urangeALTRefmin + PopDec(i) * (urangeALTRefmax - urangeALTRefmin);
                end
                for i = 19:21
                    PopDec(i) = urangePitchWmin + PopDec(i) * (urangePitchWmax - urangePitchWmin);
                end
                for i = 22:24
                    PopDec(i) = urangethrottlemin + PopDec(i) * (urangethrottlemax - urangethrottlemin);
                end

                varargout = {PopDec};

            end

        case 'random'
            disp('Called Random Search');
            [PopObj, ~] = randomSearch(Global.run, element, Global.problem, Global.requirement, Global.evaluation);
            varargout = {PopObj};

    end
end

