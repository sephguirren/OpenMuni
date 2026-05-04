# OpenMuni

<!-- Optional: Add badges here, e.g., build status, license, python version -->
![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-Backend-black?style=flat-square&logo=flask)
![MongoDB](https://img.shields.io/badge/MongoDB-Database-success?style=flat-square&logo=mongodb)
![TensorFlow](https://img.shields.io/badge/TensorFlow-AI-orange?style=flat-square&logo=tensorflow)

> Empowering local governance through transparency, streamlined project management, and AI-driven accessibility.

## Description

OpenMuni enhances municipal transparency through a public-facing portal for citizens to track local projects, a secure administrative dashboard for officials to manage them, and an NLP-powered AI chatbot to answer real-time citizen queries regarding budgets and timelines.

## 🌟 Key Features

*   **Public Portal & Admin Dashboard:** View and manage ongoing projects across barangays.
*   **Role-Based Access:** Secure delegation for Super Admins and Sub Admins.
*   **End-to-End Tracking:** Manage proposals, budgets, timelines, and progress photos.
*   **Smart AI Chatbot:** NLP-driven bot to answer specific user questions instantly.

## 🛠 Tech Stack

*   **Backend:** Python / Flask, MongoDB (PyMongo), Werkzeug
*   **Frontend:** Jinja2 (HTML), CSS / JavaScript
*   **AI (Chatbot):** TensorFlow / Keras, NLTK, NumPy, Pickle

## 🚀 Installation & Setup

### Development Setup
```bash
# 1. Clone the repository
git clone [https://github.com/sephguirren/openmuni.git](https://github.com/sephguirren/openmuni.git)
cd openmuni

# 2. Set up virtual environment & install dependencies
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure .env file
# Add: FLASK_APP=app.py, SECRET_KEY, and MONGO_URI

# 4. Run the application
flask run
```

## 💻 Usage Example

Once running, navigate to `http://localhost:5000`. Citizens can view projects and ask the AI chatbot questions directly. Administrators can navigate to `/admin` to log in, propose projects, and upload progress updates.

## 📋 Release History

*   **0.1.0**
    *   Initial release: Project Management, Transparency Portal, and AI Chatbot integration.

## 👤 Meta

Mark Joseph B. Guirren – [LinkedIn](https://www.linkedin.com/in/mark-joseph-guirren-080742403/) – sephbergonia@gmail.com

Distributed under the MIT license. See `LICENSE` for more information.

[https://github.com/sephguirren/openmuni](https://github.com/sephguirren/openmuni)

## 🤝 Contributing

1.  Fork it (https://github.com/sephguirren/openmuni/fork)
2.  Create your feature branch (`git checkout -b feature/fooBar`)
3.  Commit your changes (`git commit -am 'Add some fooBar'`)
4.  Push to the branch (`git push origin feature/fooBar`)
5.  Create a new Pull Request
