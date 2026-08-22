import os
import json
from datetime import datetime
from urllib import response

import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash
from flask import Flask, flash, redirect, render_template, request, send_from_directory, session, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from whitenoise import WhiteNoise

# =========================================================
# INITIALISATION
# =========================================================

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
app.wsgi_app=WhiteNoise(app.wsgi_app,root='static')

os.makedirs('media', exist_ok=True)

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

# =========================================================
# BASE DE DONNÉES (NEON POSTGRESQL / LOCAL)
# =========================================================

if os.getenv("RENDER"):
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
    
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL est manquant dans les variables d'environnement")
    
    # SQLAlchemy requiert 'postgresql://' et non 'postgres://'
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    print("→ Base de données : NEON POSTGRESQL")
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///local.db"
    print("→ Base de données : SQLITE LOCAL")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# =========================================================
# CONFIGURATION VARIABLES GLOBALES & ADMIN
# =========================================================

try:
    x = int(os.getenv("x", "100"))
except (ValueError, TypeError):
    x = 100

code_clair = os.getenv("CODE", "").split(",")
CODE = [c.strip() for c in code_clair if c.strip()]
CODE_HASH = [generate_password_hash(c) for c in CODE]

# =========================================================
# MODELS
# =========================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prenom = db.Column(db.String(50), nullable=False)   # Augmenté à 50
    nom = db.Column(db.String(50), nullable=False)      # Augmenté à 50
    postnom = db.Column(db.String(50), nullable=False)  # Augmenté à 50
    promotion = db.Column(db.String(20), nullable=False)
    code = db.Column(db.String(255), nullable=True)     # Taille suffisante pour le hash
    role = db.Column(db.String(20), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Evenement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date_enregistrement = db.Column(db.Date, default=datetime.utcnow)

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(500), nullable=False)
    public_id = db.Column(db.String(500), nullable=False)
    date_enregistrement = db.Column(db.Date, default=datetime.utcnow)

# =========================================================
# LOGIN MANAGER
# =========================================================


login_manager = LoginManager(app)
login_manager.login_view = 'index'

@login_manager.user_loader
def load_user(user_id):
    if user_id is None or user_id == 'None':
        return None
    try:
        return User.query.get(int(user_id))
    except:
        return None


@app.after_request
def cache(response):
    response.headers["Cache-Control"]="no-cache, must-revalidate,max-age=0"
    response.headers["Pragma"]="no-cache"
    response.headers["Expires"]="0"
    return response

# =========================================================
# ROUTES
# =========================================================


@app.route("/", methods=['POST', 'GET'])
def index():
    total = User.query.count()
    if request.method == 'POST':
        if total >= x:
            flash("Nombre maximum d'inscriptions atteint.")
            return redirect(url_for("index"))

        action = request.form.get("action")

        if action == "Inscription":
            prenom = (request.form.get("prenom") or "").title().strip()
            nom = (request.form.get("nom") or "").upper().strip()
            postnom = (request.form.get("postnom") or "").upper().strip()
            promotion = (request.form.get("promotion") or "").lower().strip()
            role = (request.form.get("role") or "user").lower().strip()
            code_saisi = (request.form.get("code") or "").strip()

            if not prenom or not nom or not postnom:
                flash("Veuillez remplir tous les champs obligatoires.")
                return redirect(url_for("index"))

            # Vérification si l'utilisateur existe déjà
            existing_user = User.query.filter_by(nom=nom, postnom=postnom, prenom=prenom).first()
            if existing_user:
                flash("Ce compte existe déjà.")
                return redirect(url_for("index"))

            code_hash = None
            if code_saisi:
                # Vérifier si le code correspond à la liste d'accès admin
                if any(check_password_hash(h, code_saisi) for h in CODE_HASH):
                    role = "admin"
                    code_hash = generate_password_hash(code_saisi)
                else:
                    flash("Code administrateur incorrect.")
                    return redirect(url_for("index"))

            user = User(
                nom=nom, 
                postnom=postnom, 
                prenom=prenom, 
                promotion=promotion,
                code=code_hash, 
                role=role
            )
            
            try:
                db.session.add(user)
                db.session.commit()
                login_user(user)
                return redirect(url_for("home"))
            except Exception as e:
                db.session.rollback()
                print(f"Erreur SQL : {e}")  # Utile dans les logs Render
                flash("Une erreur est survenue lors de l'inscription.")
                return redirect(url_for("index"))

        elif action == "Connection":
            prenom = (request.form.get("prenom") or "").title().strip()
            nom = (request.form.get("nom") or "").upper().strip()
            postnom = (request.form.get("postnom") or "").upper().strip()
            
            user = User.query.filter_by(nom=nom, postnom=postnom, prenom=prenom).first()
            if user:
                login_user(user)
                return redirect(url_for("home"))
            
            flash("Compte non trouvé.")

    return render_template("index.html", total=total, y=x)

@app.route("/home")
@login_required
def home():
    if not current_user.is_authenticated and not "user_id" in session:
        return redirect(url_for(index))
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
        description = request.form.get('description', '').capitalize()
        nom = request.form.get('nom', '').capitalize().strip()

        if f and nom:
            try:
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
            except Exception as e:
                db.session.rollback() # Prévention de l'erreur 9h9h
                flash(f"Erreur lors de l'ajout du média.")
            
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
        
        try:
            db.session.delete(media)
            db.session.commit()
            flash("Média supprimé avec succès.")
        except Exception as e:
            db.session.rollback() # Prévention de l'erreur 9h9h
            flash("Erreur lors de la suppression dans la base de données.")
            
    return redirect(url_for('page'))

@app.route("/add", methods=['POST'])
@login_required
def ajout():
    if current_user.role != "admin":
        return redirect(url_for('index'))
    titre = request.form.get("titre").upper().strip()
    message = request.form.get("message")

    if titre and message:
        nouvel_event = Evenement(titre=titre, message=message)
        try:
            db.session.add(nouvel_event)
            db.session.commit()
            flash("Événement ajouté.")
        except Exception as e:
            db.session.rollback() # Prévention de l'erreur 9h9h
            flash("Erreur lors de l'ajout de l'événement.")
            
    return redirect(url_for('page'))

@app.route("/delete_Event/<int:id>")
@login_required
def effaceEv(id):
    if current_user.role != "admin":
        return redirect(url_for('index'))
    event = Evenement.query.get(id)
    if event:
        try:
            db.session.delete(event)
            db.session.commit()
            flash("Événement supprimé.")
        except Exception as e:
            db.session.rollback() # Prévention de l'erreur 9h9h
            flash("Erreur lors de la suppression de l'événement.")
            
    return redirect(url_for('page'))

@app.route("/deconnection")
@login_required
def deconnexion():
    session.clear()
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
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f"L'utilisateur {user.nom} a été supprimé")
    except Exception as e:
        db.session.rollback() # Prévention de l'erreur 9h9h
        flash("Erreur lors de la suppression de l'utilisateur.")
        
    return redirect(url_for('home'))

with app.app_context():
    db.create_all() 
    
if __name__ == "__main__":
    # Configuration du port pour Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)