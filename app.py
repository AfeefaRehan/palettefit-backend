import os
import re
import ssl
import smtplib
from urllib.parse import urlparse
from email.message import EmailMessage

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import google.generativeai as genai

# ----------------- Setup & Config -----------------
load_dotenv()

app = Flask(__name__)

# CORS: env-driven; multiple origins allowed (comma-separated)
ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://127.0.0.1:5500,http://localhost:5500"
).split(",")
CORS(
    app,
    resources={r"/api/*": {"origins": [o.strip() for o in ALLOWED_ORIGINS]}},
    supports_credentials=True
)

# Google Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("No GOOGLE_API_KEY set for Flask application")
genai.configure(api_key=GOOGLE_API_KEY)
system_instruction = "You are a sophisticated Personalized Fashion Stylist AI, designed specifically for a Pakistani audience."
model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=system_instruction)

# Uploads (ephemeral unless you mount a disk on Render)
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Email (use env vars in production)
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ----------------- Helpers -----------------
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    """
    Prefer DATABASE_URL (Render/Heroku style). Fallback to discrete env vars for local dev.
    On Render, sslmode=require is important.
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        u = urlparse(db_url)
        return psycopg2.connect(
            dbname=u.path.lstrip("/"),
            user=u.username,
            password=u.password,
            host=u.hostname,
            port=u.port or 5432,
            sslmode="require",
        )
    # Local dev fallback (no hardcoded password defaults)
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "Palleteandfit"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", "")
    )

def send_support_email(sender_email: str, message_text: str):
    host = (os.getenv("SMTP_HOST") or "").strip()
    port = int(os.getenv("SMTP_PORT") or 587)
    user = (os.getenv("SMTP_USER") or "").strip()
    pwd  = (os.getenv("SMTP_PASS") or "").strip()
    use_tls = (os.getenv("SMTP_USE_TLS") or "1").strip() == "1"
    mail_from = (os.getenv("MAIL_FROM") or user).strip()
    contact_to = (os.getenv("CONTACT_TO") or user).strip()

    if not (host and user and pwd):
        return False, "SMTP not configured"

    try:
        msg = EmailMessage()
        msg["Subject"] = f"New contact message from {sender_email}"
        msg["From"] = mail_from
        msg["To"] = contact_to
        msg["Reply-To"] = sender_email
        msg.set_content(f"From: {sender_email}\n\n{message_text}")

        ctx = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.ehlo()
            if use_tls:
                s.starttls(context=ctx)
                s.ehlo()
            s.login(user, pwd)
            s.send_message(msg)

        return True, None
    except Exception as e:
        print("SMTP ERROR:", e)
        return False, str(e)

# ----------------- Routes -----------------
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/api/hello")
def hello():
    return jsonify({"message": "Hello from Flask backend!"})

# ---------- Auth ----------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    phone    = data.get("phone")
    name = data.get("name")
    age = data.get("age")
    gender = data.get("gender")
    skin_tone = data.get("skin_tone")
    weight = data.get("weight")
    body_length = data.get("body_length")
    upper_width = data.get("upper_width")
    lower_width = data.get("lower_width")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    try:
        hashed_pw = generate_password_hash(password)
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users
                      (username, password, phone, name, age, gender, skin_tone, weight, body_length, upper_width, lower_width)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id;
                    """,
                    (username, hashed_pw, phone, name, age, gender, skin_tone, weight, body_length, upper_width, lower_width)
                )
                user_id = cur.fetchone()[0]
                return jsonify({"id": user_id, "username": username}), 201
    except psycopg2.IntegrityError:
        return jsonify({"error": "User with this email already exists."}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE username=%s", (email,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and check_password_hash(row[0], password):
            return jsonify({"success": True}), 200
        else:
            return jsonify({"error": "Invalid email or password"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------- Profile ----------
@app.route("/api/profile", methods=["POST"])
def profile():
    data = request.get_json() or {}
    email = data.get("email")
    name = data.get("name")
    age = data.get("age")
    gender = data.get("gender")
    skin_tone = data.get("skin_tone")
    weight = data.get("weight")
    body_length = data.get("body_length")
    upper_width = data.get("upper_width")
    lower_width = data.get("lower_width")
    phone = data.get("phone")

    if not email:
        return jsonify({"error": "Missing email"}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE users SET
              name=%s, age=%s, gender=%s, skin_tone=%s,
              weight=%s, body_length=%s, upper_width=%s, lower_width=%s, phone=%s
            WHERE username=%s
            """,
            (name, age, gender, skin_tone, weight, body_length, upper_width, lower_width, phone, email)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/get_profile", methods=["POST"])
def get_profile():
    data = request.get_json() or {}
    email = data.get("email")
    if not email:
        return jsonify({"error": "Missing email"}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, age, gender, skin_tone, weight, body_length, upper_width, lower_width, phone, username,
                   last_recommendation, best_color, worst_color, light_tones_percent, dark_tones_percent,
                   western_percent, eastern_percent, personalized_analysis
            FROM users WHERE username=%s
            """,
            (email,)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            return jsonify({
                "name": user[0], "age": user[1], "gender": user[2], "skin_tone": user[3],
                "weight": user[4], "body_length": user[5], "upper_width": user[6], "lower_width": user[7],
                "phone": user[8], "email": user[9],
                "last_recommendation": user[10], "best_color": user[11], "worst_color": user[12],
                "light_tones_percent": user[13], "dark_tones_percent": user[14],
                "western_percent": user[15], "eastern_percent": user[16],
                "personalized_analysis": user[17]
            }), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/body", methods=["POST"])
def update_body():
    data = request.get_json() or {}
    email = data.get("email")
    weight = data.get("weight")
    body_length = data.get("body_length")
    upper_width = data.get("upper_width")
    lower_width = data.get("lower_width")
    if not email:
        return jsonify({"error": "Missing email"}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE users SET
              weight=%s, body_length=%s, upper_width=%s, lower_width=%s
            WHERE username=%s
            """,
            (weight, body_length, upper_width, lower_width, email)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------- Products ----------
@app.route("/api/products", methods=["GET"])
def get_all_products():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, description, image_url, gender, category FROM products")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    products = [
        {
            "id": r[0], "title": r[1], "description": r[2], "image_url": r[3],
            "gender": r[4], "category": r[5]
        }
        for r in rows
    ]
    return jsonify(products)

@app.route("/api/products/category/<category>", methods=["GET"])
def get_products_by_category(category):
    gender = request.args.get("gender")
    conn = get_db_connection()
    cur = conn.cursor()
    if gender:
        cur.execute(
            "SELECT id, title, description, image_url, gender, category FROM products WHERE category=%s AND gender=%s",
            (category, gender)
        )
    else:
        cur.execute(
            "SELECT id, title, description, image_url, gender, category FROM products WHERE category=%s",
            (category,)
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    products = [
        {
            "id": r[0], "title": r[1], "description": r[2], "image_url": r[3],
            "gender": r[4], "category": r[5]
        }
        for r in rows
    ]
    return jsonify(products)

@app.route("/api/products", methods=["POST"])
def add_product():
    # multipart upload path
    if "image_file" in request.files:
        files = request.files.getlist("image_file")
        if files and files[0].filename != "":
            title = request.form.get("title")
            description = request.form.get("description")
            gender = request.form.get("gender")
            category = request.form.get("category")
            responses = []
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
                    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    file.save(file_path)
                    image_url = f"/uploads/{filename}"
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO products (title, description, image_url, gender, category) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                        (title, description, image_url, gender, category)
                    )
                    new_id = cur.fetchone()[0]
                    conn.commit()
                    cur.close()
                    conn.close()
                    responses.append({"id": new_id, "image_url": image_url})
            return jsonify(responses), 201

    # JSON path
    data = request.get_json() or {}
    if data:
        title = data.get("title")
        description = data.get("description")
        category = data.get("category")
        image_url = data.get("image_url")
        gender = data.get("gender")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (title, description, image_url, gender, category) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (title, description, image_url, gender, category)
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"id": new_id, "image_url": image_url}), 201

    return jsonify({"error": "No image or data provided"}), 400

@app.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    if "image_file" in request.files and request.files["image_file"].filename != "":
        file = request.files["image_file"]
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            image_url = f"/uploads/{filename}"
        else:
            return jsonify({"error": "Invalid file type"}), 400
        title = request.form.get("title")
        description = request.form.get("description")
        gender = request.form.get("gender")
        category = request.form.get("category")
    else:
        data = request.get_json() or {}
        title = data.get("title")
        description = data.get("description")
        image_url = data.get("image_url")
        gender = data.get("gender")
        category = data.get("category")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE products SET title=%s, description=%s, image_url=%s, gender=%s, category=%s WHERE id=%s",
        (title, description, image_url, gender, category, product_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id=%s", (product_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True})

# ---------- Recommendations (Gemini) ----------
@app.route("/api/recommendation", methods=["POST"])
def recommendation():
    data = request.get_json() or {}
    email = data.get("email")
    user_query = data.get("query")
    if not email or not user_query:
        return jsonify({"error": "Missing email or query"}), 400

    # fetch profile (best-effort)
    profile = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, age, gender, skin_tone, weight, body_length, upper_width, lower_width
            FROM users WHERE username=%s
            """,
            (email,)
        )
        profile = cur.fetchone()
        cur.close()
        conn.close()
    except Exception:
        profile = None

    if profile:
        name, age, gender, skin_tone, weight, body_length, upper_width, lower_width = profile
        user_profile_context = (
            f"User profile:\n"
            f"- Name: {name}\n"
            f"- Age: {age}\n"
            f"- Gender: {gender}\n"
            f"- Skin tone: {skin_tone}\n"
            f"- Weight: {weight} kg\n"
            f"- Body length: {body_length} in\n"
            f"- Upper body width: {upper_width} in\n"
            f"- Lower body width: {lower_width} in\n"
        )
    else:
        user_profile_context = "No user profile found."

    user_context_prompt = (
        f"{user_profile_context}\n\n"
        f"The user asks: {user_query}\n"
        "Give a detailed, friendly, practical fashion recommendation for a Pakistani audience using this user's info. "
        "Suggest the best and worst colors, recommend percentage fit for lighter/darker tones and western/eastern styles, "
        "and include a personalized analysis/tip for the user."
    )

    try:
        # Per-request generation (no shared global chat state)
        response = model.generate_content(user_context_prompt)
        ai_text = response.text
    except Exception as e:
        return jsonify({"error": f"AI error: {str(e)}"}), 500

    # log chat (best-effort)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chatbot_logs (user_email, question, bot_response) VALUES (%s, %s, %s)",
            (email, user_query, ai_text)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Could not save chatbot log:", e)

    # extract fields (best-effort)
    def extract_ai_fields(text: str):
        fields = {
            "best_color": None,
            "worst_color": None,
            "light_tones_percent": None,
            "dark_tones_percent": None,
            "western_percent": None,
            "eastern_percent": None,
            "personalized_analysis": None
        }
        patterns = {
            "best_color": r"Best color: ?([^\n]+)",
            "worst_color": r"Worst color: ?([^\n]+)",
            "light_tones_percent": r"Light tones: ?(\d+)",
            "dark_tones_percent": r"Dark tones: ?(\d+)",
            "western_percent": r"Western styles?: ?(\d+)",
            "eastern_percent": r"Eastern styles?: ?(\d+)",
            "personalized_analysis": r"Personalized tip: ?([^\n]+)"
        }
        for key, pat in patterns.items():
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                if "percent" in key and val.isdigit():
                    val = int(val)
                fields[key] = val
        if not fields["personalized_analysis"]:
            fields["personalized_analysis"] = text
        return fields

    extracted = extract_ai_fields(ai_text)

    # save extracted fields (best-effort)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE users SET
              last_recommendation=%s,
              best_color=%s,
              worst_color=%s,
              light_tones_percent=%s,
              dark_tones_percent=%s,
              western_percent=%s,
              eastern_percent=%s,
              personalized_analysis=%s
            WHERE username=%s
            """,
            (
                ai_text,
                extracted["best_color"],
                extracted["worst_color"],
                extracted["light_tones_percent"],
                extracted["dark_tones_percent"],
                extracted["western_percent"],
                extracted["eastern_percent"],
                extracted["personalized_analysis"],
                email,
            )
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Could not save recommendation details:", e)

    return jsonify({"recommendation": ai_text})

# ---------- Wishlist ----------
@app.route("/api/wishlist", methods=["GET"])
def get_wishlist():
    email = request.args.get("email")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.id, p.title, p.description, p.image_url, p.gender, p.category
        FROM wishlist w
        JOIN products p ON w.product_id = p.id
        WHERE w.user_email = %s
        """,
        (email,)
    )
    items = cur.fetchall()
    cur.close()
    conn.close()
    wishlist = [
        {
            "id": r[0], "title": r[1], "description": r[2], "image_url": r[3],
            "gender": r[4], "category": r[5]
        }
        for r in items
    ]
    return jsonify({"wishlist": wishlist})

@app.route("/api/wishlist", methods=["POST"])
def add_to_wishlist():
    data = request.get_json() or {}
    email = data.get("email")
    product_id = data.get("product_id")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM wishlist WHERE user_email=%s AND product_id=%s", (email, product_id))
    if not cur.fetchone():
        cur.execute("INSERT INTO wishlist (user_email, product_id) VALUES (%s, %s)", (email, product_id))
        conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "added"})

@app.route("/api/wishlist", methods=["DELETE"])
def remove_from_wishlist():
    data = request.get_json() or {}
    email = data.get("email")
    product_id = data.get("product_id")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM wishlist WHERE user_email=%s AND product_id=%s", (email, product_id))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "removed"})

# ---------- Contact ----------
@app.route("/api/contact", methods=["POST"])
def contact():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip()
    message = (data.get("message") or "").strip()

    if not EMAIL_REGEX.match(email):
        return jsonify({"status": "error", "msg": "Invalid email"}), 400
    if len(message) == 0:
        return jsonify({"status": "error", "msg": "Message required"}), 400

    # save to DB (best-effort)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO contact_messages (email, message) VALUES (%s,%s);", (email, message))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Contact form DB error:", e)

    mailed, err = send_support_email(email, message)

    payload = {"status": "success", "msg": "Received", "email_sent": bool(mailed)}
    if os.getenv("DEBUG_CONTACT_RESPONSE") == "1":  # expose debug only if explicitly enabled
        payload["debug"] = err
    return jsonify(payload), 200

# ---------- Admin ----------
@app.route("/api/admin/total-users")
def admin_total_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return jsonify({"total_users": count})

@app.route("/api/admin/wishlist-gender")
def admin_wishlist_gender():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT u.gender, COUNT(*) FROM wishlist w
        JOIN users u ON w.user_email = u.username
        GROUP BY u.gender
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({row[0] if row[0] else "Unknown": row[1] for row in rows})

@app.route("/api/admin/most-wishlisted")
def admin_most_wishlisted():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.title, COUNT(*) as cnt FROM wishlist w
        JOIN products p ON w.product_id = p.id
        GROUP BY p.title ORDER BY cnt DESC LIMIT 5
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({"labels": [r[0] for r in rows], "counts": [r[1] for r in rows]})

@app.route("/api/admin/skin-tone")
def admin_skin_tone():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT skin_tone, COUNT(*) FROM users GROUP BY skin_tone")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({"labels": [r[0] if r[0] else "Unknown" for r in rows], "counts": [r[1] for r in rows]})

@app.route("/api/admin/age-group")
def admin_age_group():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            CASE
                WHEN age BETWEEN 13 AND 18 THEN '13-18'
                WHEN age BETWEEN 19 AND 25 THEN '19-25'
                WHEN age BETWEEN 26 AND 35 THEN '26-35'
                WHEN age BETWEEN 36 AND 50 THEN '36-50'
                ELSE '50+'
            END as age_group,
            COUNT(*)
        FROM users
        GROUP BY age_group
        ORDER BY age_group
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({"labels": [r[0] for r in rows], "counts": [r[1] for r in rows]})

@app.route("/api/admin/recent-wishlist")
def admin_recent_wishlist():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT w.user_email, p.title, w.id FROM wishlist w
        JOIN products p ON w.product_id = p.id
        ORDER BY w.id DESC LIMIT 10
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"user": r[0], "product": r[1]} for r in rows])

@app.route("/api/admin/chatbot-logs")
def admin_chatbot_logs():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT user_email, question, bot_response, created_at
        FROM chatbot_logs
        ORDER BY created_at DESC
        LIMIT 10
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    logs = [
        {
            "user": r[0],
            "question": r[1],
            "bot": r[2],
            "time": r[3].strftime("%Y-%m-%d %H:%M") if r[3] else ""
        }
        for r in rows
    ]
    return jsonify(logs)

@app.route("/api/users", methods=["GET"])
def admin_get_all_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, username, gender, age, skin_tone, created_at FROM users ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    users = [
        {
            "id": r[0],
            "name": r[1] or "",
            "email": r[2],
            "gender": r[3] or "",
            "age": r[4] or "",
            "skintone": r[5] or "",
            "joined": r[6].strftime("%Y-%m-%d %H:%M") if r[6] else ""
        }
        for r in rows
    ]
    return jsonify(users)

@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/messages", methods=["GET"])
def admin_get_messages():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT user_email, question, bot_response, created_at
        FROM chatbot_logs
        ORDER BY created_at DESC
        LIMIT 100
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    logs = [
        {
            "user": r[0],
            "question": r[1],
            "reply": r[2],
            "date": r[3].strftime("%Y-%m-%d %H:%M") if r[3] else ""
        }
        for r in rows
    ]
    return jsonify(logs)

# ----------------- Local dev entrypoint -----------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", "5001")))
