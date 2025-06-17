# SchoolSecure Hall Pass System (v0.0.1)

This project is a comprehensive, vertically-integrated hall pass system for K-12 schools, built with a modern tech stack. It's the first module in a larger suite of AI-enhanced education technology tools.

## Project Overview

The system provides three distinct, role-based interfaces for Students, Teachers, and Administrators to manage and monitor student movement during school hours.

- **Students:** Can request passes to pre-approved locations, view their pass history, and receive digital summons from staff.
- **Teachers:** Can approve/deny pass requests, issue passes directly, and view a dashboard with analytics on their pass-granting habits compared to school averages.
- **Administrators:** Have full oversight, with a dashboard for school-wide analytics and a settings panel to configure all pass rules, locations, and durations.

## Tech Stack

- **Database:** Supabase
- **Backend:** FastAPI (Python)
- **Frontend:** React Native (TypeScript)
- **UI:** shadcn (principles)

## Setup and Installation

1.  **Clone the repository.**
2.  **Set up the database:** The database tables and initial data are managed via tool calls within the development environment.
3.  **Configure Environment Variables:** Copy `.env.example` to a new file named `.env` and fill in the required values for `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
4.  **Install Backend Dependencies:**
    ```bash
    cd backend
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
5.  **Install Frontend Dependencies:**
    ```bash
    cd frontend
    npm install
    ```
6.  **Run the Application:**
    - Start the backend server: `uvicorn main:app --reload` from the `backend` directory.
    - Start the frontend application: `npm run ios` or `npm run android` from the `frontend` directory. 