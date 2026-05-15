%This function is used to create a CSV file before initiating test suite
%generation irrespective of the strategy (i.e. SA, RS, LR or RT)
function createCSV(run,simModel,requirement,iteration,mlmodel)

        %Set path where CSV needs to be created. 
        p = '../../Results/';
%         if strcmp(string(iteration),'3500')
        maxIterationNum = iteration;
%         else
%             maxIterationNum = 3500;
%         end
        mlModelName = mlmodel;
        if not(isfolder(strcat(p,simModel)))
            mkdir(strcat(p,simModel))
        end
        if isfolder(strcat(p,simModel))
            if not(isfolder(strcat(p,simModel,'/verify')))
                mkdir(strcat(p,simModel,'/verify'))
            end
        end
        base_path = strcat(p,simModel,'/');
        disp(base_path)
        replace_dot = strrep(requirement,'.','_');
        path = strcat(base_path,simModel,'_',replace_dot,'_regression_',string(maxIterationNum),'_',mlModelName,'_',string(run),'.csv');
        if isfile(path)
            disp(strcat('file exists:', path)); 
        else
     
            if strcmp(simModel,'autopilot')
                cHeader = {'Fitness', 'Label', 'Type', 'TrainDelta', 'TestDelta', ...
                        'AP_Eng', 'HDG_Mode', 'ALT_Mode', 'HDG_Ref', ...
                        'TurnK', 'ALT_Ref', 'Pwheel', 'Throttle','alt','term','termMin','termMax','Pct','State'};

                %cHeader = {'Fitness', 'Label','Type','TrainDelta','TestDelta','AP_Eng1','AP_Eng2','AP_Eng3','HDG_Mode1','HDG_Mode2','HDG_Mode3','ALT_Mode1','ALT_Mode2','ALT_Mode3','HDG_Ref1','HDG_Ref2','HDG_Ref3','TurnK1','TurnK2','TurnK3','ALT_Ref1','ALT_Ref2','ALT_Ref3','Pwheel1','Pwheel2','Pwheel3','Throttle1','Throttle2','Throttle3'};
            end
            commaHeader = [cHeader;repmat({','},1,numel(cHeader))];
            disp(commaHeader);
            commaHeader = commaHeader(:)';
            disp(commaHeader);
            textHeader = cell2mat(commaHeader);
            textHeader = textHeader(1:end-1);
            disp(textHeader);
            %Creating an empty CSV file with the columns specified above
            fid = fopen(path,'wt');
            fprintf(fid,'%s\n',textHeader);
            fclose(fid);  
        end


        %Code similar to above. Used to create verify file to evaluate the
        %accuracy of surrogate technique. 

        verify_path = strcat(base_path,'verify/');
        verify_file = strcat(verify_path,simModel,'_',replace_dot,'_verify_',string(maxIterationNum),'_',mlModelName,'_',string(run),'.csv');
        
        if isfile(verify_file)
            disp(strcat('file exists:', verify_file));
            
        else
            %Define the columns for the CSV file
            if strcmp(simModel,'autopilot')
                cHeader = {'PredictedFitness', 'PredictedLabel', 'SimulatedFitness', 'SimulatedLabel', ...
                           'Same/Different', 'Index', ...
                           'AP_Eng', 'HDG_Mode', 'ALT_Mode', 'HDG_Ref', ...
                           'TurnK', 'ALT_Ref', 'Pwheel', 'Throttle','alt','term','termMin','termMax','Pct','State'};

                %                 cHeader = {'PredictedFitness','PredictedLabel','SimulatedFitness','SimulatedLabel','Same/Different','Index','AP_Eng1','AP_Eng2','AP_Eng3','HDG_Mode1','HDG_Mode2','HDG_Mode3','ALT_Mode1','ALT_Mode2','ALT_Mode3','HDG_Ref1','HDG_Ref2','HDG_Ref3','TurnK1','TurnK2','TurnK3','ALT_Ref1','ALT_Ref2','ALT_Ref3','Pwheel1','Pwheel2','Pwheel3','Throttle1','Throttle2','Throttle3'};
            end
            commaHeader = [cHeader;repmat({','},1,numel(cHeader))]; 
            commaHeader = commaHeader(:)';
            textHeader = cell2mat(commaHeader);
            textHeader = textHeader(1:end-1);
            %Create an empty CSV file
            fid = fopen(verify_file,'wt');
            fprintf(fid,'%s\n',textHeader);            
            fclose(fid);  
        end