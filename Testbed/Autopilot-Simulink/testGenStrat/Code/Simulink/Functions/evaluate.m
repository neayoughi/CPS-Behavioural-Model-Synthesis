function metric_result = evaluate(actual, predicted)
    metric_result = mae(actual - predicted);
end