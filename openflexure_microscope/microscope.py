from __future__ import print_function
import picamera
from picamera import PiCamera
import picamera.array
import numpy as np
import scipy
from scipy import ndimage
import time
import matplotlib.pyplot as plt
from openflexure_stage import OpenFlexureStage
from contextlib import contextmanager, closing

picam2_full_res = (3280, 2464)
picam2_half_res = tuple([d/2 for d in picam2_full_res])
picam2_quarter_res = tuple([d/4 for d in picam2_full_res])
picamera_init_settings = {"lens_shading_table": None, "resolution": tuple}
picamera_later_settings = {"awb_mode":str, 
                           "awb_gains":tuple,
                           "shutter_speed":"[()]",
                           "analog_gain":"[()]",
                           "digital_gain":"[()]",
                           "brightness":"[()]",
                           "contrast":"[()]",
                           }

def round_resolution(res):
    """Round up the camera resolution to units of 32 and 16 in x and y"""
    return tuple([int(q*np.ceil(res[i]/float(q))) for i, q in enumerate([32,16])])

def decimate_to(shape, image):
    """Decimate an image to reduce its size if it's too big."""
    decimation = np.max(np.ceil(np.array(image.shape, dtype=np.float)[:len(shape)]/np.array(shape)))
    return image[::decimation, ::decimation, ...]

def sharpness_sum_lap2(rgb_image):
    """Return an image sharpness metric: sum(laplacian(image)**")"""
    image_bw=np.mean(decimate_to((1000,1000), rgb_image),2)
    image_lap=ndimage.filters.laplace(image_bw)
    return np.mean(image_lap.astype(np.float)**4)

def sharpness_edge(image):
    """Return a sharpness metric optimised for vertical lines"""
    gray = np.mean(image.astype(float), 2)
    n = 20
    edge = np.array([[-1]*n + [1]*n])
    return np.sum([np.sum(ndimage.filters.convolve(gray,W)**2) 
                   for W in [edge, edge.T]])

class Microscope(object):
    def __init__(self, camera=None, stage=None):
        """Create the microscope object.  The camera and stage should already be initialised."""
        self.camera = camera
        self.stage = stage

    def close(self):
        """Shut down the microscope hardware."""
        self.camera.close()
        self.stage.close()

    def rgb_image_old(self, use_video_port=True):
        """Capture a frame from a camera and output to a numpy array"""
        res = round_resolution(self.camera.resolution)
        shape = (res[1], res[0], 3)
        buf = np.empty(np.product(shape), dtype=np.uint8)
        self.camera.capture(buf, 
                format='rgb', 
                use_video_port=use_video_port)
        #get an image, see picamera.readthedocs.org/en/latest/recipes2.html
        return buf.reshape(shape)

    def rgb_image(self, use_video_port=True, resize=None):
        """Capture a frame from a camera and output to a numpy array"""
        with picamera.array.PiRGBArray(self.camera, size=resize) as output:
            self.camera.capture(output, 
                    format='rgb', 
                    resize=resize,
                    use_video_port=use_video_port)
        #get an image, see picamera.readthedocs.org/en/latest/recipes2.html
            return output.array

    def freeze_camera_settings(self, iso=None, wait_before=2, wait_after=0.5):
        """Turn off as much auto stuff as possible (except lens shading)"""
        if iso is not None:
            self.camera.iso = iso
        time.sleep(wait_before)
        self.camera.shutter_speed = self.camera.exposure_speed
        self.camera.exposure_mode = "off"
        g = self.camera.awb_gains
        self.camera.awb_mode = "off"
        self.camera.awb_gains = g
        print("Camera settings are frozen.  Analogue gain: {}, Digital gain: {}, Exposure speed: {}, AWB gains: {}".format(self.camera.analog_gain, self.camera.digital_gain, self.camera.exposure_speed, self.camera.awb_gains))
        time.sleep(wait_after)

    def autofocus(self, dz, backlash=0, settle=0.5, metric_fn=sharpness_sum_lap2):
        """Perform a simple autofocus routine.

        The stage is moved to z positions (relative to current position) in dz,
        and at each position an image is captured and the sharpness function 
        evaulated.  We then move back to the position where the sharpness was
        highest.  No interpolation is performed.

        dz is assumed to be in ascending order (starting at -ve values)
        """
        sharpnesses = []
        positions = []
        for i in self.stage.scan_z(dz):
            positions.append(self.stage.position[2])
            time.sleep(settle)
            sharpnesses.append(metric_fn(self.rgb_image(
                        use_video_port=True, 
                        resize=(640,480))))
        newposition = positions[np.argmax(sharpnesses)]
        self.stage.focus_rel(newposition - self.stage.position[2], backlash=backlash)
        return positions, sharpnesses

    def settings_dict(self):
        """Return all the relevant settings as a dictionary."""
        settings = {}
        for k in picamera_later_settings.keys() + picamera_init_settings.keys():
            settings[k] = getattr(self.camera, k)
        return settings

    def save_settings(self, npzfile):
        "Save the microscope's current settings to an npz file"
        np.savez(npzfile, **self.settings_dict())


def extract_settings(source_dict, converters):
    """Extract a subset of a dictionary of settings.

    For each item in ``source_dict`` that shares a key with an item in
    ``converters``, return a dictionary of values that have been
    processed using the conversion functions in the second dict.

    NB "None" is equivalent to no processing, to save some typing.
    There are some special string values for converters:
    "[()]" will convert a 0-dimensional numpy array to a scalar
    "[0]" will return the first element of a 1D array
    If either "[()]" or "[0]" is specified and raises an exception,
    then we fall back to no processing.  This is good if the values
    might be from a numpy ``.npz`` file, or might be specified directly.
    """
    settings = {}
    for k in source_dict:
        if k in converters:
            if converters[k] is None:
                settings[k] = source_dict[k]
            elif converters[k] == "[()]":
                try:
                    settings[k] = source_dict[k][()]
                except:
                    settings[k] = source_dict[k]
            elif converters[k] == "[0]":
                try:
                    settings[k] = source_dict[k][0]
                except:
                    settings[k] = settings[k]
            else:
                settings[k] = converters[k](source_dict[k])
    return settings


#
@contextmanager
def load_microscope(npzfile=None, save_settings=False, **kwargs):
    """Create a microscope object with specified settings. (context manager)

    This will read microscope settings from a .npz file, and/or from
    keyword arguments.  It will then create the microscope object, and
    close it at the end of the with statement.  Keyword arguments will
    override settings specified in the file.

    If save_settings is
    True, it will attempt to save the microscope's settings at the end of
    the with block, to the same filename.  If save_settings_on_exit is set
    to a string, it should save instead to that filename.
    """
    settings = {}
    try:
        npz = np.load(npzfile)
        for k in npz:
            settings[k] = npz[k]
    except:
        pass
    settings.update(kwargs)

    if "stage_port" in settings:
        stage_port = settings["stage_port"]
        del settings["stage_port"]
    else:
        stage_port = None


    with closing(OpenFlexureStage(stage_port)) as stage, \
         closing(PiCamera(**extract_settings(settings, picamera_init_settings))) as camera:
        ms = Microscope(camera, stage)
        for k, v in extract_settings(settings, picamera_later_settings).items():
            setattr(ms.camera, k, v)
        yield ms # The contents of the with block from which we're called happen here
        if save_settings:
            if save_settings is True:
                save_settings = npzfile
            ms.save_settings(save_settings)



if __name__ == "__main__":
    with picamera.PiCamera() as camera, \
         OpenFlexureStage("/dev/ttyUSB0") as stage:
#        camera.resolution=(640,480)
        camera.start_preview()
        ms = Microscope(camera, stage)
        ms.freeze_camera_settings(iso=100)
        camera.shutter_speed = camera.shutter_speed / 4

        backlash=128

        for step,n in [(1000,10),(200,10),(100,10),(50,10)]:
            dz = (np.arange(n) - (n-1)/2.0) * step
                
            pos, sharps = ms.autofocus(dz, backlash=backlash)

            
            plt.plot(pos,sharps,'o-')

        plt.xlabel('position (Microsteps)')
        plt.ylabel('Sharpness (a.u.)')
        time.sleep(2)
        
    plt.show()
 
    print("Done :)")

