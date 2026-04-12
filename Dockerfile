# Image de base Python
FROM python:3.11-slim

# Empêcher Python de générer des fichiers .pyc et activer le mode non-interactif
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV ENV production
ENV RRROCKET_PATH /app/parsers/rrrocket

# Installation des dépendances système nécessaires (curl pour télécharger le parser)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Création du répertoire de travail
WORKDIR /app

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Création des répertoires pour les données et le parser
RUN mkdir -p data uploaded_replays parsers/boxcars

# Téléchargement du binaire rrrocket pour Linux
RUN curl -L https://github.com/nick12/rrrocket/releases/download/v0.1.0/rrrocket-linux-x86_64 -o /app/parsers/boxcars/rrrocket \
    && chmod +x /app/parsers/boxcars/rrrocket

# Copie du reste de l'application
COPY . .

# Définition du chemin du parser pour le mode production
ENV RRROCKET_PATH /app/parsers/boxcars/rrrocket

# Exposition du port
EXPOSE 8000

# Commande de démarrage
CMD ["python", "main.py"]
