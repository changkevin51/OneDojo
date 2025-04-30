# OneDojo - Dojo Management Portal

OneDojo is a comprehensive web application designed to manage martial arts dojos efficiently. It provides separate portals for students and instructors/administrators, streamlining tasks like attendance tracking, assignment management, progress monitoring, and communication.

[Insert image of student dashboard]

## Features

### Student Portal
*   **Dashboard:** View active assignments, overdue tasks, and completion status.
*   **Progress Tracking:** Monitor belt progress, assignment completion rates, and attendance records. View detailed criteria for the current belt level.
*   **Assignments:** View active and completed assignments, submit work, and view feedback.
*   **Assessments:** View assessment results and feedback.
*   **Calendar:** View upcoming events, deadlines, and dojo schedule.
*   **Notifications:** Receive updates on assignments, feedback, and announcements.

### Instructor/Admin Portal
*   **Dashboard:** Overview of assigned classes and recent activities.
*   **Student Management:** View student lists per class, access detailed student profiles (progress, attendance, assignments), manage belt levels, and add timeline events (assignments, assessments, materials).
*   **Class Management:** Create and edit classes (units), assign teachers, and manage student enrollments.
*   **Attendance Tracking:** Take attendance for classes, view historical attendance records, and edit entries.
*   **Assignment Management:** Post assignments to specific classes or students. View submissions and provide feedback.
*   **Feedback Management:** Create, manage, and use feedback templates for efficient communication.
*   **Belt Criteria Management:** Define and manage the criteria required for each belt level. Track student progress against these criteria.
*   **Calendar Management:** Create and manage dojo events, view student/staff birthdays (toggleable), and control event visibility.
*   **User Management:** Create, view, edit, and delete user accounts (students, teachers, admins). Filter and sort user lists.
*   **Dojo Management (Superuser):** Create and manage multiple dojos, generate registration links.

[Insert image of instructor dashboard or student management view]

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



