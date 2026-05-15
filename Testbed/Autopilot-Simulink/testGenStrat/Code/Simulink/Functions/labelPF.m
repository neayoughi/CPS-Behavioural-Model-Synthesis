function label = labelPF(PopObj,high,req)
    %Label data point into B or NB using PopObj

    if (PopObj >= 0)
        label = 1; %B
        disp("pass");
    else
        label = 0; %NB
        disp("fail");
    end

end