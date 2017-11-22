"""
A script to print the current AWB gains of the Pi Camera
"""
import picamera


if __name__ == "__main__":
    with picamera.PiCamera(resolution=microscope.picam2_full_res) as camera:
        camera.start_preview()
        
        time.sleep(3)
        print "AWB Gains:"
        print camera.awb_gains

