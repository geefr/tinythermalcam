
import cv2
import numpy as np
import serial
import sys

def get_image(s):
    buf = s.read(2048)
    img = np.frombuffer(buf, np.int16).reshape(32, 32, 1)
    
    return img

def denoise(img):
    return cv2.fastNlMeansDenoising(img, None, 10, 7, 21)

def set_emissivity(s, e):
    # Limit 0.1 - 1.0, as per app
    e = max(e, 0.1)
    e = min(e, 1.0)

    # MainActivity.onStopTrackingTouch
    # ??? [address, command, value, checksum/end] ???
    msg = [85, 1, 0, 0]

    msg[2] = int(e * 100)

    v = 0
    for i in range(0, 3):
        v += msg[i]
    
    msg[3] = v

    s.write(bytes(msg))

def main():

    if len(sys.argv) < 2:
        print("Tiny Thermal Cam: For 32x32 TIOP01 thermal imager (Tiny Thermal Imager(TIOPS2))")
        print(f"USAGE: ./{sys.argv[0]} /dev/ttyACM0")
        print("(Assuming you have permissions to the port)")
        sys.exit(0)

    print("Starting capture, press q to exit")
    s = serial.Serial(sys.argv[1], 921600)

    # https://www.thermoworks.com/emissivity-table/
    set_emissivity(s, 0.95) # Skin
    # set_emissivity(s, 0.59) # Steel

    while True:
        # Port of java ThermalImager from TinyThermalImager app
        # https://www.pgyer.com/KWVl

        # Byte2IntTemp
        # int16
        img = get_image(s)
        img = cv2.flip(img, 0)

        # TempSort
        # mTempFilterAryInt is scanned for min/max
        # fMaxTemp is FilterAryInt / 10.0f -> Temp in celcius
        # TODO: I assume here is where we do emissivity constants?
        #       Or do we send to the camera to set those?
        #       Dividing by 10 seems to get skin temperature about right
        img_celcius = img.astype(np.float32) / 10.0
        minTemp = np.min(img_celcius)
        maxTemp = np.max(img_celcius)
        print(f"Min: {minTemp:.2f}c Max: {maxTemp:.2f}c")

        # TempFilter - Or similar to it
        x1 = 0.15
        x2 = 0.3
        smoothen = np.array([
            [x1, x2, x1],
            [x2, 1.0, x2],
            [x1, x2, x1]
        ])
        smoothen /= np.sum(smoothen)
        img = cv2.filter2D(img, -1, smoothen)

        # sharpen = np.array(
        #     [[-1,-1,-1],
        #      [-1,9,-1],
        #      [-1,-1,-1]]
        # )
        # img = cv2.filter2D(img, -1, sharpen)

        # TempScale
        # Code for this one is really confusing, but looks like an upscale?
        img = cv2.resize(img, (512, 512), None, None, None, cv2.INTER_LINEAR)


        # To normalised float
        img = img.astype(np.float32)
        img /= 65535
        # minFloat = np.min(img)
        # maxFloat = np.max(img)

        # Temp2Color
        # Want min just above ambient, max high enough to not clip
        normMin = (18 * 10.0) / 65535.0
        normMax = (45 * 10.0) / 65535.0

        img_vis = img.copy()
        
        img_vis = img_vis.clip(normMin, normMax)
        img_vis = (img_vis - normMin) / (normMax - normMin)

        img_vis = (img_vis * 255.0).astype(np.uint8)
        img_vis = cv2.applyColorMap(img_vis, cv2.COLORMAP_PLASMA)

        cv2.imshow('ttc', img_vis)
        if cv2.waitKey(1) == ord('q'):
            break

if __name__ == '__main__':
    main()
