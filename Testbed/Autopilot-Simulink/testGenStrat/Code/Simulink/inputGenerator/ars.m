function [bestfit,curfit] = ars(Global)
% <algorithm> <Random Search Algorithm>

% This file performs random search in the input search space for input
% generation

    %% Generate initial solution
    initialS = Global.Initialization();

    maxSimulationNum = Global.maxSimNum; %600
    model_name = Global.mlmodel;
    run = Global.run;
    iterations = Global.evaluation;

    p = '../../Results/';
    data_path = strcat(p,func2str(Global.problem),'/');
    replace_dot = strrep(Global.requirement,'.','_');
    disp(string(iterations));
    data_file_location = strcat(data_path,func2str(Global.problem),'_',replace_dot,'_regression_',string(iterations),'_',model_name,'_',string(run),'.csv');
    disp(data_file_location);
    disp('Reading csv file to continue the simulations');
    T = readtable(data_file_location);

    if strcmp(func2str(Global.problem), 'autopilot')
        T.Properties.VariableNames([1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19]) = { ...
            'Fitness', 'Label', 'Type', 'TrainDelta', 'TestDelta', ...
            'AP_Eng', 'HDG_Mode', 'ALT_Mode', 'HDG_Ref', ...
            'TurnK', 'ALT_Ref', 'Pwheel', 'Throttle','alt', 'term','termMin','termMax','Pct','State'...
        };

%         T.Properties.VariableNames([1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29]) = {'Fitness', 'Label','Type','TrainDelta','TestDelta','AP_Eng1','AP_Eng2','AP_Eng3','HDG_Mode1','HDG_Mode2','HDG_Mode3','ALT_Mode1','ALT_Mode2','ALT_Mode3','HDG_Ref1','HDG_Ref2','HDG_Ref3','TurnK1','TurnK2','TurnK3','ALT_Ref1','ALT_Ref2','ALT_Ref3','Pwheel1','Pwheel2','Pwheel3','Throttle1','Throttle2','Throttle3'}; % names of columns
    end
    H = height(T);
    counter = H;

    bestS = initialS;
    bestFitness = Global.Fitness(initialS);
    %% Optimization
    bestfit = zeros(Global.evaluation,1001);  %we added this to see the improvement 
                                           %of the fitness. 
    curfit = zeros(Global.evaluation,1001);
    exectime = zeros(1,Global.evaluation);

    trainingData = [];
    startTime = tic;
    %While the total simulation budget is not reached, generate inputs from
    %the input search space
     while (counter < Global.evaluation)
            disp('Searching for the csv file');
            p = '../../Results/';
            data_path = strcat(p,func2str(Global.problem),'/');
            replace_dot = strrep(Global.requirement,'.','_');
            run = Global.run;
            data_file_location = strcat(data_path,func2str(Global.problem),'_',replace_dot,'_regression_',string(iterations),'_',model_name,'_',string(run),'.csv');
            T = readtable(data_file_location);
            if strcmp(func2str(Global.problem), 'autopilot')

                T.Properties.VariableNames([1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19]) = { ...
                    'Fitness', 'Label', 'Type', 'TrainDelta', 'TestDelta', ...
                    'AP_Eng', 'HDG_Mode', 'ALT_Mode', 'HDG_Ref', ...
                    'TurnK', 'ALT_Ref', 'Pwheel', 'Throttle','alt', 'term','termMin','termMax','Pct','State'...
                };
%                 T.Properties.VariableNames([1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29]) = {'Fitness', 'Label','Type','TrainDelta','TestDelta','AP_Eng1','AP_Eng2','AP_Eng3','HDG_Mode1','HDG_Mode2','HDG_Mode3','ALT_Mode1','ALT_Mode2','ALT_Mode3','HDG_Ref1','HDG_Ref2','HDG_Ref3','TurnK1','TurnK2','TurnK3','ALT_Ref1','ALT_Ref2','ALT_Ref3','Pwheel1','Pwheel2','Pwheel3','Throttle1','Throttle2','Throttle3'}; % names of columns
            end
            H = height(T);
            disp('total no of rows:')
            simCounter = 0;
            
            if H > 1
                idx = T.Type==0;
                simulationData = T(idx,:);
                simCounter = height(simulationData);
            end

            if H == Global.initialSimNum
                initialSimulationTime = toc(startTime);
                save initialSimulationTime;
            end
            
            disp('Number of simulations');
            disp(simCounter)

            if (simCounter > maxSimulationNum) 
                break
            end
            if (H == Global.evaluation)
                break
            end


         runTime = tic;
         newSPrev =   bestS;  

         newS  = Global.Initialization(); 

         newFitness = Global.Fitness(newS);
       
       if newFitness <= bestFitness
           bestS = newS; 
           bestFitness = newFitness;                 
       end
      exectime(1,counter+1)=toc(runTime);
      bestfit(counter+1,:)=bestFitness;
      curfit(counter+1,:)=newFitness;
      counter = counter + 1;
     end

    totalExecutionTime = toc(startTime);
    trainingData(1) = totalExecutionTime;
    timepath = strcat(data_path,'time.csv');
    writematrix(trainingData,timepath,'WriteMode', 'append');
                           
    save fitmat.mat bestfit curfit exectime; 
end