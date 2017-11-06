import microscope
import picamera
import numpy as np
import matplotlib.pyplot as plt
import time
#resolution=(3280,2464)
#m = microscope.Microscope(picamera.PiCamera(resolution=(640,480)), None)
m = microscope.Microscope(picamera.PiCamera(resolution=(3280/1,2464/1)), None)
m.cam.start_preview()
time.sleep(2)
image = m.rgb_image()
m.cam.stop_preview()

plt.figure()
plt.imshow(image)
plt.figure()
plt.imshow(microscope.decimate_to((100,100),image))
plt.show()
