function export_vsi_dims(vsi_paths, output_path)
    for i = 1:length(vsi_paths)
        output_struct(i) = struct( ...
            'vsi_path', vsi_paths{i}, ...
            'pad_size', get_margin_size(downsampleToAtlasScale(get_vsi_size(vsi_paths{i}))) ...
        );
    end

    savejson('', output_struct, output_path)


function vsi_size = get_vsi_size(vsi_path)
    reader = bfGetReader(vsi_path);
    rows = reader.getSizeY();
    cols = reader.getSizeX();
    vsi_size = [rows, cols];

function downsampled_size = downsampleToAtlasScale(im_size)
    disp('Downsizing image.....')
    vsiPixelSize = .64497; % in um
    atlasPixelSize = 25; % in um
    atlas_scale = vsiPixelSize/atlasPixelSize;
    downsampled_size = im_size * atlas_scale;

function margin_size = get_margin_size(im_size)
    disp('Padding to atlas size.....')
    atlasSize = [320, 456];
    margin_size = ceil((atlasSize - im_size)./2);
    margin_size(margin_size < 0) = 0; % Remove 0s if im is larger than atlasSize in either dimension
