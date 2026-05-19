import os
import socket
import subprocess
from flask import Flask, render_template_string, request, redirect, url_for, send_from_directory

app = Flask(__name__)

# Configuration des dossiers
# On utilise un chemin absolu pour être sûr que Flask trouve les fichiers
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED = {'pdf', 'doc', 'docx', 'txt', 'odt', 'xls', 'xlsx'}

# On crée le dossier s'il n'existe pas
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Ton code HTML (Inchangé, assure-toi qu'il est bien présent au début du fichier)
HTML = '''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Cloud Prive</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Segoe UI,sans-serif;background:#f0f4f8;color:#4a5568;min-height:100vh}
nav{background:#ffffff;padding:16px 32px;border-bottom:3px solid #a8d8ea;display:flex;justify-content:space-between;align-items:center;box-shadow:0 2px 8px rgba(0,0,0,0.06)}
nav h1{color:#5b8fb9;font-size:20px;font-weight:700;letter-spacing:1px}
.badge{background:#e8f4f8;border:1px solid #a8d8ea;border-radius:20px;padding:6px 16px;font-size:12px;color:#5b8fb9;font-weight:600}
.wrap{max-width:860px;margin:36px auto;padding:0 20px}
.card{background:#ffffff;border:1px solid #e2e8f0;border-radius:14px;padding:28px;margin-bottom:24px;box-shadow:0 2px 12px rgba(0,0,0,0.05)}
.card h2{font-size:12px;text-transform:uppercase;letter-spacing:1px;color:#a8d8ea;margin-bottom:18px;padding-bottom:10px;border-bottom:2px solid #f0f4f8;font-weight:700}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.box{background:#f7fbfd;border:1px solid #e2e8f0;border-radius:10px;padding:16px}
.lbl{font-size:10px;color:#a0aec0;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
.val{font-size:20px;font-weight:700;color:#5b8fb9}
.zone{border:2px dashed #a8d8ea;border-radius:10px;padding:30px;text-align:center;background:#f7fbfd;transition:all 0.2s}
.zone:hover{border-color:#5b8fb9;background:#edf6fb}
input[type=file]{color:#4a5568;font-size:13px;margin:0 auto 18px;display:block}
.btn{background:#a8d8ea;color:#ffffff;border:none;padding:12px 32px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:700;letter-spacing:1px;text-transform:uppercase;transition:background 0.2s}
.btn:hover{background:#5b8fb9}
.note{margin-top:12px;font-size:11px;color:#a0aec0}
.msg{background:#e6f9f0;border-left:4px solid #68d391;padding:12px 16px;border-radius:6px;font-size:13px;color:#2f855a;margin-bottom:18px}
table{width:100%;border-collapse:collapse}
th{background:#f7fbfd;padding:12px 16px;text-align:left;font-size:11px;color:#5b8fb9;text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #e2e8f0}
td{padding:12px 16px;border-bottom:1px solid #f0f4f8;font-size:13px;color:#4a5568}
tr:hover td{background:#f7fbfd}
a.dl{color:#5b8fb9;text-decoration:none;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;padding:6px 12px;background:#e8f4f8;border-radius:6px}
a.dl:hover{background:#a8d8ea;color:#ffffff}
.empty{text-align:center;padding:40px;color:#a0aec0;font-size:13px}
.tag{display:inline-block;background:#fef3cd;color:#d69e2e;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;margin-left:8px}
</style></head>
<body>
<nav>
<h1>Cloud Prive — Stockage Documents</h1>
<span class="badge">{{ serveur }} — {{ ip }}</span>
</nav>
<div class="wrap">

<div class="card">
<h2>Informations du serveur</h2>
<div class="grid">
<div class="box"><div class="lbl">Nom du serveur</div><div class="val">{{ serveur }}</div></div>
<div class="box"><div class="lbl">Adresse IP</div><div class="val">{{ ip }}</div></div>
</div></div>

<div class="card">
<h2>Deposer un document</h2>
{% if message %}<div class="msg">{{ message }}</div>{% endif %}
<div class="zone">
<form method="POST" action="/upload" enctype="multipart/form-data">
<input type="file" name="fichier" accept=".pdf,.doc,.docx,.txt,.odt,.xls,.xlsx">
<button type="submit" class="btn">Envoyer le document</button>
</form>
<p class="note">Formats acceptes : PDF · DOC · DOCX · TXT · ODT · XLS · XLSX · Taille max 16 Mo</p>
</div></div>

<div class="card">
<h2>Documents stockes</h2>
{% if fichiers %}
<table>
<thead><tr><th>Nom du fichier</th><th>Taille</th><th>Action</th></tr></thead>
<tbody>
{% for f in fichiers %}
<tr><td>{{ f.nom }}</td><td>{{ f.taille }}</td><td><a href="/download/{{ f.nom }}" class="dl">Telecharger</a></td></tr>
{% endfor %}
</tbody></table>
{% else %}<div class="empty">Aucun document stocke pour le moment.</div>{% endif %}
</div>

</div></body></html>'''

@app.route('/')
def index():
    fichiers = []
    # On vérifie si le dossier contient des fichiers
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for f in os.listdir(app.config['UPLOAD_FOLDER']):
            chemin_complet = os.path.join(app.config['UPLOAD_FOLDER'], f)
            if os.path.isfile(chemin_complet):
                t = os.path.getsize(chemin_complet)
                # Formatage de la taille
                if t < 1024:
                    s = f"{t} o"
                elif t < 1048576:
                    s = f"{t//1024} Ko"
                else:
                    s = f"{t//1048576} Mo"
                fichiers.append({'nom': f, 'taille': s})

    # Récupération de la vraie IP (10.0.2.16) au lieu de 127.0.1.1
    try:
        vrai_ip = subprocess.check_output(['hostname', '-I']).decode().split()[0]
    except Exception:
        vrai_ip = "10.0.2.16"

    return render_template_string(HTML, fichiers=fichiers,
        serveur=socket.gethostname(),
        ip=vrai_ip,
        message=request.args.get('message',''))

@app.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('fichier')
    if not f or f.filename == '':
        return redirect(url_for('index', message='Aucun fichier selectionne'))

    # Vérification de l'extension du fichier
    extension = f.filename.rsplit('.', 1)[-1].lower()
    if extension in ALLOWED:
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], f.filename))
        return redirect(url_for('index', message=f'{f.filename} uploade avec succes'))

    return redirect(url_for('index', message='Format non autorise'))

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    # Écoute sur toutes les interfaces pour l'accès via Proxmox/Tunnel
    app.run(host='0.0.0.0', port=5000, debug=False)