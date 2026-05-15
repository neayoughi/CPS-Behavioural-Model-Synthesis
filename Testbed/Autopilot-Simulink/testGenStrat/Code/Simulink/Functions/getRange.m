function high = getBoundaryRange(simModel, req)
    switch simModel
        case 'autopilot'
            if strcmp(req,'R12_1')
                low = 0;
                high = 0;
            end
    end
end