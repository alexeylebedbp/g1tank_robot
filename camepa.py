import cv2
import ipywidgets.widgets as widgets


cap = cv2.VideoCapture(0)
print(cap.isOpened())
cap.set(3, 1920);           # Width
cap.set(4, 1080);           # Height
cap.set(5, 30);             # Frame
cap.set(10, 1);             # Brightness 1
cap.set(11,40);             # Contrast 40
cap.set(12, 50);            # Saturation 50
cap.set(13, 50);            # Hue 50
cap.set(15, 50);            # Exposure 50


def brg_to_jpeg(value, quality=75):
    return bytes(cv2.imencode('.jpg', value)[1])



ret, frame = cap.read()
print(frame)
# jpg = brg_to_jpeg(frame)
# print(jpg)

# with open("my_file.txt", "wb") as binary_file:
   
#     # Write bytes to file
#     binary_file.write(some_bytes)
