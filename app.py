from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.utils import secure_filename
from pymongo import MongoClient
import os
import numpy as np
import pickle
import json
import random
import nltk
from nltk.stem import WordNetLemmatizer
from tensorflow.keras.models import load_model
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_openmuni_key' 

# --- CONFIGURATION FOR PHOTO UPLOADS ---
UPLOAD_FOLDER = 'static/img/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- MONGODB CONNECTION ---
client = MongoClient('mongodb://localhost:27017/')
db = client['openmuni_db'] 

# Helper to auto-increment IDs so we don't break the frontend HTML
def get_next_id(collection_name):
    max_doc = db[collection_name].find_one(sort=[("_id", -1)])
    return (max_doc["_id"] + 1) if max_doc else 1

# ==========================================
# 🌐 PUBLIC ROUTES (The Frontend)
# ==========================================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/transparency')
def transparency():
    return render_template('transparency.html')

@app.route('/projects')
def public_projects():
    search_query = request.args.get('search', '')
    
    pipeline = [
        {"$lookup": {"from": "barangays", "localField": "barangay_id", "foreignField": "_id", "as": "barangay_info"}},
        {"$unwind": {"path": "$barangay_info", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "users", "localField": "submitted_by", "foreignField": "_id", "as": "user_info"}},
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"created_at": -1}}
    ]

    if search_query:
        pipeline.insert(0, {
            "$match": {
                "$or": [
                    {"title": {"$regex": search_query, "$options": "i"}},
                    {"status": {"$regex": search_query, "$options": "i"}},
                    {"barangay_info.name": {"$regex": search_query, "$options": "i"}}
                ]
            }
        })

    raw_projects = list(db.projects.aggregate(pipeline))
    
    projects = []
    for p in raw_projects:
        p['id'] = p['_id']
        p['barangay_name'] = p.get('barangay_info', {}).get('name', 'Unknown')
        p['submitter_name'] = p.get('user_info', {}).get('full_name', 'Unknown')
        p['images'] = p.get('images', []) 
        projects.append(p)

    return render_template('public_projects.html', projects=projects, search_query=search_query)

# ==========================================
# 🔐 AUTHENTICATION & ADMIN ROUTES
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = db.users.find_one({"username": username, "password_hash": password})
            
        if user:
            if user.get('role') == 'sub_admin':
                db.activity_logs.insert_one({
                    "_id": get_next_id('activity_logs'),
                    "full_name": user['full_name'], 
                    "action_description": "Logged into the system.",
                    "timestamp": datetime.now()
                })
                
            session['user_id'] = user['_id']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials. Please try again.")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # 1. Fetch Projects
    match_stage = {} if session.get('role') == 'super_admin' else {"submitted_by": session['user_id']}
    
    pipeline = [
        {"$match": match_stage},
        {"$lookup": {"from": "barangays", "localField": "barangay_id", "foreignField": "_id", "as": "b_info"}},
        {"$unwind": {"path": "$b_info", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"_id": -1}}
    ]
    raw_projects = list(db.projects.aggregate(pipeline))
    
    dashboard_projects = []
    for p in raw_projects:
        p['id'] = p['_id'] 
        p['barangay_name'] = p.get('b_info', {}).get('name', 'Unknown')
        
        # Format dates nicely for the dashboard
        if isinstance(p.get('start_date'), datetime):
            p['start_date'] = p['start_date'].strftime('%Y-%m-%d')
        if isinstance(p.get('target_completion'), datetime):
            p['target_completion'] = p['target_completion'].strftime('%Y-%m-%d')
            
        dashboard_projects.append(p)

    # 2. Fetch all Barangays
    barangays = list(db.barangays.find().sort("name", 1))
    for b in barangays:
        b['id'] = b['_id']
        managers = list(db.users.find({"barangay_id": b['_id'], "role": "sub_admin"}))
        b['manager_name'] = ", ".join([m['full_name'] for m in managers]) if managers else None

    # 3. Fetch Sub-Admins
    sub_admins = []
    if session.get('role') == 'super_admin':
        raw_admins = list(db.users.find({"role": "sub_admin"}))
        for admin in raw_admins:
            admin['id'] = admin['_id']
            b = db.barangays.find_one({"_id": admin.get('barangay_id')})
            admin['barangay_name'] = b['name'] if b else 'Unknown'
            
            last_log = db.activity_logs.find_one(
                {"full_name": admin['full_name'], "action_description": "Logged into the system."},
                sort=[("timestamp", -1)]
            )
            admin['last_login'] = last_log['timestamp'].strftime('%b %d, %Y %I:%M %p') if last_log and 'timestamp' in last_log else None
            sub_admins.append(admin)

    # 4. Donut Chart Math
    status_counts = {'proposed': 0, 'approved': 0, 'in_progress': 0, 'completed': 0}
    for proj in dashboard_projects:
        if proj.get('status') in status_counts:
            status_counts[proj['status']] += 1
            
    donut_data = [
        status_counts['proposed'], status_counts['approved'],
        status_counts['in_progress'], status_counts['completed']
    ]

    # 5. Line Chart Math
    yearly_data = {}
    for proj in dashboard_projects:
        start_raw = proj.get('start_date')
        if start_raw:
            yr = int(str(start_raw)[:4])
            if yr not in yearly_data:
                yearly_data[yr] = {'yr': yr, 'total_budget': 0, 'total_expenses': 0}
            
            budget = float(proj.get('budget', 0))
            yearly_data[yr]['total_budget'] += budget
            if proj.get('status') in ['completed', 'in_progress']:
                yearly_data[yr]['total_expenses'] += budget

    sorted_years = sorted(yearly_data.values(), key=lambda x: x['yr'], reverse=True)[:3]
    sorted_years.reverse() 
    
    chart_years = [str(row['yr']) for row in sorted_years] if sorted_years else ['2024', '2025', '2026']
    chart_budgets = [row['total_budget'] for row in sorted_years] if sorted_years else [0, 0, 0]
    chart_expenses = [row['total_expenses'] for row in sorted_years] if sorted_years else [0, 0, 0]

    # 6. Fetch History Feed
    raw_logs = list(db.activity_logs.find().sort([("timestamp", -1), ("_id", -1)]).limit(50))
    all_logs = []
    for log in raw_logs:
        log['id'] = log['_id']
        if 'timestamp' in log and isinstance(log['timestamp'], datetime):
            log['time_ago'] = log['timestamp'].strftime('%b %d, %I:%M %p')
        else:
            log['time_ago'] = 'Recent'
        all_logs.append(log)

    return render_template('dashboard.html', 
                           projects=dashboard_projects, 
                           barangays=barangays, 
                           sub_admins=sub_admins,
                           donut_data=donut_data,
                           chart_years=chart_years,
                           chart_budgets=chart_budgets,
                           chart_expenses=chart_expenses,
                           all_logs=all_logs)

@app.route('/propose_project', methods=['POST'])
def propose_project():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    title = request.form.get('title')
    specific_location = request.form.get('specific_location')
    budget = float(request.form.get('budget', 0))
    
    # Convert string dates from HTML form into real Datetime objects
    try:
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        target_completion = datetime.strptime(request.form.get('target_completion'), '%Y-%m-%d')
    except:
        start_date = datetime.now()
        target_completion = datetime.now()
        
    user_data = db.users.find_one({"_id": session['user_id']})
    barangay_id = user_data.get('barangay_id', 1) if user_data else 1

    new_project_id = get_next_id('projects')
    
    db.projects.insert_one({
        "_id": new_project_id,
        "title": title,
        "barangay_id": barangay_id,
        "specific_location": specific_location,
        "budget": budget,
        "start_date": start_date,
        "target_completion": target_completion,
        "status": "proposed",
        "submitted_by": session['user_id'],
        "created_at": datetime.now(),
        "images": []
    })
    
    db.activity_logs.insert_one({
        "_id": get_next_id('activity_logs'),
        "full_name": session['full_name'], 
        "action_description": f"Proposed a new project: '{title}'.",
        "timestamp": datetime.now()
    })

    flash("Project proposed successfully!")
    return redirect(url_for('dashboard'))

@app.route('/add_admin', methods=['POST'])
def add_admin():
    if session.get('role') != 'super_admin':
        flash("Unauthorized access.")
        return redirect(url_for('dashboard'))

    full_name = request.form.get('full_name')
    username = request.form.get('username')
    barangay_id = int(request.form.get('barangay_id'))
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if password != confirm_password:
        flash("Error: Passwords do not match!")
        return redirect(url_for('dashboard'))

    if db.users.find_one({"username": username}):
        flash("Error: Username already exists!")
        return redirect(url_for('dashboard'))

    db.users.insert_one({
        "_id": get_next_id('users'),
        "full_name": full_name,
        "username": username,
        "password_hash": password,
        "role": 'sub_admin',
        "barangay_id": barangay_id,
        "created_at": datetime.now()
    })

    flash(f"Success: Sub-Admin account for {full_name} created!")
    return redirect(url_for('dashboard'))

# ==========================================
# ⚡ AJAX API ENDPOINTS
# ==========================================

@app.route('/api/update_status/<int:project_id>', methods=['POST'])
def update_status(project_id):
    if session.get('role') != 'super_admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    new_status = request.json.get('status')
    
    db.projects.update_one({"_id": project_id}, {"$set": {"status": new_status}})
    project = db.projects.find_one({"_id": project_id})
    project_title = project['title'] if project else f"Project #{project_id}"

    clean_status = new_status.replace('_', ' ').title()
    action_msg = f"Changed the status of '{project_title}' to {clean_status}."

    db.activity_logs.insert_one({
        "_id": get_next_id('activity_logs'),
        "full_name": session['full_name'],
        "action_description": action_msg,
        "timestamp": datetime.now()
    })
    
    return jsonify({"status": "success", "message": f"Project marked as {clean_status}!"})

@app.route('/api/delete_log/<int:log_id>', methods=['POST'])
def delete_log(log_id):
    if session.get('role') != 'super_admin':
        return jsonify({'status': 'error', 'message': 'Unauthorized action'}), 403
        
    db.activity_logs.delete_one({"_id": log_id})
    return jsonify({'status': 'success', 'message': 'Log deleted successfully.'})

@app.route('/api/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    if session.get('role') != 'super_admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    db.projects.delete_one({"_id": project_id})
    return jsonify({"status": "success", "message": "Project permanently deleted!"})

@app.route('/api/add_barangay', methods=['POST'])
def add_barangay():
    if session.get('role') != 'super_admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    
    name = request.json.get('name')
    if db.barangays.find_one({"name": name}):
        return jsonify({"status": "error", "message": "Barangay already exists!"})
        
    db.barangays.insert_one({
        "_id": get_next_id('barangays'),
        "name": name
    })
    return jsonify({"status": "success", "message": f"Barangay '{name}' added successfully!"})

@app.route('/api/delete_admin/<int:admin_id>', methods=['POST'])
def delete_admin(admin_id):
    if session.get('role') != 'super_admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
    db.users.delete_one({"_id": admin_id, "role": "sub_admin"})
    return jsonify({"status": "success", "message": "Admin account permanently deleted."})

@app.route('/api/edit_admin/<int:admin_id>', methods=['POST'])
def edit_admin(admin_id):
    if session.get('role') != 'super_admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
    full_name = request.json.get('full_name')
    db.users.update_one({"_id": admin_id, "role": "sub_admin"}, {"$set": {"full_name": full_name}})
    return jsonify({"status": "success", "message": "Admin name updated successfully!"})

@app.route('/api/upload_photo', methods=['POST'])
def upload_photo():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    project_id = int(request.form.get('project_id'))
    if 'photo' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
        
    file = request.files['photo']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"proj_{project_id}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)

        # MongoDB Magic: Push the image directly into the project's array!
        db.projects.update_one({"_id": project_id}, {"$push": {"images": unique_filename}})
        
        project = db.projects.find_one({"_id": project_id})
        project_title = project['title'] if project else f"Project #{project_id}"

        action_msg = f"Uploaded a new progress photo for '{project_title}'."
        db.activity_logs.insert_one({
            "_id": get_next_id('activity_logs'),
            "full_name": session['full_name'], 
            "action_description": action_msg,
            "timestamp": datetime.now()
        })

        return jsonify({"status": "success", "message": "Photo uploaded successfully!"})

# ==========================================
# 🤖 AI CHATBOT SYSTEM
# ==========================================
lemmatizer = WordNetLemmatizer()

try:
    intents = json.loads(open('intents.json').read())
    words = pickle.load(open('words.pkl', 'rb'))
    classes = pickle.load(open('classes.pkl', 'rb'))
    model = load_model('chatbot_model.h5') 
    print("✅ AI Model Loaded Successfully!")
except Exception as e:
    model = None
    print(f"⚠️ Warning: Could not load AI Model. Error: {e}")

def clean_up_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
    return sentence_words

def bow(sentence, words, show_details=True):
    sentence_words = clean_up_sentence(sentence)
    bag = [0]*len(words)
    for s in sentence_words:
        for i, w in enumerate(words):
            if w == s:
                bag[i] = 1
    return(np.array(bag))

def predict_class(sentence, model):
    if model is None:
        return []
    p = bow(sentence, words, show_details=False)
    res = model.predict(np.array([p]))[0]
    ERROR_THRESHOLD = 0.25
    results = [[i, r] for i, r in enumerate(res) if r > ERROR_THRESHOLD]
    results.sort(key=lambda x: x[1], reverse=True)
    return_list = []
    for r in results:
        return_list.append({"intent": classes[r[0]], "probability": str(r[1])})
    return return_list

@app.route('/api/chat', methods=['POST'])
def chat_api():
    if not model:
        return jsonify({"reply": "System Error: AI is currently offline."})

    user_message = request.json.get('message', '').lower()
    ints = predict_class(user_message, model)
    
    if not ints:
        return jsonify({"reply": "I'm sorry, I didn't quite understand that. Could you rephrase?"})

    tag = ints[0]['intent']
    dynamic_tags = ['ask_budget', 'ask_location', 'ask_proposer', 'ask_date', 'ask_status']
    
    if tag in dynamic_tags:
        pipeline = [
            {"$lookup": {"from": "barangays", "localField": "barangay_id", "foreignField": "_id", "as": "b_info"}},
            {"$unwind": {"path": "$b_info", "preserveNullAndEmptyArrays": True}},
            {"$lookup": {"from": "users", "localField": "submitted_by", "foreignField": "_id", "as": "u_info"}},
            {"$unwind": {"path": "$u_info", "preserveNullAndEmptyArrays": True}}
        ]
        all_projects = list(db.projects.aggregate(pipeline))

        target_project = None
        user_msg = user_message.lower()
        
        for p in all_projects:
            db_title = p.get('title', '').lower()
            if db_title in user_msg:
                target_project = p
                break
                
            words_to_remove = ["how", "much", "is", "the", "budget", "for", "what", "where", "status", "of", "when", "who", "proposed", "?", "tell", "me", "about", "project"]
            clean_words = [w for w in user_msg.split() if w not in words_to_remove]
            search_keyword = " ".join(clean_words).strip()
            
            if len(search_keyword) >= 4 and search_keyword in db_title:
                target_project = p
                break

        if target_project:
            title = target_project['title']
            b_name = target_project.get('b_info', {}).get('name', 'Unknown')
            proposer = target_project.get('u_info', {}).get('full_name', 'Unknown')
            start = target_project.get('start_date').strftime('%Y-%m-%d') if isinstance(target_project.get('start_date'), datetime) else target_project.get('start_date')
            end = target_project.get('target_completion').strftime('%Y-%m-%d') if isinstance(target_project.get('target_completion'), datetime) else target_project.get('target_completion')

            if tag == 'ask_budget':
                return jsonify({"reply": f"The allocated budget for the '{title}' is ₱{target_project.get('budget', 0):,.2f}."})
            elif tag == 'ask_location':
                return jsonify({"reply": f"The '{title}' is located at {target_project.get('specific_location')}, {b_name}."})
            elif tag == 'ask_proposer':
                return jsonify({"reply": f"The '{title}' was officially proposed by {proposer}."})
            elif tag == 'ask_date':
                return jsonify({"reply": f"The '{title}' is scheduled to start on {start} with a target completion of {end}."})
            elif tag == 'ask_status':
                return jsonify({"reply": f"The current status of the '{title}' is: {target_project.get('status', 'unknown').upper()}."})
        else:
            return jsonify({"reply": "I detect you are asking for specific details, but I couldn't find a project with that exact name in your sentence. Could you specify the project title?"})

    elif tag == 'projects':
        live_projects = list(db.projects.find().limit(5))
        if live_projects:
            project_list = ", ".join([f"'{p['title']}' ({p['status']})" for p in live_projects])
            return jsonify({"reply": f"Here are the latest projects from our database: {project_list}."})
        else:
            return jsonify({"reply": "There are currently no active projects."})

    list_of_intents = intents['intents']
    for i in list_of_intents:
        if i['tag'] == tag:
            reply = random.choice(i['responses'])
            return jsonify({"reply": reply})

    return jsonify({"reply": "I'm here to help with OpenMuni!"})

if __name__ == '__main__':
    app.run(debug=True)