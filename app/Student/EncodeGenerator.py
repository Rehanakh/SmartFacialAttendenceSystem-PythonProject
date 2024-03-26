import cv2
import  face_recognition
import  pickle
import os

# importing students images

script_dir = os.path.dirname(os.path.abspath(__file__))

# Build the path to the 'static/faces' directory
folderModepath = os.path.join(script_dir, '..', 'static', 'faces')
modePathList = os.listdir(folderModepath)
print(modePathList)
imgModeList = []
StudentIds=[]

for path in modePathList:
    # imgModeList.append(cv2.imread(os.path.join(folderModepath, path)))
    img = cv2.imread(os.path.join(folderModepath, path))
    imgModeList.append(img)
    identifier = os.path.splitext(path)[0]  # This gets the filename without the extension

    StudentIds.append(identifier)
    print(StudentIds)
def findEncoding(imagesList):
    encodeList=[]
    for img in imagesList:
        img=cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
        encode=face_recognition.face_encodings(img)[0]
        encodeList.append(encode)

    return encodeList
print("Encoding Started...")
encodeListKnown = findEncoding(imgModeList)
encodeListKnownWithIds = [encodeListKnown, StudentIds]
print("Encoding Complete")
print("Current working directory:", os.getcwd())

file = open("EncodeFile.p", 'wb')
pickle.dump(encodeListKnownWithIds, file)
file.close()
print('File saved')