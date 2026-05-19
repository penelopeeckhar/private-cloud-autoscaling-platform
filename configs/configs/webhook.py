#!/usr/bin/env python3
"""
webhook.py — Récepteur d'alertes Alertmanager
Écoute sur le port 5001, déclenche autoscale.sh à la réception d'une alerte.
"""

import subprocess
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

# Verrou pour éviter les exécutions parallèles
lock = threading.Lock()


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print(f"[WEBHOOK] Alerte reçue : {data}")

    alerts = data.get('alerts', [])
    for alert in alerts:
        if alert.get('status') == 'firing':
            instance = alert.get('labels', {}).get('instance', 'inconnu')
            print(f"[WEBHOOK] Alerte FIRING sur instance : {instance}")

            # Déclenchement du script d'autoscaling dans un thread séparé
            if lock.acquire(blocking=False):
                thread = threading.Thread(target=run_autoscale, args=(instance,))
                thread.start()
            else:
                print("[WEBHOOK] Autoscaling déjà en cours, alerte ignorée.")

    return jsonify({"status": "received"}), 200


def run_autoscale(instance):
    try:
        print(f"[AUTOSCALE] Démarrage du script pour instance : {instance}")
        result = subprocess.run(
            ['bash', '/home/abir/autoscale.sh'],
            capture_output=True,
            text=True
        )
        print(f"[AUTOSCALE] stdout : {result.stdout}")
        print(f"[AUTOSCALE] stderr : {result.stderr}")
    finally:
        lock.release()
        print("[AUTOSCALE] Script terminé, verrou libéré.")


if __name__ == '__main__':
    # Écoute sur toutes les interfaces, port 5001
    app.run(host='0.0.0.0', port=5001)
