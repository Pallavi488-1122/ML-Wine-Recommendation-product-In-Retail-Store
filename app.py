from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import accuracy_score
import numpy as np
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'wine_secret_key_2024'

def init_db():
    conn = sqlite3.connect('wines.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS wines
                 (id INTEGER PRIMARY KEY,
                  name TEXT, type TEXT, taste TEXT,
                  occasion TEXT, budget TEXT,
                  description TEXT, price TEXT, rating REAL)''')

    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY,
                  username TEXT UNIQUE, email TEXT UNIQUE,
                  password TEXT, created_at TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY,
                  user_id INTEGER, taste TEXT, occasion TEXT,
                  budget TEXT, wine_type TEXT,
                  recommended_wine TEXT, searched_at TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS ratings
                 (id INTEGER PRIMARY KEY,
                  user_id INTEGER, wine_name TEXT,
                  rating INTEGER, review TEXT,
                  created_at TEXT)''')

    wines = [
        ('Sula Chenin Blanc', 'white', 'sweet', 'casual', 'low', 'Light and fruity white wine', '₹400', 4.2),
        ('Jacob Creek Shiraz', 'red', 'dry', 'dinner', 'medium', 'Bold and spicy red wine', '₹800', 4.5),
        ('Fratelli Sangiovese', 'red', 'dry', 'party', 'medium', 'Smooth Italian style red wine', '₹900', 4.3),
        ('Sula Brut', 'sparkling', 'semi-dry', 'party', 'medium', 'Celebratory sparkling wine', '₹700', 4.4),
        ('Grover Zampa La Reserve', 'red', 'dry', 'gift', 'high', 'Premium red wine perfect for gifting', '₹1800', 4.7),
        ('Four Seasons White Zinfandel', 'rose', 'sweet', 'casual', 'low', 'Light and refreshing rose wine', '₹450', 4.1),
        ('Sula Dindori Shiraz', 'red', 'semi-dry', 'dinner', 'medium', 'Award winning Indian red wine', '₹850', 4.6),
        ('York Arros', 'red', 'dry', 'gift', 'high', 'Elegant premium red wine', '₹2000', 4.8),
        ('Fratelli Vitae', 'white', 'dry', 'dinner', 'medium', 'Crisp and refreshing white wine', '₹750', 4.3),
        ('Sula Riesling', 'white', 'sweet', 'gift', 'medium', 'Floral and sweet white wine', '₹600', 4.2),
        ('Myra Vineyards Cabernet', 'red', 'dry', 'party', 'high', 'Rich full bodied red wine', '₹1600', 4.5),
        ('Four Seasons Barrique', 'red', 'semi-dry', 'casual', 'low', 'Easy drinking everyday red wine', '₹480', 4.0),
        ('Chandon Brut', 'sparkling', 'dry', 'party', 'high', 'Premium sparkling celebration wine', '₹1900', 4.7),
        ('Sula Sauvignon Blanc', 'white', 'dry', 'casual', 'low', 'Fresh and zesty white wine', '₹420', 4.1),
        ('Grover Zampa Chene', 'white', 'semi-dry', 'dinner', 'high', 'Oak aged premium white wine', '₹1700', 4.6),
    ]

    c.execute('DELETE FROM wines')
    c.executemany('INSERT INTO wines (name, type, taste, occasion, budget, description, price, rating) VALUES (?,?,?,?,?,?,?,?)', wines)
    conn.commit()
    conn.close()

def get_encoded_data():
    conn = sqlite3.connect('wines.db')
    df = pd.read_sql_query('SELECT * FROM wines', conn)
    conn.close()

    taste_map = {'sweet': 0, 'semi-dry': 1, 'dry': 2}
    occasion_map = {'casual': 0, 'party': 1, 'dinner': 2, 'gift': 3}
    budget_map = {'low': 0, 'medium': 1, 'high': 2}
    type_map = {'white': 0, 'rose': 1, 'red': 2, 'sparkling': 3}

    df['taste_enc'] = df['taste'].map(taste_map)
    df['occasion_enc'] = df['occasion'].map(occasion_map)
    df['budget_enc'] = df['budget'].map(budget_map)
    df['type_enc'] = df['type'].map(type_map)

    X = df[['taste_enc', 'occasion_enc', 'budget_enc', 'type_enc']].values
    y = df['id'].values

    return X, y, taste_map, occasion_map, budget_map, type_map

def train_model():
    X, y, taste_map, occasion_map, budget_map, type_map = get_encoded_data()

    knn = KNeighborsClassifier(n_neighbors=3)
    knn.fit(X, y)

    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X, y)

    return knn, rf, taste_map, occasion_map, budget_map, type_map

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/index')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        try:
            conn = sqlite3.connect('wines.db')
            c = conn.cursor()
            c.execute('INSERT INTO users (username, email, password, created_at) VALUES (?,?,?,?)',
                     (username, email, password, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            conn.close()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except:
            flash('Username or email already exists!', 'error')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('wines.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username=?', (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/recommend', methods=['POST'])
def recommend():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    taste = request.form['taste']
    occasion = request.form['occasion']
    budget = request.form['budget']
    wine_type = request.form['wine_type']

    knn, rf, taste_map, occasion_map, budget_map, type_map = train_model()

    input_data = np.array([[
        taste_map[taste],
        occasion_map[occasion],
        budget_map[budget],
        type_map[wine_type]
    ]])

    distances, indices = knn.kneighbors(input_data)

    conn = sqlite3.connect('wines.db')
    df = pd.read_sql_query('SELECT * FROM wines', conn)

    recommendations = []
    for idx in indices[0]:
        wine = df.iloc[idx]
        recommendations.append({
            'name': wine['name'],
            'type': wine['type'].title(),
            'description': wine['description'],
            'price': wine['price'],
            'rating': wine['rating']
        })

    c = conn.cursor()
    c.execute('INSERT INTO history (user_id, taste, occasion, budget, wine_type, recommended_wine, searched_at) VALUES (?,?,?,?,?,?,?)',
             (session['user_id'], taste, occasion, budget, wine_type,
              recommendations[0]['name'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

    return render_template('result.html',
                         recommendations=recommendations,
                         taste=taste, occasion=occasion,
                         budget=budget, wine_type=wine_type)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('wines.db')
    c = conn.cursor()

    c.execute('SELECT COUNT(*) FROM history')
    total_searches = c.fetchone()[0]

    c.execute('SELECT recommended_wine, COUNT(*) as cnt FROM history GROUP BY recommended_wine ORDER BY cnt DESC LIMIT 1')
    popular = c.fetchone()
    popular_wine = popular[0] if popular else 'N/A'

    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]

    c.execute('SELECT budget, COUNT(*) FROM history GROUP BY budget')
    budget_data = c.fetchall()

    c.execute('SELECT wine_type, COUNT(*) FROM history GROUP BY wine_type')
    type_data = c.fetchall()

    c.execute('SELECT taste, COUNT(*) FROM history GROUP BY taste')
    taste_data = c.fetchall()

    c.execute('SELECT taste, occasion, budget, wine_type, recommended_wine, searched_at FROM history WHERE user_id=? ORDER BY searched_at DESC LIMIT 5', (session['user_id'],))
    user_history = c.fetchall()

    # Wine popularity
    c.execute('SELECT recommended_wine, COUNT(*) as cnt FROM history GROUP BY recommended_wine ORDER BY cnt DESC LIMIT 8')
    wine_popularity = c.fetchall()

    conn.close()

    return render_template('dashboard.html',
                         total_searches=total_searches,
                         popular_wine=popular_wine,
                         total_users=total_users,
                         budget_data=budget_data,
                         type_data=type_data,
                         taste_data=taste_data,
                         user_history=user_history,
                         wine_popularity=wine_popularity)

@app.route('/ml_comparison')
def ml_comparison():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    X, y, _, _, _, _ = get_encoded_data()

    models = {
        'KNN': KNeighborsClassifier(n_neighbors=3),
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
        'Decision Tree': DecisionTreeClassifier(random_state=42)
    }

    results = []
    for name, model in models.items():
        model.fit(X, y)
        train_acc = accuracy_score(y, model.predict(X))
        results.append({
            'name': name,
            'cv_accuracy': round(train_acc * 100, 2),
            'train_accuracy': round(train_acc * 100, 2),
            'std': 0.0
        })

    return render_template('ml_comparison.html', results=results)

@app.route('/search')
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    query = request.args.get('query', '')
    wine_type = request.args.get('wine_type', '')
    budget = request.args.get('budget', '')
    min_rating = request.args.get('min_rating', 0)

    conn = sqlite3.connect('wines.db')
    c = conn.cursor()

    sql = 'SELECT * FROM wines WHERE 1=1'
    params = []

    if query:
        sql += ' AND name LIKE ?'
        params.append(f'%{query}%')
    if wine_type:
        sql += ' AND type=?'
        params.append(wine_type)
    if budget:
        sql += ' AND budget=?'
        params.append(budget)
    if min_rating:
        sql += ' AND rating >= ?'
        params.append(float(min_rating))

    c.execute(sql, params)
    wines = c.fetchall()
    conn.close()

    return render_template('search.html', wines=wines, query=query,
                         wine_type=wine_type, budget=budget, min_rating=min_rating)

@app.route('/rate_wine', methods=['POST'])
def rate_wine():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    wine_name = request.form['wine_name']
    rating = request.form['rating']
    review = request.form['review']

    conn = sqlite3.connect('wines.db')
    c = conn.cursor()
    c.execute('INSERT INTO ratings (user_id, wine_name, rating, review, created_at) VALUES (?,?,?,?,?)',
             (session['user_id'], wine_name, rating, review,
              datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

    flash('Rating submitted successfully! Thank you!', 'success')
    return redirect(url_for('search'))

@app.route('/reviews')
def reviews():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('wines.db')
    c = conn.cursor()
    c.execute('''SELECT r.wine_name, r.rating, r.review, r.created_at, u.username
                 FROM ratings r JOIN users u ON r.user_id = u.id
                 ORDER BY r.created_at DESC''')
    all_reviews = c.fetchall()
    conn.close()

    return render_template('reviews.html', reviews=all_reviews)
@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from flask import make_response
    import io

    taste = request.form.get('taste', '')
    occasion = request.form.get('occasion', '')
    budget = request.form.get('budget', '')
    wine_type = request.form.get('wine_type', '')
    wines_str = request.form.get('wines', '')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("🍷 Wine Recommendation Report", styles['Title']))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Generated for: {session['username']}", styles['Normal']))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 20))

    story.append(Paragraph("Your Preferences:", styles['Heading2']))
    data = [
        ['Taste', taste.title()],
        ['Occasion', occasion.title()],
        ['Budget', budget.title()],
        ['Wine Type', wine_type.title()],
    ]
    t = Table(data, colWidths=[150, 300])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#6b0f1a')),
        ('TEXTCOLOR', (0,0), (0,-1), colors.white),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 11),
        ('ROWBACKGROUNDS', (1,0), (1,-1), [colors.HexColor('#fff5f5'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e0c0c0')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    story.append(Paragraph("Recommended Wines:", styles['Heading2']))
    for i, wine in enumerate(wines_str.split('|')):
        if wine:
            story.append(Paragraph(f"{i+1}. {wine}", styles['Normal']))
            story.append(Spacer(1, 5))

    story.append(Spacer(1, 30))
    story.append(Paragraph("Generated by Wine Recommendation System", styles['Normal']))

    doc.build(story)
    buffer.seek(0)

    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=wine_recommendation.pdf'
    return response

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('chatbot.html')

@app.route('/chat_api', methods=['POST'])
def chat_api():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_message = request.json.get('message', '')

    # Wine knowledge base
    wine_info = {
        'red': 'Red wines include Shiraz, Cabernet, Sangiovese. Best for dinner and gifting.',
        'white': 'White wines include Chenin Blanc, Sauvignon Blanc, Riesling. Light and refreshing.',
        'rose': 'Rose wines are light pink, slightly sweet. Great for casual occasions.',
        'sparkling': 'Sparkling wines like Brut are perfect for parties and celebrations.',
        'sweet': 'Sweet wines have higher sugar content. Great for dessert or casual drinking.',
        'dry': 'Dry wines have less sugar. Perfect for dinner pairing.',
        'budget': 'We have wines from ₹400 to ₹2000 range.',
        'recommend': 'Go to Home page and fill preferences to get ML-based recommendations!',
        'sula': 'Sula is India\'s most popular wine brand. They make Chenin Blanc, Riesling, Dindori Shiraz.',
        'grover': 'Grover Zampa makes premium Indian wines like La Reserve and Chene.',
    }

    response = "I'm your Wine Assistant! 🍷 "
    msg_lower = user_message.lower()

    matched = False
    for key, value in wine_info.items():
        if key in msg_lower:
            response = value
            matched = True
            break

    if not matched:
        if 'hello' in msg_lower or 'hi' in msg_lower:
            response = f"Hello {session['username']}! 🍷 I'm your Wine Assistant. Ask me about wines, types, or recommendations!"
        elif 'help' in msg_lower:
            response = "I can help you with: wine types (red, white, rose, sparkling), taste preferences, budget options, and wine brands!"
        elif 'thank' in msg_lower:
            response = "You're welcome! Enjoy your wine! 🍷"
        else:
            response = "I can answer questions about wine types, tastes, budgets, and brands. Try asking about 'red wine', 'sweet wine', or 'Sula'!"

    return jsonify({'response': response})
@app.route('/advanced_ml')
def advanced_ml():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    from sklearn.metrics import precision_score, recall_score, f1_score

    X, y, _, _, _, _ = get_encoded_data()

    models = {
        'KNN': (KNeighborsClassifier(n_neighbors=3), 'Simple & Fast recommendations'),
        'Random Forest': (RandomForestClassifier(n_estimators=100, random_state=42), 'High accuracy ensemble'),
        'Decision Tree': (DecisionTreeClassifier(random_state=42), 'Easy to interpret')
    }

    results = []
    for name, (model, best_for) in models.items():
        model.fit(X, y)
        y_pred = model.predict(X)
        acc = accuracy_score(y, y_pred) * 100
        prec = precision_score(y, y_pred, average='weighted', zero_division=0) * 100
        rec = recall_score(y, y_pred, average='weighted', zero_division=0) * 100
        f1 = f1_score(y, y_pred, average='weighted', zero_division=0) * 100
        results.append({
            'name': name,
            'accuracy': round(acc, 1),
            'precision': round(prec, 1),
            'recall': round(rec, 1),
            'f1': round(f1, 1),
            'best_for': best_for
        })

    best_accuracy = max(r['accuracy'] for r in results)
    best_precision = max(r['precision'] for r in results)
    best_recall = max(r['recall'] for r in results)
    best_f1 = max(r['f1'] for r in results)

    return render_template('advanced_ml.html',
                         results=results,
                         best_accuracy=best_accuracy,
                         best_precision=best_precision,
                         best_recall=best_recall,
                         best_f1=best_f1)
@app.route('/wine_map')
def wine_map():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('wine_map.html')
if __name__ == '__main__':
    init_db()
    app.run(debug=True)