# 🏗️ Mini Cloud Privé — Infrastructure Automatisée

> Projet académique — ENSA Fès · Filière GDNC4 · 2025/2026  
> **Auteure :** Abir MAJDI · **Encadrant :** Pr. Youssef AOUNZO

---

## 🎯 Objectifs

Ce projet conçoit, configure et administre une infrastructure de **Cloud Privé** fonctionnelle, capable de :

- Répartir la charge entre plusieurs serveurs web (Load Balancing)
- Surveiller l'état des machines en temps réel (Monitoring)
- Se déclencher automatiquement en cas de surcharge (Autoscaling)
- Assurer la continuité du service en cas de panne (Haute Disponibilité)

---

## 🏛️ Architecture Globale

### Approche 1 — Proxmox VE (cluster distribué)

```
Internet / Utilisateur
        │
        ▼
┌───────────────────┐
│  HAProxy (VM 100) │  192.168.126.131:80
│  Load Balancer    │
└────────┬──────────┘
         │  Round Robin
    ┌────┴─────┐
    ▼          ▼
┌────────┐  ┌────────┐
│ Flask1 │  │ Flask2 │
│ VM 101 │  │ VM 102 │
│node5   │  │node2   │
└────────┘  └────────┘
    │            │
    └────┬───────┘
         │
    ZeroTier VPN Overlay
    (pve-node5 ↔ pve-node2)
```

### Approche 2 — VMware local (autoscaling complet)

```
Internet / Utilisateur
        │
        ▼
┌──────────────────────────────────────┐
│        Serveur Principal             │
│        192.168.220.131               │
│  ┌──────────┐  ┌────────────────┐    │
│  │ HAProxy  │  │   Prometheus   │    │
│  │  :80     │  │ Alertmanager   │    │
│  │          │  │  webhook :5001 │    │
│  └────┬─────┘  └───────┬────────┘    │
└───────┼────────────────┼────────────┘
        │ Least Conn.    │ Alert POST
   ┌────┴────┐      ┌────▼────┐
   ▼         ▼      ▼         
┌──────┐  ┌──────┐  autoscale.sh
│ web1 │  │ web2 │       │
│.132  │  │.133  │       ▼
└──────┘  └──────┘  ┌──────┐
  Flask      Flask  │ web3 │ ← activé si CPU > 80%
  :8080      :8080  │.134  │
                    └──────┘
```

---

## 🛠️ Technologies utilisées

| Composant | Rôle | Version |
|---|---|---|
| **Proxmox VE** | Hyperviseur Type 1 (bare-metal) | 8.x |
| **VMware Workstation** | Hyperviseur Type 2 (local) | — |
| **ZeroTier** | VPN overlay inter-nœuds | — |
| **HAProxy** | Load Balancer (Round Robin / Least Connections) | 2.x |
| **Flask (Python)** | Application web serveur | 3.x |
| **Prometheus** | Monitoring & scraping de métriques | 2.x |
| **Node Exporter** | Agent de métriques système (CPU, RAM) | — |
| **Alertmanager** | Routage des alertes Prometheus | — |
| **Ubuntu Server** | OS des machines virtuelles | 22.04 LTS |

---

## ⚖️ Load Balancing

HAProxy est configuré en **frontend/backend** sur le port 80.  
Deux algorithmes ont été testés :

- **Round Robin** (Approche Proxmox) : les requêtes sont distribuées à tour de rôle entre les serveurs. Chaque rechargement de page bascule entre Flask-1 et Flask-2.
- **Least Connections** (Approche VMware) : les nouvelles requêtes sont envoyées au serveur le moins chargé. Testé avec un endpoint `/slow` simulant une lenteur sur web1 — HAProxy privilégie automatiquement web2.

**Tolérance aux pannes :** HAProxy détecte les serveurs indisponibles via des health checks réguliers et les exclut du pool en moins de 10 secondes, sans interruption de service pour l'utilisateur.

---

## 📡 Monitoring (Prometheus Stack)

```
Node Exporter (web1/2/3 :9100)
        │  scrape toutes les 15s
        ▼
   Prometheus (:9090)
        │  évalue les règles d'alerte
        ▼
  Alertmanager (:9093)
        │  POST HTTP si CPU > 80% pendant > 30s
        ▼
   webhook.py (:5001)
```

**Règle d'alerte déclenchée :**  
`HighCPU` — CPU > 80% pendant plus d'une minute → alerte CRITICAL envoyée à Alertmanager.

---

## 🚀 Autoscaling Automatique

**Pipeline complet :**

```
Prometheus → Alertmanager → webhook.py → autoscale.sh → HAProxy
```

**Étapes du script `autoscale.sh` :**

1. Interroge Node Exporter sur chaque machine candidate
2. Écarte les machines où Flask tourne déjà (port 8080 actif)
3. Sélectionne la machine avec le **CPU le plus bas** (< 70%) et au moins 300 Mo RAM libre
4. Teste la connexion SSH sans mot de passe vers la machine cible
5. Copie l'application Flask via SCP
6. Lance Flask en arrière-plan via SSH sur le port 8080
7. Attend 15 secondes puis vérifie que Flask répond
8. Ajoute automatiquement la nouvelle machine dans la configuration HAProxy
9. Recharge HAProxy **sans interruption de service**

**Test de validation :**  
Simulation avec `stress --cpu 4 --timeout 180` → CPU atteint 99.99% → alerte FIRING → web3 (`192.168.220.134`) déployé et intégré automatiquement en moins de 2 minutes.

---

## 🎬 Démo vidéo
APPROCHE 1

> ProxmoxVE: https://drive.google.com/file/d/1Vi0OEsayQS8DS7vnjeizROXIVdaSn-Mc/view?usp=sharing

APPROCHE 2

> Load balancing : https://drive.google.com/file/d/1cwA6o3R1lUo9ZQbpWp5CWIV6gdQPv3g7/view?usp=sharing

> Autoscaling : https://drive.google.com/file/d/13UcL5R4D_Iq8zVgE4anhp8zL5M3OlRga/view?usp=sharing

---

## 📁 Structure du dépôt

```
private-cloud-autoscaling-platform/
│
├── README.md
├── Rapport_Final_cloud_prive_GDNC.pdf
│
├── configs/
│   ├── haproxy.cfg
│   ├── prometheus.yml
│   ├── alertmanager.yml
│   ├── autoscale.sh
│   └── webhook.py
│
├── architecture/
│
└── demo/
```

---

## ▶️ Lancement rapide

```bash
# 1. Démarrer le webhook sur le serveur principal
python3 configs/webhook.py

# 2. Simuler une surcharge CPU (pour tester l'autoscaling)
stress --cpu 4 --timeout 180

# 3. Vérifier les alertes Prometheus
# http://192.168.220.131:9090/alerts

# 4. Vérifier l'intégration dans HAProxy
cat /etc/haproxy/haproxy.cfg
```

---

## 👩‍💻 Auteure

**Abir MAJDI** — Étudiante GDNC4, ENSA Fès  
GitHub : [@penelopeeckhar](https://github.com/penelopeeckhar)  
Portfolio : [penelopeeckhar.github.io/portfolio](https://penelopeeckhar.github.io/portfolio)   
Linkedin : [Abir Majdi] (www.linkedin.com/in/abir-majdi-a221bb296)
