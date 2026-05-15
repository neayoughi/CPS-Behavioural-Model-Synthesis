classdef GLOBAL < handle
    properties
        D;                              % Number of variables
        lower;                          % Lower bound of each decision variable
        upper;                          % Upper bound of each decision variable
        evaluation = 10000;             % Maximum number of evaluations
        localop = 300;             % Maximum number of evaluations
        operator   = @GMutation;         	% Operator function      
        lag = 50;
        law = 47;                       % Maximum law
    end
    properties(SetAccess = private)
        algorithm  = @hc;               % Algorithm function
        problem    = @DTLZ2;            % Problem function
        requirement = 'R1.1';           % Requirement
        gen;                            % Current generation
        maxgen;                         % Maximum generation
        run        = 1;                 % Run No.
        runtime    = 0;                 % Runtime
        result     = {};                % Set of recorded populations
        parameter  = struct();      	% Parameters of functions specified by users
        mlmodel; %
        initialSimNum;
        maxSimNum;
        simulationType
    end
    methods
        %% Constructor
        function obj = GLOBAL(varargin)
            
            proStr = {'D','algorithm','problem','requirement','operator','evaluation','run'};
            if nargin > 0
                % The parameter setting of the environment
                
                IsString = find(cellfun(@ischar,varargin(1:end-1)));
                [~,Loc]  = ismember(varargin(IsString),cellfun(@(S)['-',S],proStr,'UniformOutput',false));
                for i = find(Loc)
                    obj.(varargin{IsString(i)}(2:end)) = varargin{IsString(i)+1};
                end
                % The parameter setting of the algorithm, problem and
                % operator
                MatchString = regexp(varargin(IsString),'^\-.+_parameter$');
                Loc         = cell2mat(cellfun(@(S)~isempty(S),MatchString,'UniformOutput',false));
                for i = find(Loc)
                    obj.parameter.(varargin{IsString(i)}(2:end-10)) = varargin{IsString(i)+1};
                end
                disp(varargin);
                obj.mlmodel = string(varargin(end-4));
                obj.initialSimNum = str2double(string(varargin(end-2)));
                obj.maxSimNum = str2double(string(varargin(end)));
                obj.simulationType = string(varargin(4));
                obj.run = string(varargin(2));
%                 disp('RUn');
%                 disp(obj.run)
%                 disp('simType');
%                 disp(obj.simulationType);
%                 disp('ml');
%                 disp(obj.mlmodel);
%                 disp('initialSim');
%                 disp(obj.initialSimNum);
%                 disp('maxSim');
%                 disp(obj.maxSimNum);
            end
            % Add the folders of the algorithm, problem and operator to the
            % top of the search path
            addpath(fileparts(which(func2str(obj.operator))));
            addpath(fileparts(which(func2str(obj.problem))));
            addpath(fileparts(which(func2str(obj.algorithm))));
%             addpath(fileparts(which(func2str(obj.run))));
            
        end
        %% Start running the algorithm
        function Start(obj)
        %Start - Start running the algorithm
        %
        %   obj.Start() runs the algorithm with the defined setting. This
        %   method of one GLOBAL object can only be invoked once.
        %
        %   Example:
        %       obj.Start()

             try
                 tic;
                 %[bestfit,curfit]=obj.algorithm(obj);
                 obj.algorithm(obj);
             catch err
                 if strcmp(err.identifier,'GLOBAL:Termination')
                     return;
                 else
                     rethrow(err);
                 end
                
             end 
           %  save fitmat.mat bestfit curfit; %moved to the algorithm
           %  files.
        end
        
        function InitialS = Initialization(obj)
            InitialS = obj.problem('init',obj, []);
            disp('Initialized: ');
            display(InitialS);
        end

        function fitValue = Fitness(obj, element)
            fitValue = obj.problem(obj.simulationType,obj, element);
        end
        
        function NewS = Mutation(obj, element)
            NewS = obj.operator(obj, element); 
            disp('Mutated: ');
            display(NewS);
         
        end
        
     
    end
end