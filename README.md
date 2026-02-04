# WebMarket+ - Architecture AWS pour PME

## 📚 Panorama du Cloud & Déploiement AWS - EFRE 2025-2026

Ce projet déploie une architecture cloud complète sur AWS pour une PME (WebMarket+), incluant une infrastructure scalable, sécurisée et optimisée en coûts.

### 🏗️ Architecture

L'infrastructure déployée suit une architecture **3-tier** avec haute disponibilité :

- **Tier Public** : Application Load Balancer (ALB) dans des sous-réseaux publics
- **Tier Application** : Auto Scaling Group avec instances EC2 (t3.micro) dans des sous-réseaux privés
- **Tier Base de données** : RDS MySQL Multi-AZ dans des sous-réseaux privés isolés
- **Stockage** : S3 bucket pour les assets (datalake) avec versioning activé

### Composants principaux

- **VPC** : Réseau isolé avec 6 sous-réseaux répartis sur 2 AZ
- **ALB** : Répartition de charge HTTP avec health checks
- **Auto Scaling** : Scaling automatique basé sur l'utilisation CPU (cible: 70%)
- **RDS** : MySQL 8.0 en Multi-AZ pour haute disponibilité
- **S3** : Bucket privé avec versioning pour le catalogue d'assets
- **CloudWatch** : Dashboard de monitoring (CPU, instances, trafic HTTP)
- **Sécurité** : Security Groups avec isolation par tier, pas d'accès SSH public

## 📋 Prérequis

- Terraform >= 1.0
- Python 3.8+
- AWS CLI configuré avec credentials valides
- Accès AWS avec permissions suffisantes

## 🚀 Déploiement

### 1. Installation des dépendances Python

```bash
pip install -r requirements.txt
```

### 2. Configuration Terraform

Les variables par défaut sont définies dans `terraform/variables.tf`. Pour personnaliser :

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

**Variables principales :**

- `aws_region` : Région AWS (défaut: `eu-west-3` - Paris)
- `project_name` : Nom du projet (défaut: `webmarket-plus`)
- `environment` : Environnement (défaut: `dev`)
- `db_password` : Mot de passe RDS

### 3. Population du Data Lake

Après le déploiement, uploader les assets vers S3 :

```bash
python scripts/populate_datalake.py
```

Les fichiers du dossier `assets/` seront uploadés dans le bucket S3 sous `catalogue/`.

## 🧪 Scripts utilitaires

### Load Generator (`scripts/load_generator.py`)

Génère du trafic HTTP continu vers l'ALB pour tester la scalabilité :

```bash
python scripts/load_generator.py
```

- Récupère automatiquement l'URL de l'ALB via les outputs Terraform
- Lance 100 threads simulés (clients virtuels)
- Arrêt avec `CTRL+C`

### Audit Infrastructure (`scripts/audit_infra.py`)

Audit FinOps et sécurité de l'infrastructure déployée :

```bash
python scripts/audit_infra.py
```

**Vérifications effectuées :**

- Coûts estimés (EC2, ALB, NAT Gateway)
- Estimation mensuelle
- Détection de vulnérabilités (SSH public ouvert)

### Backup Manager (`scripts/backup_manager.py`)

Création de snapshots RDS manuels avec horodatage :

```bash
python scripts/backup_manager.py
```

- Crée un snapshot avec un ID unique incluant un timestamp
- Récupère automatiquement l'instance RDS via les outputs Terraform
- Format du snapshot : `snap-{instance-id}-{YYYY-MM-DD-HH-MM}`

### Cleanup (`scripts/cleanup.py`)

Nettoyage automatique des anciens snapshots RDS :

```bash
python scripts/cleanup.py
```

- Supprime les snapshots manuels de plus de 7 jours (configurable)
- Affiche la liste des snapshots avec leur âge
- Permet de réduire les coûts de stockage

### Daily Scheduler (`scripts/daily_scheduler.py`)

Gestion automatique des instances EC2 en environnement dev :

```bash
# Arrêter les instances dev
python scripts/daily_scheduler.py stop

# Démarrer les instances dev
python scripts/daily_scheduler.py start
```

- Cible uniquement les instances avec le tag `Environment=dev`
- Permet d'économiser les coûts en arrêtant les instances hors heures de travail
- À planifier avec un cron job ou EventBridge

## 📊 Outputs Terraform

Après le déploiement, récupérer les informations importantes :

```bash
cd terraform
terraform output
```

**Outputs disponibles :**

- `alb_dns_name` : URL publique de l'application
- `s3_bucket_name` : Nom du bucket S3
- `rds_endpoint` : Endpoint de la base de données
- `rds_instance_id` : Identifiant de l'instance RDS

## 📊 Monitoring

Un dashboard CloudWatch est automatiquement créé pour surveiller l'infrastructure :

- **CPU Moyen** : Utilisation CPU moyenne de l'Auto Scaling Group
- **Instances Actives** : Nombre d'instances en service dans l'ASG
- **Trafic HTTP** : Nombre de requêtes reçues par l'ALB

Accéder au dashboard depuis la console AWS CloudWatch ou via :

```bash
aws cloudwatch get-dashboard --dashboard-name webmarket-plus-dashboard-dev
```

## 🔒 Sécurité

- **Security Groups** : Isolation stricte entre les tiers (ALB → App → DB)
- **S3** : Accès public bloqué par défaut
- **RDS** : Accessible uniquement depuis le tier application
- **IAM** : Rôles avec permissions minimales (S3 + SSM)
- **Pas de SSH public** : Accès via AWS Systems Manager Session Manager

## 💰 Estimation des coûts

L'architecture est optimisée pour un environnement de démonstration :

- **EC2** : t3.micro (2-4 instances selon charge) ~ $0.0118/h
- **ALB** : ~ $0.0243/h
- **NAT Gateway** : ~ $0.048/h
- **RDS** : db.t3.micro Multi-AZ ~ $0.034/h

**Estimation mensuelle** : ~ $85-100/mois (selon utilisation)

⚠️ **Important** : Pensez à détruire l'infrastructure après utilisation avec `terraform destroy` pour éviter les coûts inutiles.

## 📁 Structure du projet

```text
.
├── terraform/          # Configuration Infrastructure as Code
│   ├── main.tf         # ALB, Auto Scaling, Launch Template
│   ├── vpc.tf          # VPC, Subnets, NAT Gateway
│   ├── database.tf     # RDS MySQL
│   ├── storage.tf      # S3 Bucket
│   ├── security.tf     # Security Groups
│   ├── iam.tf          # IAM Roles & Policies
│   ├── monitoring.tf   # CloudWatch Dashboard
│   ├── variables.tf    # Variables Terraform
│   └── outputs.tf      # Outputs Terraform
├── scripts/            # Scripts Python utilitaires
│   ├── load_generator.py      # Génération de trafic
│   ├── audit_infra.py         # Audit FinOps & Sécurité
│   ├── populate_datalake.py   # Upload S3
│   ├── backup_manager.py      # Création snapshots RDS
│   ├── cleanup.py             # Nettoyage snapshots anciens
│   └── daily_scheduler.py     # Gestion instances dev
└── assets/             # Assets à uploader dans S3
```

## 🧹 Nettoyage

Pour détruire toute l'infrastructure et éviter les coûts :

```bash
cd terraform
terraform destroy
```

## 📝 Notes

- L'architecture utilise **Multi-AZ** pour RDS (haute disponibilité)
- Le **Auto Scaling** est configuré pour maintenir 2-4 instances selon la charge
- Les **snapshots RDS** peuvent être créés manuellement via `backup_manager.py`
- Le script `cleanup.py` permet de gérer la rétention des snapshots (7 jours par défaut)
- Le **Daily Scheduler** permet d'économiser sur les environnements dev en arrêtant les instances la nuit
- Le **dashboard CloudWatch** est créé automatiquement pour le monitoring
- Le mot de passe RDS par défaut doit être changé en production
