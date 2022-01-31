#@ File (label="Select a directory", style="directory") dirname
#@ Integer (label="Resolution level", value=2) series
#@ String (visibility=MESSAGE, value="Resolution level 1 = full res; 2 = half the pixels per dimension ...") msg1
#@ String (label="File type", value=".ims") filetype

function convert_img_to_h5(in_file, out_file, series) {

    run("Bio-Formats Importer", "open=" + in_file + " color_mode=Default rois_import=[ROI manager] view=Hyperstack stack_order=XYCZT series_" + series);
    title = getTitle();
    run("Export HDF5", "select=" + out_file +  " datasetname=data compressionlevel=0 input=[" + title + "]");
    close(title);
};

all_files = getFileList(dirname);

for (i=0; i<all_files.length; i++) {
    in_file = dirname + "/" + all_files[i];
    if (endsWith(in_file, filetype)) {
        print("Converting " + in_file);
        out_file = dirname + "/" + File.getNameWithoutExtension(in_file) + ".h5";
        print("Converting: " + in_file +  " --> " + out_file);
        if (File.exists(out_file) != 1) {
            convert_img_to_h5(in_file, out_file, series);
            print("  - done");

        } else {
            print("  - output exists already, skipping...");
        }
    }
}

