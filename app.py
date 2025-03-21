import cv2
import os
from flask import Flask, request, render_template, redirect, url_for
from datetime import date, datetime
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
import pandas as pd
import joblib

# Defining Flask App
app = Flask(__name__)

nimgs = 10

# Saving Date today in 2 different formats
datetoday = date.today().strftime("%m_%d_%y")
datetoday2 = date.today().strftime("%d-%B-%Y")

# Initializing VideoCapture object to access WebCam
face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
notification = None  # or set it to some meaningful value


# Ensure required directories exist
if not os.path.isdir('Profile'):
    os.makedirs('Profile')
if not os.path.isdir('static'):
    os.makedirs('static')
if not os.path.isdir('static/faces'):
    os.makedirs('static/faces')
if not os.path.isdir('static/notes'):
    os.makedirs('static/notes')
if f'Profile-{datetoday}.csv' not in os.listdir('Profile'):
    with open(f'Profile/Profile-{datetoday}.csv', 'w') as f:
        f.write('Name,Roll,Time')

# Get the number of total registered users
def totalreg():
    return len(os.listdir('static/faces'))

# Extract the face from an image
def extract_faces(img):
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_points = face_detector.detectMultiScale(gray, 1.2, 5, minSize=(20, 20))
        return face_points
    except:
        return []

# Identify face using ML model
def identify_face(facearray):
    model = joblib.load('static/face_recognition_model.pkl')
    return model.predict(facearray)

# A function which trains the model on all the faces available in faces folder
def train_model():
    faces = []
    labels = []
    userlist = os.listdir('static/faces')
    for user in userlist:
        for imgname in os.listdir(f'static/faces/{user}'):
            img = cv2.imread(f'static/faces/{user}/{imgname}')
            resized_face = cv2.resize(img, (50, 50))
            faces.append(resized_face.ravel())
            labels.append(user)
    faces = np.array(faces)
    knn = KNeighborsClassifier(n_neighbors=5)
    knn.fit(faces, labels)
    joblib.dump(knn, 'static/face_recognition_model.pkl')

# Extract info from today's profile file in profile folder
def extract_profile():
    df = pd.read_csv(f'Profile/Profile-{datetoday}.csv')
    names = df['Name']
    rolls = df['Roll']
    times = df['Time']
    l = len(df)
    return names, rolls, times, l

# Add Profile of a specific user
def add_profile(name):
    username = name.split('_')[0]
    userid = name.split('_')[1]
    current_time = datetime.now().strftime("%H:%M:%S")

    df = pd.read_csv(f'Profile/Profile-{datetoday}.csv')
    if int(userid) not in list(df['Roll']):
        with open(f'Profile/Profile-{datetoday}.csv', 'a') as f:
            f.write(f'\n{username},{userid},{current_time}')

# A function to get names and roll numbers of all users
def getallusers():
    userlist = os.listdir('static/faces')
    names = []
    rolls = []
    l = len(userlist)

    for i in userlist:
        name, roll = i.split('_')
        names.append(name)
        rolls.append(roll)

    return userlist, names, rolls, l

# A function to delete a user folder 
def deletefolder(duser):
    pics = os.listdir(duser)
    for i in pics:
        os.remove(duser + '/' + i)
    os.rmdir(duser)

################## ROUTING FUNCTIONS #########################

# Main page
@app.route('/')
def home():
    names, rolls, times, l = extract_profile()
    return render_template('home.html', names=names, rolls=rolls, times=times, l=l, totalreg=totalreg(), datetoday2=datetoday2)

# List users page
@app.route('/listusers')
def listusers():
    userlist, names, rolls, l = getallusers()
    return render_template('listusers.html', userlist=userlist, names=names, rolls=rolls, l=l, totalreg=totalreg(), datetoday2=datetoday2)

# Delete user functionality
@app.route('/deleteuser', methods=['GET'])
def deleteuser():
    duser = request.args.get('user')
    deletefolder('static/faces/' + duser)

    if os.listdir('static/faces/') == []:
        os.remove('static/face_recognition_model.pkl')

    try:
        train_model()
    except:
        pass

    userlist, names, rolls, l = getallusers()
    return render_template('listusers.html', userlist=userlist, names=names, rolls=rolls, l=l, totalreg=totalreg(), datetoday2=datetoday2)

# Main Face Recognition functionality
@app.route('/start', methods=['GET'])
def start():
    names, rolls, times, l = extract_profile()

    if 'face_recognition_model.pkl' not in os.listdir('static'):
        return render_template('home.html', names=names, rolls=rolls, times=times, l=l, totalreg=totalreg(), datetoday2=datetoday2, mess='No trained model found. Please add a new face to continue.')

    ret = True
    cap = cv2.VideoCapture(0)
    while ret:
        ret, frame = cap.read()
        if len(extract_faces(frame)) > 0:
            (x, y, w, h) = extract_faces(frame)[0]
            cv2.rectangle(frame, (x, y), (x+w, y+h), (86, 32, 251), 1)
            face = cv2.resize(frame[y:y+h, x:x+w], (50, 50))
            identified_person = identify_face(face.reshape(1, -1))[0]
            add_profile(identified_person)
            cap.release()
            cv2.destroyAllWindows()
            # Redirect to the notes page with the recognized username
            username = identified_person.split('_')[0]
            return redirect(url_for('notes', username=username))
        cv2.imshow('Profile', frame)
        if cv2.waitKey(1) == 27:
            break
    cap.release()
    cv2.destroyAllWindows()
    return render_template('home.html', names=names, rolls=rolls, times=times, l=l, totalreg=totalreg(), datetoday2=datetoday2)

# Add new user
@app.route('/add', methods=['GET', 'POST'])
def add():
    newusername = request.form['newusername']
    newuserid = request.form['newuserid']
    userimagefolder = 'static/faces/' + newusername + '_' + str(newuserid)
    if not os.path.isdir(userimagefolder):
        os.makedirs(userimagefolder)
    i, j = 0, 0
    cap = cv2.VideoCapture(0)
    while 1:
        _, frame = cap.read()
        faces = extract_faces(frame)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 20), 2)
            cv2.putText(frame, f'Images Captured: {i}/{nimgs}', (30, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 20), 2, cv2.LINE_AA)
            if j % 5 == 0:
                name = newusername + '_' + str(i) + '.jpg'
                cv2.imwrite(userimagefolder + '/' + name, frame[y:y+h, x:x+w])
                i += 1
            j += 1
        if j == nimgs * 5:
            break
        cv2.imshow('Adding new User', frame)
        if cv2.waitKey(1) == 27:
            break
    cap.release()
    cv2.destroyAllWindows()
    print('Training Model')
    train_model()
    names, rolls, times, l = extract_profile()
    return render_template('home.html', names=names, rolls=rolls, times=times, l=l, totalreg=totalreg(), datetoday2=datetoday2)

# Notes page for recognized user
@app.route('/notes/<username>', methods=['GET', 'POST'])
def notes(username):
    notes_file = f'static/notes/{username}.txt'

    if request.method == 'POST':
        note_content = request.form.get('note')
        with open(notes_file, 'a') as f:
            f.write(f'{note_content}\n')

    notes = []
    if os.path.exists(notes_file):
        with open(notes_file, 'r') as f:
            notes = f.readlines()

    return render_template('notes.html', username=username, notes=notes)

# Run Flask App
if __name__ == '__main__':
    app.run(debug=True)
