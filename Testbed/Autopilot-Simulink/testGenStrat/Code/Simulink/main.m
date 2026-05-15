function main(varargin)
    cd(fileparts(mfilename('fullpath')));
    addpath(genpath(cd));
    Global = GLOBAL(varargin{:});
    Global.Start();
end

