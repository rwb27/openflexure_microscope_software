from __future__ import print_function
from .. import microscope
import picamera.array
import picamera
import numpy as np
import sys
import time

def lens_shading_correction_from_rgb(rgb_array, binsize=64):
    """Calculate a correction to a lens shading table from an RGB image.
    
    Returns:
        a floating-point table of gains that should multiply the current
        lens shading table.
    """
    full_resolution = rgb_array.shape[:2]
    table_resolution = [(r // binsize) + 1 for r in full_resolution]
    lens_shading = np.zeros([4] + table_resolution, dtype=np.float)
    
    for i in range(3):
        # We simplify life by dealing with only one channel at a time.
        image_channel = rgb_array[:,:,i]
        iw, ih = image_channel.shape
        ls_channel = lens_shading[int(i*1.6),:,:] # NB there are *two* green channels
        lw, lh = ls_channel.shape
        # The lens shading table is rounded **up** in size to 1/64th of the size of
        # the image.  Rather than handle edge images separately, I'm just going to
        # pad the image by copying edge pixels, so that it is exactly 32 times the
        # size of the lens shading table (NB 32 not 64 because each channel is only
        # half the size of the full image - remember the Bayer pattern...  This
        # should give results very close to 6by9's solution, albeit considerably 
        # less computationally efficient!
        padded_image_channel = np.pad(image_channel, 
                                      [(0, lw*binsize - iw), (0, lh*binsize - ih)],
                                      mode="edge") # Pad image to the right and bottom
        assert padded_image_channel.shape == (lw*binsize, lh*binsize), "padding problem"
        # Next, fill the shading table (except edge pixels).  Please excuse the
        # for loop - I know it's not fast but this code needn't be!
        box = 3 # We average together a square of this side length for each pixel.
        # NB this isn't quite what 6by9's program does - it averages 3 pixels
        # horizontally, but not vertically.
        for dx in np.arange(box) - box//2:
            for dy in np.arange(box) - box//2:
                ls_channel[:,:] += padded_image_channel[binsize/2+dx::binsize,binsize/2+dy::binsize]
        ls_channel /= box**2
        # Everything is normalised relative to the centre value.  I follow 6by9's
        # example and average the central 64 pixels in each channel.
        ls_channel /= np.mean(image_channel[iw//2-4:iw//2+4, ih//2-4:ih//2+4])
        # NB the central pixel should now be *approximately* 1.0 (may not be exactly
        # due to different averaging widths between the normalisation & shading table)
        # For most sensible lenses I'd expect that 1.0 is the maximum value.
        # NB ls_channel should be a "view" of the whole lens shading array, so we don't
        # need to update the big array here.
    # What we actually want to calculate is the gains needed to compensate for the 
    # lens shading - that's 1/lens_shading_table_float as we currently have it.
    lens_shading[2,...] = lens_shading[1,...] # Duplicate the green channels
    gains = 1.0/lens_shading # 32 is unity gain
    return gains

def validate_and_convert_lst(gains):
    """Given a lens shading gains table (where no gain=1.0), convert to 8-bit."""
    gains = gains.copy()
    gains[gains > 255] = 255 # clip at 255, maximum gain is 255/32
    gains[gains < 32] = 32 # clip at 32, minimum gain is 1 (is this necessary?)
    return gains.astype(np.uint8)

if __name__ == '__main__':
    try:
        output_fname = sys.argv[1]
    except:
        output_fname = "microscope_settings.npz"
    # Start by loading the raw image from the Pi camera.  This creates a ``picamera.PiBayerArray``.
    with picamera.PiCamera() as cam:
        lens_shading_table = np.zeros(cam._lens_shading_table_shape(), dtype=np.uint8) + 32
        max_res = cam.MAX_RESOLUTION
    # Open the microscope and start with flat (i.e. no) lens shading correction.
    with microscope.load_microscope(lens_shading_table=lens_shading_table,
                                    resolution=max_res) as ms:
        ms.camera.start_preview(resolution=(1080*4/3, 1080))
        ms.freeze_camera_settings(wait_before=4)
        ms.camera.shutter_speed /=2
        for i in range(5):
            # Take an RGB (i.e. processed) image, and calculate the change needed in the shading table
            rgb_image = ms.rgb_image(use_video_port=True, resize=(max_res[0]//2, max_res[1]//2))
            incremental_gains = lens_shading_correction_from_rgb(rgb_image, 64//2)
            # Apply this change (actually apply a bit less than the change)
            ms.camera.lens_shading_table = validate_and_convert_lst(incremental_gains**0.2 * lens_shading_table)
            time.sleep(2)
        settings = ms.settings_dict()
        settings['lens_shading_table'] = ms.camera.lens_shading_table

    for k in settings:
        print("{}: {}".format(k, settings[k]))
    np.savez(output_fname, **settings)
    print("Lens shading table written to {}".format(output_fname))

