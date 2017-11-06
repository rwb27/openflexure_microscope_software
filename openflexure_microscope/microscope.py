import picamera
import picamera.array
import cv2
import numpy as np
import scipy
from scipy import ndimage
import time
import matplotlib.pyplot as plt
from openflexure_stage import OpenFlexureStage

picam2_full_res = (3280, 2464)
picam2_half_res = tuple([d/2 for d in picam2_full_res])
picam2_quarter_res = tuple([d/4 for d in picam2_full_res])

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
        """Not bothering with context manager yet!"""
        self.cam = camera
        self.stage = stage

    def rgb_image_old(self, use_video_port=True):
        """Capture a frame from a camera and output to a numpy array"""
        res = round_resolution(self.cam.resolution)
        shape = (res[1], res[0], 3)
        buf = np.empty(np.product(shape), dtype=np.uint8)
        self.cam.capture(buf, 
                format='rgb', 
                use_video_port=use_video_port)
        #get an image, see picamera.readthedocs.org/en/latest/recipes2.html
        return buf.reshape(shape)

    def rgb_image(self, use_video_port=True, resize=None):
        """Capture a frame from a camera and output to a numpy array"""
        with picamera.array.PiRGBArray(self.cam, size=resize) as output:
            self.cam.capture(output, 
                    format='rgb', 
                    resize=resize,
                    use_video_port=use_video_port)
        #get an image, see picamera.readthedocs.org/en/latest/recipes2.html
            return output.array

    def freeze_camera_settings(self, iso=None, wait_before=2, wait_after=0.5):
        """Turn off as much auto stuff as possible"""
        if iso is not None:
            self.cam.iso = iso
        time.sleep(wait_before)
        self.cam.shutter_speed = self.cam.exposure_speed
        self.cam.exposure_mode = "off"
        g = self.cam.awb_gains
        self.cam.awb_mode = "off"
        self.cam.awb_gains = g
        time.sleep(wait_after)

    def scan_linear(self, rel_positions, backlash=True, return_to_start=True):
        """Scan through a list of (relative) positions (generator fn)
        
        rel_positions should be an nx3-element array (or list of 3 element arrays).  
        Positions should be relative to the starting position - not a list of relative moves.

        backlash argument is passed to the stage (default true)
        
        if return_to_start is True (default) we return to the starting position after a
        successful scan.  NB we always attempt to return to the starting position if the
        scan was unsuccessful.
        """
        starting_position = self.stage.position
        rel_positions = np.array(rel_positions)
        assert rel_positions.shape[1] == 3, ValueError("Positions should be 3 elements long.")
        try:
            self.stage.move_rel(rel_positions[0], backlash=backlash)
            yield 0

            for i, step in enumerate(np.diff(rel_positions, axis=0)):
                self.stage.move_rel(step, backlash=backlash)
                yield i+1
        except Exception as e:
            return_to_start = True # always return to start if it went wrong.
            raise e
        finally:
            if return_to_start:
                self.stage.move_abs(starting_position, backlash=backlash)

    def scan_z(self, dz, **kwargs):
        """Scan through a list of (relative) z positions (generator fn)"""
        return self.scan_linear([[0,0,z] for z in dz], **kwargs)


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
        def z():
            return self.stage.position[2]
        def measure():
            time.sleep(settle)
            sharpnesses.append(metric_fn(self.rgb_image(
                        use_video_port=True, 
                        resize=(640,480))))
            positions.append(z())

        self.stage.focus_rel(dz[0]-backlash)
        self.stage.focus_rel(backlash)
        measure()

        for step in np.diff(dz):
            self.stage.focus_rel(step)
            measure()
           
        newposition = positions[np.argmax(sharpnesses)]

        self.stage.focus_rel(newposition - backlash - z())
        self.stage.focus_rel(backlash)

        return positions, sharpnesses


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
 
    print "Done :)"

