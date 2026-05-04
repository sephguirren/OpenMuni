# OpenMuni

## System Description
OpenMuni is a comprehensive web-based platform designed to enhance transparency and streamline project management for municipalities and local government units. The system provides a dual-faceted approach: a public-facing portal for citizens to view and track local projects, and a secure administrative dashboard for officials to propose, manage, and monitor projects across different barangays. To further improve accessibility, OpenMuni integrates an intelligent, NLP-powered AI chatbot capable of answering real-time citizen queries regarding project budgets, locations, timelines, and statuses.

## Features
- **Public Transparency Portal:** Allows citizens to search and view ongoing, completed, and proposed local projects across different barangays.
- **Role-Based Access Control:** Secure login system supporting multiple roles (Super Admins and Sub Admins) to ensure proper data governance and delegation.
- **Admin Dashboard:** Comprehensive dashboard with real-time statistics, including interactive charts for tracking project statuses and annual budget vs. expenses.
- **Project Management:** End-to-end tracking of projects from proposal to completion, including budget allocation, timelines, and specific location mapping.
- **Progress Photo Uploads:** Allows authorized users to upload images documenting project milestones and progress.
- **Activity Logging:** Automated logging of administrative actions to maintain a clear audit trail of system changes.
- **Barangay & User Management:** Super Admins can add new barangays and manage Sub Admin accounts for localized project handling.
- **Smart AI Chatbot:** An integrated NLP chatbot that dynamically queries the database to answer specific user questions like "What is the budget for [Project]?" or "What is the status of [Project]?".

## Tech Stack
### Backend
- **Framework:** Python / Flask
- **Database:** MongoDB (PyMongo)
- **File Handling:** Werkzeug (Secure Filenames)

### Frontend
- **Templating:** Jinja2 (HTML)
- **Styling & Interactivity:** CSS / JavaScript (Client-side logic and Charts)

### AI & Machine Learning (Chatbot)
- **Deep Learning Framework:** TensorFlow / Keras (Neural Network Model)
- **Natural Language Processing:** NLTK (WordNetLemmatizer, Tokenization)
- **Data Processing:** NumPy, Pickle
