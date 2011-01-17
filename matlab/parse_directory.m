function [IX, IA, IB, N, ids] = parse_directory(dir_name, dataset, x)


IX = [];
IA = [];
IB = [];
N = [];
ids = [];

files = dir([dir_name '/*.out']) ;
    

for i = 1:length(files)
    fprintf('parsing file %s\n', files(i).name);
    [IX0, IA0, IB0, N0, ids0] = parse_output([dir_name files(i).name], dataset);
    IX = [IX; IX0];
    IA = [IA; IA0];
    IB = [IB; IB0];
    N = [N; N0];
    ids = unique([ids; ids0]);
end

if length(x) == 1
    x = rand(length(ids), x);
end

save_experiement_data([dir_name 'all.data.mat'], IX, IA, IB, N, ids, dataset, x);
IXho = [];
IAho = [];
IBho = [];
Nho = [];
files = dir([dir_name '/*.out.heldout']);
for i = 1:length(files)
    [IX0, IA0, IB0, N0, ids0] = parse_output([dir_name files(i).name], dataset);
    IXho = [IXho; IX0];
    IAho = [IAho; IA0];
    IBho = [IBho; IB0];
    Nho = [Nho; N0];
end

save_experiement_data([dir_name 'heldout.data.mat'], IXho, IAho, IBho, Nho, ids, dataset, x);

