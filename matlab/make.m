mexfiles = {'logistic_deriv.cpp', 'confusion_matrix.cpp', ...
            'model_likelihood.cpp', 'distance_deriv.cpp', ...
            'update_matrix.cpp', 'produce_adaptive.cpp', ...
            'information_gain.cpp', 'predict_using_bank.cpp'}

for i = 1:length(mexfiles)
    mex(mexfiles{i});
end
