#!/usr/bin/env python3
"""
app.py — Application Flask "Bite and Delight"
Site de restauration déployé sur web1, web2 (et web3 via autoscaling).
Affiche l'IP du serveur qui répond à chaque requête.
"""

import socket
from flask import Flask, render_template_string, request
import time

app = Flask(__name__)

SERVER_IP = socket.gethostbyname(socket.gethostname())

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Bite and Delight</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
        .banner {
            background: #e74c3c;
            color: white;
            padding: 10px 20px;
            font-size: 14px;
        }
        .container { padding: 40px; }
        h1 { color: #2c3e50; }
    </style>
</head>
<body>
    <div class="banner">
        🖥️ Servi par le serveur de IP : {{ server_ip }}
    </div>
    <div class="container">
        <h1>🍽️ Bite and Delight</h1>
        <p>Bienvenue sur notre application de restauration.</p>
        <p>Ce serveur héberge l'application Flask déployée automatiquement
           dans le cadre du projet Cloud Privé — ENSA Fès GDNC4.</p>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, server_ip=SERVER_IP)

@app.route('/health')
def health():
    return {"status": "ok", "server": SERVER_IP}, 200

@app.route('/slow')
def slow():
    """Endpoint de simulation de lenteur (utilisé pour tester Least Connections)."""
    time.sleep(10)
    return {"status": "slow response", "server": SERVER_IP}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
