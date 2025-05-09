import os
import cv2
import sqlite3
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import face_recognition
import datetime

# Initialize database
conn = sqlite3.connect('attendance.db')
c = conn.cursor()

# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS students
             (roll TEXT PRIMARY KEY, name TEXT, course TEXT, image_path TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS attendance
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              roll TEXT, date TEXT, status TEXT,
              FOREIGN KEY(roll) REFERENCES students(roll))''')
conn.commit()


class FaceAttendanceSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Attendance System")

        # Initialize known face encodings and names
        self.known_face_encodings = []
        self.known_face_rolls = []
        self.load_existing_students()

        # Create GUI
        self.create_gui()

    def create_gui(self):
        # Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(padx=10, pady=10, expand=True)

        # Add Student Tab
        self.add_student_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.add_student_tab, text="Add Student")
        self.create_add_student_tab()

        # Take Attendance Tab
        self.attendance_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.attendance_tab, text="Take Attendance")
        self.create_attendance_tab()

    def create_add_student_tab(self):
        # Form elements
        ttk.Label(self.add_student_tab, text="Roll Number:").grid(row=0, column=0, padx=5, pady=5)
        self.roll_entry = ttk.Entry(self.add_student_tab)
        self.roll_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(self.add_student_tab, text="Name:").grid(row=1, column=0, padx=5, pady=5)
        self.name_entry = ttk.Entry(self.add_student_tab)
        self.name_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(self.add_student_tab, text="Course:").grid(row=2, column=0, padx=5, pady=5)
        self.course_entry = ttk.Entry(self.add_student_tab)
        self.course_entry.grid(row=2, column=1, padx=5, pady=5)

        self.image_path = tk.StringVar()
        ttk.Button(self.add_student_tab, text="Upload Image",
                   command=self.upload_image).grid(row=3, column=0, columnspan=2, pady=5)

        ttk.Button(self.add_student_tab, text="Add Student",
                   command=self.add_student).grid(row=4, column=0, columnspan=2, pady=10)

    def create_attendance_tab(self):
        ttk.Button(self.attendance_tab, text="Start Attendance",
                   command=self.start_attendance).pack(pady=20)

        # Attendance Log
        self.log_text = tk.Text(self.attendance_tab, height=10, width=50)
        self.log_text.pack(padx=10, pady=10)

    def upload_image(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.image_path.set(file_path)

    def add_student(self):
        roll = self.roll_entry.get()
        name = self.name_entry.get()
        course = self.course_entry.get()
        image_path = self.image_path.get()

        if not all([roll, name, course, image_path]):
            print("All fields are required!")
            return

        # Save image to student_images folder
        os.makedirs("student_images", exist_ok=True)
        new_path = os.path.join("student_images", f"{roll}.jpg")
        os.rename(image_path, new_path)

        # Store in database
        try:
            c.execute("INSERT INTO students VALUES (?, ?, ?, ?)",
                      (roll, name, course, new_path))
            conn.commit()

            # Add face encoding
            image = face_recognition.load_image_file(new_path)
            encoding = face_recognition.face_encodings(image)[0]
            self.known_face_encodings.append(encoding)
            self.known_face_rolls.append(roll)

            print("Student added successfully!")
        except sqlite3.IntegrityError:
            print("Student with this roll number already exists!")

    def load_existing_students(self):
        students = c.execute("SELECT roll, image_path FROM students").fetchall()
        for roll, path in students:
            image = face_recognition.load_image_file(path)
            encoding = face_recognition.face_encodings(image)[0]
            self.known_face_encodings.append(encoding)
            self.known_face_rolls.append(roll)

    def start_attendance(self):
        cv2.CAP_DSHOW = 1
        video_capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        while True:
            ret, frame = video_capture.read()
            if not ret:
                break

            # Convert to RGB for face_recognition
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Find all faces
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations,model="large",num_jitters=1)

            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
                roll = "Unknown"

                if True in matches:
                    first_match_index = matches.index(True)
                    roll = self.known_face_rolls[first_match_index]

                    # Mark attendance
                    self.mark_attendance(roll)

                # Draw rectangle and label
                top, right, bottom, left = face_locations[0]
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.putText(frame, roll, (left + 6, bottom - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.imshow('Video', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        video_capture.release()
        cv2.destroyAllWindows()

    def mark_attendance(self, roll):
        today = datetime.date.today().strftime("%Y-%m-%d")

        # Check if already marked today
        existing = c.execute("SELECT * FROM attendance WHERE roll=? AND date=?",
                             (roll, today)).fetchone()
        if not existing:
            c.execute("INSERT INTO attendance (roll, date, status) VALUES (?, ?, ?)",
                      (roll, today, "Present"))
            conn.commit()
            self.log_text.insert(tk.END, f"{roll} marked present - {datetime.datetime.now()}\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = FaceAttendanceSystem(root)
    root.mainloop()
    conn.close()