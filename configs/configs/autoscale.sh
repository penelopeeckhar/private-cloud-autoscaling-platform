#!/bin/bash
# autoscale.sh — Script d'autoscaling automatique
# Déclenché par webhook.py sur réception d'une alerte HighCPU
# Sélectionne une machine libre, déploie Flask, intègre dans HAProxy

HAPROXY_CFG="/etc/haproxy/haproxy.cfg"
FLASK_APP_DIR="/home/abir/flask-app"
FLASK_PORT=8080
SSH_USER="abir"

# Machines candidates (web3 uniquement dans ce projet)
CANDIDATES=("192.168.220.134")

echo "[AUTOSCALE] Démarrage du script d'autoscaling..."

TARGET=""
TARGET_CPU=100

for HOST in "${CANDIDATES[@]}"; do
    echo "[AUTOSCALE] Vérification de $HOST..."

    # Vérifier si Flask tourne déjà sur cette machine
    FLASK_RUNNING=$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$SSH_USER@$HOST" \
        "ss -tlnp | grep :$FLASK_PORT" 2>/dev/null)

    if [ -n "$FLASK_RUNNING" ]; then
        echo "[AUTOSCALE] Flask déjà actif sur $HOST, machine ignorée."
        continue
    fi

    # Récupérer le CPU idle via Node Exporter (port 9100)
    CPU_IDLE=$(curl -s "http://$HOST:9100/metrics" | \
        grep 'node_cpu_seconds_total{cpu="0",mode="idle"}' | \
        awk '{print $2}')

    # Récupérer la RAM disponible (en octets)
    RAM_FREE=$(curl -s "http://$HOST:9100/metrics" | \
        grep 'node_memory_MemAvailable_bytes ' | \
        awk '{print $2}')

    RAM_FREE_MB=$(echo "$RAM_FREE / 1024 / 1024" | bc 2>/dev/null || echo "0")

    echo "[AUTOSCALE] $HOST — CPU idle: $CPU_IDLE, RAM libre: ${RAM_FREE_MB}Mo"

    # Sélectionner si RAM > 300Mo (CPU idle = critère secondaire ici)
    if [ "$RAM_FREE_MB" -gt 300 ] 2>/dev/null; then
        TARGET="$HOST"
        echo "[AUTOSCALE] Machine sélectionnée : $TARGET"
        break
    fi
done

if [ -z "$TARGET" ]; then
    echo "[AUTOSCALE] Aucune machine disponible. Abandon."
    exit 1
fi

# ── Étape 1 : Test SSH ─────────────────────────────────────────────
echo "[AUTOSCALE] Test de la connexion SSH vers $TARGET..."
ssh -o BatchMode=yes -o ConnectTimeout=5 "$SSH_USER@$TARGET" "echo SSH OK" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[AUTOSCALE] Connexion SSH échouée vers $TARGET. Abandon."
    exit 1
fi

# ── Étape 2 : Copie des fichiers Flask ────────────────────────────
echo "[AUTOSCALE] Copie de l'application Flask vers $TARGET..."
ssh "$SSH_USER@$TARGET" "mkdir -p $FLASK_APP_DIR"
scp -r "$FLASK_APP_DIR/"* "$SSH_USER@$TARGET:$FLASK_APP_DIR/"
if [ $? -ne 0 ]; then
    echo "[AUTOSCALE] Copie SCP échouée. Abandon."
    exit 1
fi

# ── Étape 3 : Lancement de Flask ──────────────────────────────────
echo "[AUTOSCALE] Lancement de Flask sur $TARGET:$FLASK_PORT..."
ssh "$SSH_USER@$TARGET" \
    "cd $FLASK_APP_DIR && nohup python3 app.py > flask.log 2>&1 &"

# ── Étape 4 : Vérification (attente 15 secondes) ──────────────────
echo "[AUTOSCALE] Attente de 15 secondes pour vérifier le démarrage..."
sleep 15

HTTP_RESP=$(curl -s -o /dev/null -w "%{http_code}" "http://$TARGET:$FLASK_PORT" 2>/dev/null)
if [ "$HTTP_RESP" != "200" ]; then
    echo "[AUTOSCALE] Flask ne répond pas (HTTP $HTTP_RESP). Abandon."
    exit 1
fi
echo "[AUTOSCALE] Flask répond correctement sur $TARGET:$FLASK_PORT (HTTP 200)."

# ── Étape 5 : Intégration dans HAProxy ────────────────────────────
# Extraire le nom court (ex: web3 depuis 192.168.220.134)
HOST_NAME="web3"

echo "[AUTOSCALE] Ajout de $HOST_NAME dans HAProxy..."
# Insérer la ligne server avant le commentaire de fin de backend
sed -i "/# web3 ajouté automatiquement/a\\    server $HOST_NAME $TARGET:$FLASK_PORT check" \
    "$HAPROXY_CFG"

# Recharger HAProxy sans interruption
systemctl reload haproxy
if [ $? -eq 0 ]; then
    echo "[AUTOSCALE] HAProxy rechargé avec succès. $HOST_NAME intégré."
else
    echo "[AUTOSCALE] Erreur lors du rechargement HAProxy."
    exit 1
fi

echo "[AUTOSCALE] Autoscaling terminé avec succès. $TARGET est maintenant actif."
exit 0
