# Image de base Python
FROM python:3.11-slim

# Config environnement
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV ENV production

# Installation des dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Création du répertoire de travail
WORKDIR /app

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Création des répertoires pour les données et le parser
RUN mkdir -p data uploaded_replays parsers/boxcars

# Téléchargement et extraction du binaire rrrocket pour Linux
RUN curl -L https://github.com/nickbabcock/rrrocket/releases/download/v0.10.12/rrrocket-0.10.12-x86_64-unknown-linux-musl.tar.gz -o rrrocket.tar.gz \
    && tar -xzf rrrocket.tar.gz -C /app/parsers/boxcars/ --strip-components=1 \
    && rm rrrocket.tar.gz \
    && chmod +x /app/parsers/boxcars/rrrocket

# Copie du reste de l'application
COPY . .

# Définition du chemin du parser pour le mode production
ENV RRROCKET_PATH /app/parsers/boxcars/rrrocket

# Exposition du port
EXPOSE 8000

# Commande de démarrage
CMD ["python", "main.py"]
