
<p align="center">
  <img width="280" height="260" src="https://github.com/user-attachments/assets/1e5dfd9a-808e-4a71-bc43-b0f6b81e8260">
</p>

<div align="center">
  <h1>OneDojo - Dojo Management Portal</h1>
</div>



OneDojo is a comprehensive web application designed to manage martial arts dojos efficiently. It provides separate portals for students and instructors/administrators. It aims to streamline tasks like attendance tracking, assignment management, progress monitoring, and communication.

![image](https://github.com/user-attachments/assets/fba55f19-ef22-4fc9-ade9-e7c2fbc1d8be)

<div align="center">
  <i>Student portfolio on the instructor view</i>
</div>

## Features

### Student Portal
*   **Dashboard:** A brief overview of their activities, progress, and assignments.
*   **Progress Tracking:** Monitor belt progress, assignment completion, and attendance records. View detailed criteria for the current belt level and improve with monthly progress reports. 
*   **Assignments:** View active and completed assignments, submit work, and view feedback.
*   **Assessments:** View assessment results and feedback.
*   **Calendar:** View upcoming events, deadlines, and dojo schedule.
*   **Notifications:** Receive updates on assignments, feedback, and announcements.

### Instructor/Admin Portal
*   **Student Management:** View student lists per class, access detailed student profiles (progress, attendance, assignments), manage belt levels. All activity is saved in their timeline events.
*   **Class Management:** Create and edit classes, assign teachers, and manage student enrollments.
*   **Attendance Tracking:** Take attendance for classes, view historical attendance records, and edit entries.
*   **Assignment Management:** Post assignments to specific classes or students. View submissions and provide feedback.
*   **Feedback Management:** Create, manage, and use feedback templates for efficient communication.
*   **Progress Report:** Send personalized progress reports to students (strengths, weaknesses, next steps)
*   **Belt Criteria Management:** Define and manage the criteria required for each belt level. Track student progress against these criteria.
*   **Calendar Management:** Create and manage dojo events, view student/staff birthdays (toggleable), and control event visibility.
*   **User Management:** Create, view, edit, and delete user accounts (students, teachers, admins). Filter and sort user lists.
*   **Dojo Management (Superuser):** Create and manage multiple dojos, generate registration links.

Watch a demo of the app:

[Watch a Demo of the app](https://github.com/user-attachments/assets/2bfcf80d-05ea-48ea-8fad-5e83013a6066)




## Installation

Follow these steps to set up the project locally:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/changkevin51/OneDojo.git
    cd OneDojo
    ```
2.  **Set up a virtual environment (Recommended):**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Apply database migrations:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```
5.  **Create a superuser account:**
    Follow the prompts to create an administrator account.
    ```bash
    python manage.py createsuperuser
    ```
6.  **Run the development server:**
    ```bash
    python manage.py runserver
    ```
7.  **Access the application:**
    Open your web browser and go to `http://127.0.0.1:8000/`.
8.  **Access the admin panel:**
    Go to `http://127.0.0.1:8000/admin/` and log in with the superuser credentials created in step 5.

**(Note: The database (SQLite) is not included in the repository. You need to run the migration commands and create users.)**


# Credits and Acknowledgements

* [AdminLTE's](https://adminlte.io/) was used for the development of the app. The default template has been heavily modified to suit the requirements of the app.

* AI assistance was used to help debug.




