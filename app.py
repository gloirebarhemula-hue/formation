
import os
import json
from datetime import datetime

import cloudinary
import cloudinary.uploader
import cloudinary.api

from dotenv import load_dotenv

from werkzeug.security import check_password_hash, generate_password_hash

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from flask_sqlalchemy import SQLAlchemy


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "dev-secret-key-change-me",
)


# =========================================================
# MEDIA DIRECTORY
# =========================================================

os.makedirs("media", exist_ok=True)


# =========================================================
# CLOUDINARY
# =========================================================

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)


# =========================================================
# DATABASE (TURSO / LOCAL SQLITE)
# =========================================================
if os.getenv("RENDER", "").lower() == "true":
    TURSO_URL = os.getenv("TURSO_DATABASE_URL")
    TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")
    
    if not TURSO_URL:
        raise RuntimeError("TURSO_DATABASE_URL est manquant.")
    if not TURSO_TOKEN:
        raise RuntimeError("TURSO_AUTH_TOKEN est manquant.")
    
    TURSO_URL = TURSO_URL.strip()
    TURSO_TOKEN = TURSO_TOKEN.strip()

    # Nettoyage de l'URL
    if TURSO_URL.startswith("libsql://"):
        TURSO_URL = TURSO_URL[len("libsql://"):]
    if TURSO_URL.startswith("https://"):
        TURSO_URL = TURSO_URL[len("https://"):]
    if TURSO_URL.endswith("/"):
        TURSO_URL = TURSO_URL.rstrip("/")

    # Format de connexion pour éviter l'erreur de redirection 308 :
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"sqlite+libsql://{TURSO_URL}/?authToken={TURSO_TOKEN}&secure=true"
    )
    print("-> Base de données : TURSO")
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///local.db"
    print("-> Base de données : SQLITE LOCAL")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# =========================================================
# APPLICATION SETTINGS
# =========================================================

try:
    x = int(os.getenv("x", "100"))
except ValueError:
    raise RuntimeError("La variable d'environnement 'x' doit être un entier.")


# =========================================================
# ADMIN CODES
# =========================================================

code_clair = os.getenv("CODE", "").split(",")

CODE = [
    c.strip()
    for c in code_clair
    if c.strip()
]

CODE_HASH = [
    generate_password_hash(c)
    for c in CODE
]


# =========================================================
# LOGIN & MODELS
# =========================================================

login_manager = LoginManager(app)
login_manager.login_view = "index"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key = True)
    prenom = db.Column(db.String(20), nullable = False)
    nom = db.Column(db.String(20), nullable = False)
    postnom = db.Column(db.String(20), nullable = False)
    promotion = db.Column(db.String(7), nullable = False)
    code = db.Column(db.String(5), nullable = True)
    role = db.Column(db.String(15), nullable = False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Evenement(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    titre = db.Column(db.String(20), nullable = False)
    message = db.Column(db.Text, nullable = False)
    date_enregistrement = db.Column(db.Date, default = datetime.utcnow)

class Media(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    nom = db.Column(db.String(20), nullable = False)
    description = db.Column(db.Text, nullable = False)
    url = db.Column(db.String(500), nullable = False)
    public_id = db.Column(db.String(500), nullable = False)
    date_enregistrement = db.Column(db.Date, default = datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    if user_id is None or user_id == 'None':
        return None
    try:
        return User.query.get(int(user_id))
    except:
        return None


# =========================================================
# ROUTES
# =========================================================

@app.route("/", methods=['POST', 'GET'])
def index():
    total = User.query.count()
    if request.method == 'POST':
        if total > x:
            flash("temps ecouler")
            pass
        
        action = request.form.get("action")
        
        if action == "Inscription":
            prenom = request.form.get("prenom").title().strip()
            nom = request.form.get("nom").upper().strip()
            postnom = request.form.get("postnom").upper().strip()
            promotion = request.form.get("promotion").lower().strip()
            role = request.form.get("role").lower().strip()
            code = request.form.get("code").strip()

            if User.query.filter_by(nom=nom, postnom=postnom, prenom=prenom).first():
                flash("ce compte existe déjà")
                return redirect(url_for("index"))
                                                            
            if code != "":
                if any(check_password_hash(h, code) for h in CODE_HASH):
                    if User.query.filter_by(code=generate_password_hash(code)).first():
                        flash("ce compte existe déjà")
                        return redirect(url_for("index"))
                    
                    role = "admin"
                else:
                    flash("code incorrect")
                    return redirect(url_for("index"))
                
            codeh = generate_password_hash(code)
                
            user = User(
                nom=nom, 
                postnom=postnom, 
                prenom=prenom, 
                promotion=promotion,
                code=codeh, 
                role=role
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("home"))   

        elif action == "Connection":
            prenom = request.form.get("prenom").title().strip()
            nom = request.form.get("nom").upper().strip()
            postnom = request.form.get("postnom").upper().strip()
            role = request.form.get("role").lower().strip()
            user = User.query.filter_by(nom=nom, postnom=postnom, prenom=prenom, role=role).first()
            if user:
                login_user(user)
                return redirect(url_for("home"))
            flash("compte pas trouver")

    return render_template("index.html", total=total, y=x)



@app.route("/home")
@login_required
def home():
    u = User.query.all()
    n = User.query.count()
    q = request.args.get('q', '').strip()
    return render_template("home.html", users=u, numb=x - n, q=q)



@app.route("/page", methods=['POST', 'GET'])
@login_required
def page():
    all_media = Media.query.order_by(Media.date_enregistrement.desc()).all()
    data = {m.nom: {"description": m.description, "url": m.url, "public_id": m.public_id, "date": m.date_enregistrement} for m in all_media}

    event = Evenement.query.order_by(Evenement.date_enregistrement.desc()).all()

    if request.method == 'POST':
        f = request.files.get("fichier")
        description = request.form.get('description').capitalize()
        nom = request.form.get('nom').capitalize().strip()

        if f and nom:
            ext = f.filename.rsplit('.', 1)[-1]
            newNom = f"{nom}.{ext}"
    
            result = cloudinary.uploader.upload(
                f,
                resource_type="auto",
                public_id=f"media/{nom}"
            )
            existing = Media.query.filter_by(nom=newNom).first()
            if existing:
                existing.description = description
                existing.url = result['secure_url']
                existing.public_id = result['public_id']
            else:
                nouveau = Media(nom=newNom, description=description, url=result['secure_url'], public_id=result['public_id'])
                db.session.add(nouveau)

        db.session.commit()
        flash("media ajouté avec succès !")
        return redirect(url_for('page'))

    fichier = list(data.keys())
    return render_template("page.html", fichiers=fichier, data=data, textes=event)



@app.route("/delete/<nom>")
@login_required
def effacer(nom):
    if current_user.role != "admin":
        return redirect(url_for('index'))
    media = Media.query.filter_by(nom=nom).first()
    if media:
        try:
            cloudinary.uploader.destroy(media.public_id, resource_type="image")
        except:
            try:
                cloudinary.uploader.destroy(media.public_id, resource_type="video")
            except:
                pass
        db.session.delete(media)
        db.session.commit()
    return redirect("/page")



@app.route("/add", methods=['POST'])
@login_required
def ajout():
    if current_user.role != "admin":
        return redirect(url_for('index'))
    titre = request.form.get("titre").upper().strip()
    message = request.form.get("message")

    if titre and message:
        nouvel_event = Evenement(titre=titre, message=message)
        db.session.add(nouvel_event)
        db.session.commit()
    return redirect(url_for('page'))



@app.route("/delete_Event/<int:id>")
@login_required
def effaceEv(id):
    if current_user.role != "admin":
        return redirect(url_for('index'))
    event = Evenement.query.get(id)
    if event:
        db.session.delete(event)
        db.session.commit()

    return redirect('/page')



@app.route("/deconnection")
@login_required
def deconnexion():
    logout_user()
    return redirect(url_for("index"))    



@app.route("/supprimer/<int:user_id>", methods=['POST'])
@login_required
def delete(user_id):
    if current_user.role != "admin":
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Tu ne peux pas te supprimer toi-même")
        return redirect(url_for('home'))
    db.session.delete(user)
    db.session.commit()
    flash(f"L'utilisateur {user.nom} a été supprimé")
    return redirect(url_for('home'))



with app.app_context():
    db.create_all() 
    
if __name__ == "__main__":
    # Binding the app to 0.0.0.0 and dynamically pulling port helps deployment platforms
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
app.py
