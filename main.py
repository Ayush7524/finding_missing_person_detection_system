import cv2, sys, numpy, os
import requests
import json
import time
import datetime
import argparse
import requests
from datetime import datetime

def send_last_seen_info(name, location):
    url = "http://localhost:5000/api/add_last_seen"
    payload = {
        "image_path": name,
        "location": location,
        "timestamp": datetime.now().isoformat()
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)

    # Print response
    if response.ok:
        print("Success:", response.json())
    else:
        print("Error:", response.status_code, response.text)



fire_notification = False


# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-t", "--thress", required=True,
    help = "recognition threshold")

ap.add_argument("-l", "--loc", required=True,
    help = "Location name without spce")

args = vars(ap.parse_args())


location = args['loc']
thressHoldFaceMatch = int(args['thress'])

    
face_confirm_frame_count = 0
face_confirm_frame_count_limit = 10


size = 2
fn_haar = 'haarcascade_frontalface_default.xml'
fn_dir = 'att_faces'










# Part 1: Create fisherRecognizer
print('Training...')

# Create a list of images and a list of corresponding names
(images, lables, names, id) = ([], [], {}, 0)

# Get the folders containing the training data
for (subdirs, dirs, files) in os.walk(fn_dir):

    # Loop through each folder named after the subject in the photos
    for subdir in dirs:
        names[id] = subdir
        subjectpath = os.path.join(fn_dir, subdir)

        # Loop through each photo in the folder
        for filename in os.listdir(subjectpath):

            # Skip non-image formates
            f_name, f_extension = os.path.splitext(filename)
            if(f_extension.lower() not in
                    ['.png','.jpg','.jpeg','.gif','.pgm']):
                print("Skipping "+filename+", wrong file type")
                continue
            path = subjectpath + '/' + filename
            lable = id

            # Add to training data
            images.append(cv2.imread(path, 0))
            lables.append(int(lable))
        id += 1
(im_width, im_height) = (112, 92)

# Create a Numpy array from the two lists above
(images, lables) = [numpy.array(lis) for lis in [images, lables]]

# OpenCV trains a model from the images
# NOTE FOR OpenCV2: remove '.face'
#model = cv2.face.createFisherFaceRecognizer()
#model = cv2.face.FisherFaceRecognizer_create()
model = cv2.face.LBPHFaceRecognizer_create()
#model = cv2.face.LBPHFaceRecognizer_create()
#model = cv2.face.EigenFaceRecognizer_create()
model.train(images, lables)





alarm_not_recog = False
alarm_not_recog_last = False


# Part 2: Use fisherRecognizer on camera stream
haar_cascade = cv2.CascadeClassifier(fn_haar)
webcam = cv2.VideoCapture(0)

confimation_frame_count = 0

while True:

    # Loop until the camera is working
    rval = False
    while(not rval):
        # Put the image from the webcam into 'frame'
        (rval, frame) = webcam.read()
        if(not rval):
            print("Failed to open webcam. Trying again...")

        
    # Flip the image (optional)
    frame=cv2.flip(frame,1,0)

    # Convert to grayscalel
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Resize to speed up detection (optinal, change size above)
    mini = cv2.resize(gray, (int(gray.shape[1] / size), int(gray.shape[0] / size)))

    # Detect faces and loop through each one
    faces = haar_cascade.detectMultiScale(mini)
    for i in range(len(faces)):
        face_i = faces[i]

        # Coordinates of face after scaling back by `size`
        (x, y, w, h) = [v * size for v in face_i]
        face = gray[y:y + h, x:x + w]
        face_resize = cv2.resize(face, (im_width, im_height))

        # Try to recognize the face
        prediction = model.predict(face_resize)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)

        # [1]
        # Write the name of recognized face
        #cv2.putText(frame,'%s - %.0f' % (names[prediction[0]],prediction[1]),(x-10, y-10), cv2.FONT_HERSHEY_PLAIN,1,(0, 255, 0))
        if prediction[1] < thressHoldFaceMatch:
            cv2.putText(frame,'%s - %.0f' % (names[prediction[0]],prediction[1]),(x-10, y-10), cv2.FONT_HERSHEY_PLAIN,1,(0, 255, 0))
            confimation_frame_count += 1
            if confimation_frame_count >= 10:
                confimation_frame_count = 10     
                print("sending to server..")     
                send_last_seen_info(names[prediction[0]], location)
            
        else:
            cv2.putText(frame,'Not recognized',(x-10, y-10), cv2.FONT_HERSHEY_PLAIN,1,(0, 0, 255))
            confimation_frame_count = 0



    cv2.imshow('Camera', frame)


    
    Key = cv2.waitKey(1)
    if Key == 27:
        cv2.destroyAllWindows()
        break
        
   
    
  

        



        
