function reliable = reliability_check(predictedFitness, delta,high, req)

        isreliable = false;

        disp('predicted fitness:');
        disp(predictedFitness);
        disp('delta');
        disp(delta);
%         disp('low');
%         disp(low);
        disp('high');
        disp(high);

        if (predictedFitness + delta >= 0) && (predictedFitness - delta >= 0) && (predictedFitness >= 0)
            isreliable = true;
        end
        if (predictedFitness + delta < 0) && (predictedFitness - delta < 0) && (predictedFitness < 0)
            isreliable = true;
        end

        if (isreliable)
            reliable = true;
            disp('prediction is reliable')
        else
            disp('prediction not reliable');
            reliable = false;
        end
end