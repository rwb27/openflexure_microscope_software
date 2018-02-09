from __future__ import print_function
from .. import microscope
import picamera.array
import picamera
import numpy as np
import sys

if __name__ == '__main__':
    try:
        output_fname = sys.argv[1]
    except:
        output_fname = "microscope_settings.npz"
    # Start by loading the raw image from the Pi camera.  This creates a ``picamera.PiBayerArray``.
    with picamera.PiCamera() as cam:
        lens_shading_table = np.zeros(cam._lens_shading_table_shape(), dtype=np.uint8) + 32
        max_res = cam.MAX_RESOLUTION
    with microscope.load_microscope(lens_shading_table=lens_shading_table,
                                    resolution=max_res) as ms:
        ms.camera.start_preview(resolution=(1080*4/3, 1080))
        ms.freeze_camera_settings()
        pi_bayer_array = picamera.array.PiBayerArray(ms.camera)
        ms.camera.capture(pi_bayer_array, format="jpeg", bayer=True)
        settings = ms.settings_dict()
        bayer_array_array = pi_bayer_array.array
    for k in settings:
        print("{}: {}".format(k, settings[k]))

    # The bayer data is split into colour channels - I sum over these 
    # to avoid confusion and get closer to an array that represents what
    # the camera actually measures, i.e. one number = one photodetector.
    bayer_data = bayer_array_array.sum(axis=2) #16-bit bayer data
    # We need to figure out which pixels to assign to which channels
    bayer_pattern = [(i//2, i%2) for i in range(4)]
    full_resolution = bayer_data.shape
    table_resolution = [(r // 64) + 1 for r in full_resolution]
    lens_shading = np.zeros([4] + table_resolution, dtype=np.float)
    
    for i, offset in enumerate(bayer_pattern):
        # We simplify life by dealing with only one channel at a time.
        image_channel = bayer_data[offset[0]::2, offset[1]::2]
        iw, ih = image_channel.shape
        ls_channel = lens_shading[i,:,:]
        lw, lh = ls_channel.shape
        # The lens shading table is rounded **up** in size to 1/64th of the size of
        # the image.  Rather than handle edge images separately, I'm just going to
        # pad the image by copying edge pixels, so that it is exactly 32 times the
        # size of the lens shading table (NB 32 not 64 because each channel is only
        # half the size of the full image - remember the Bayer pattern...  This
        # should give results very close to 6by9's solution, albeit considerably 
        # less computationally efficient!
        padded_image_channel = np.pad(image_channel, 
                                      [(0, lw*32 - iw), (0, lh*32 - ih)],
                                      mode="edge") # Pad image to the right and bottom
        print("Channel shape: {}x{}, shading table shape: {}x{}, after padding {}".format(iw,ih,lw*32,lh*32,padded_image_channel.shape))
        # Next, fill the shading table (except edge pixels).  Please excuse the
        # for loop - I know it's not fast but this code needn't be!
        box = 3 # We average together a square of this side length for each pixel.
        # NB this isn't quite what 6by9's program does - it averages 3 pixels
        # horizontally, but not vertically.
        for dx in np.arange(box) - box//2:
            for dy in np.arange(box) - box//2:
                ls_channel[:,:] += padded_image_channel[16+dx::32,16+dy::32]
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
    gains = 32.0/lens_shading # 32 is unity gain
    gains[gains > 255] = 255 # clip at 255, maximum gain is 255/32
    gains[gains < 32] = 32 # clip at 32, minimum gain is 1 (is this necessary?)
    lens_shading_table = gains.astype(np.uint8)
    # Finally, save the results in a numpy zip file.
    settings['lens_shading_table'] = lens_shading_table
    np.savez(output_fname, **settings)
    print("Lens shading table written to {}".format(output_fname))
    print("Double-checking settings saved OK")
    npz = np.load(output_fname)
    for k in npz:
        print("{}: {}".format(k, npz[k]))

