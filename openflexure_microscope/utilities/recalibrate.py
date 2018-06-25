from __future__ import print_function
from .. import microscope
import picamera.array
import picamera
import numpy as np
import sys
import time
import matplotlib.pyplot as plt

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
        channel_centre = np.mean(image_channel[iw//2-4:iw//2+4, ih//2-4:ih//2+4])
        ls_channel /= channel_centre
        print("channel {} centre brightness {}".format(i, channel_centre))
        # NB the central pixel should now be *approximately* 1.0 (may not be exactly
        # due to different averaging widths between the normalisation & shading table)
        # For most sensible lenses I'd expect that 1.0 is the maximum value.
        # NB ls_channel should be a "view" of the whole lens shading array, so we don't
        # need to update the big array here.
        print("min {}, max {}".format(ls_channel.min(), ls_channel.max()))
    # What we actually want to calculate is the gains needed to compensate for the 
    # lens shading - that's 1/lens_shading_table_float as we currently have it.
    lens_shading[2,...] = lens_shading[1,...] # Duplicate the green channels
    gains = 1.0/lens_shading # 32 is unity gain
    return gains

def gains_to_lst(gains):
    """Given a lens shading gains table (where no gain=1.0), convert to 8-bit."""
    lst = gains / np.min(gains)*32 # minimum gain is 32 (= unity gain)
    lst[lst > 255] = 255 # clip at 255
    return lst.astype(np.uint8)
    
def generate_lens_shading_table_closed_loop(output_fname="microscope_settings.npz", 
                                            n_iterations=5,
                                            images_to_average=5):
    """Reset the camera's parameters, and recalibrate the lens shading to get unifrom images.
    
    This function requires the microscope to be set up with a blank, uniformly 
    illuminated field of view.  When it runs, it first auto-exposes, then fixes 
    the gains/shutter speed and resets the lens shading correction to a unity
    gain.  Rather than take a single raw image and calibrate from that (as 
    done in the open loop version, which is a more or less direct Python port 
    of 6by9's C code), we do it incrementally.  Each iteration (of a default 5)
    consists of acquiring a processed RGB image, then adjusting the lens shading
    table to make it uniform.  It seems that doing this 3-5 times gives much 
    better results than just doing it once.
    
    At the end, all camera settings are saved into the output file, where they
    can be used to set up a microscope with `load_microscope`.
    """
    print("Regenerating the camera settings, including lens shading.")
    print("This will only work if the camera is looking at something uniform and white.")
    # Start by loading the raw image from the Pi camera.  This creates a ``picamera.PiBayerArray``.
    with picamera.PiCamera() as cam:
        lens_shading_table = np.zeros(cam._lens_shading_table_shape(), dtype=np.uint8) + 32
        gains = np.ones_like(lens_shading_table, dtype=np.float)
        max_res = cam.MAX_RESOLUTION
    # Open the microscope and start with flat (i.e. no) lens shading correction.
    with microscope.load_microscope(lens_shading_table=lens_shading_table,
                                    resolution=max_res) as ms:
        ms.camera.start_preview(resolution=(1080*4/3, 1080))
        def get_rgb_image(): # shorthand for taking an RGB image
            return ms.rgb_image(use_video_port=True, resize=(max_res[0]//2, max_res[1]//2))
        ms.freeze_camera_settings(wait_before=4)
        # Adjust the shutter speed until the brightest pixels are giving a set value (say 220)
        for i in range(3):
            ms.camera.shutter_speed = int(ms.camera.shutter_speed * 150.0 / np.max(get_rgb_image()))
            time.sleep(1)
        
        #ms.camera.shutter_speed /=2
        for i in range(n_iterations):
            print("Optimising lens shading, pass {}/{}".format(i+1, n_iterations))
            # Take an RGB (i.e. processed) image, and calculate the change needed in the shading table
            images = [] #averaging to reduce noise
            for j in range(images_to_average):
                images.append(get_rgb_image())
            rgb_image = np.mean(images, axis=0, dtype=np.float)
            incremental_gains = lens_shading_correction_from_rgb(rgb_image, 64//2)
            gains *= incremental_gains#**0.8
            # Apply this change (actually apply a bit less than the change)
            ms.camera.lens_shading_table = gains_to_lst(gains*32)
            time.sleep(2)

        # Fix the AWB gains so the image is neutral
        channel_means = np.mean(np.mean(get_rgb_image(), axis=0, dtype=np.float), axis=0)
        old_gains = ms.camera.awb_gains
        ms.camera.awb_gains = (channel_means[1]/channel_means[0] * old_gains[0], channel_means[1]/channel_means[2]*old_gains[1])
        time.sleep(1)

        # Adjust shutter speed to make the image bright but not saturated
        for i in range(3):
            ms.camera.shutter_speed = int(ms.camera.shutter_speed * 230.0 / np.max(get_rgb_image()))
            time.sleep(1)
        
        settings = ms.settings_dict()
        settings['lens_shading_table'] = ms.camera.lens_shading_table
        time.sleep(1)

    for k in settings:
        print("{}: {}".format(k, settings[k]))
    np.savez(output_fname, **settings)
    print("Lens shading table written to {}".format(output_fname))

if __name__ == '__main__':
    try:
        generate_lens_shading_table_closed_loop(sys.argv[1])
    except:
        generate_lens_shading_table_closed_loop()
