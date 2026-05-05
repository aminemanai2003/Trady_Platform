# Configuration et Utilisation de l'API Gemini

## Résumé des Modifications

### 1. Clé API Mise à Jour ✅
- **Nouvelle clé** : `AIzaSyAgDSaXCVX3xGUdiAyXFbxqdH-FQ0x0_m0`
- **Fichier** : `backend/.env`
- **Variable** : `GEMINI_API_KEY`

### 2. Migration vers le SDK Officiel ✅
- **Package installé** : `google-genai` (SDK officiel Python)
- **Ancien système** : Requêtes REST directes avec `requests`
- **Nouveau système** : SDK officiel Google GenAI

### 3. Système OCR - Gemini Retiré ✅
- Le système OCR n'utilise **plus** Gemini pour le fallback LLM
- L'OCR repose uniquement sur EasyOCR + extraction heuristique
- **Plus économique** et **plus rapide**

### 4. Système RAG Amélioré ✅
- **Embeddings** : `gemini-embedding-001` (768 dimensions)
- **Génération** : `gemini-1.5-flash` (modèle stable pour tier gratuit)
- **Cache Redis** : 
  - Embeddings : 7 jours
  - Réponses : 1 heure

---

## Configuration de l'API Gemini

### Obtenir une Clé API
1. Visitez : https://aistudio.google.com/app/apikey?hl=fr
2. Créez une clé API gratuite
3. Ajoutez-la dans `backend/.env` :
   ```bash
   GEMINI_API_KEY=votre_clé_ici
   ```

### Installation du SDK
```bash
pip install google-genai
```

### Utilisation de Base

#### 1. Embeddings (pour RAG)
```python
from google import genai
from google.genai import types

client = genai.Client(api_key="VOTRE_CLE")

# Générer un embedding
result = client.models.embed_content(
    model="gemini-embedding-001",
    contents="Texte à embedding",
    config=types.EmbedContentConfig(
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=768
    )
)

embedding_values = result.embeddings[0].values
```

#### 2. Génération de Texte
```python
response = client.models.generate_content(
    model="gemini-1.5-flash",
    contents="Votre prompt ici",
    config=types.GenerateContentConfig(
        max_output_tokens=1024,
        temperature=0.2,
    )
)

answer = response.text
```

---

## Modèles Disponibles (Version Gratuite)

### Embeddings
- **gemini-embedding-001** : 768 dimensions (recommandé)
- **text-embedding-004** : Ancienne version (non utilisée)

### Génération de Texte
- **gemini-1.5-flash** : Rapide, stable, gratuit ✅
- **gemini-2.0-flash** : Peut avoir des limites de quota
- **gemini-pro** : Plus puissant mais limites strictes

---

## Limites de l'API Gratuite

### Quotas (environ)
- **Requêtes par minute** : 15 RPM
- **Requêtes par jour** : 1,500 RPD
- **Tokens par minute** : 1 million TPM

### Gestion du Rate Limiting
Le système implémente :
- **Retry avec backoff exponentiel** (2s, 4s, 8s)
- **Cache Redis** pour éviter les appels redondants
- **Détection 429 automatique**

---

## Tests

### Tester le Système RAG
```bash
cd backend
python test_rag_gemini.py
```

### Test Manuel avec Python
```python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from rag_tutor.services.gemini_service import get_embedding, generate_answer

# Test embedding
embedding = get_embedding("test text")
print(f"Dimensions: {len(embedding)}")

# Test génération
result = generate_answer(
    query="What is forex?",
    context_chunks=["Forex is foreign exchange trading"],
    user_id="test"
)
print(result['answer'])
```

---

## Structure des Fichiers Modifiés

```
backend/
├── .env                          # ✅ Clé API mise à jour
├── rag_tutor/
│   └── services/
│       └── gemini_service.py    # ✅ Migration SDK officiel
├── ocr/
│   ├── pipeline.py              # ✅ Gemini retiré
│   └── llm_module.py            # ❌ Non utilisé (SDK prêt si besoin)
└── test_rag_gemini.py           # ✅ Script de test
```

---

## Dépannage

### Erreur: "GEMINI_API_KEY not set"
- Vérifiez que `.env` contient la clé
- Redémarrez le serveur Django

### Erreur: "429 Rate Limited"
- Attendez quelques secondes
- Le système retry automatiquement
- Cache Redis réduit les appels

### Embeddings fonctionnent mais pas la génération
- Vérifiez le modèle : utilisez `gemini-1.5-flash`
- Quota journalier peut être atteint
- Attendez 24h ou utilisez une nouvelle clé

---

## Documentation Officielle

- **Guide de démarrage** : https://ai.google.dev/gemini-api/docs/quickstart?hl=fr
- **Embeddings** : https://ai.google.dev/gemini-api/docs/embeddings?hl=fr
- **SDK Python** : https://pypi.org/project/google-genai/
- **Tarifs** : https://ai.google.dev/gemini-api/docs/pricing?hl=fr

---

## Statut Actuel

✅ **Opérationnel**
- Clé API configurée
- SDK installé
- Embeddings testés avec succès (768 dimensions)
- Cache Redis fonctionnel
- OCR indépendant de Gemini

⚠️ **Note sur le Rate Limiting**
- La génération de texte peut rencontrer des limites avec l'API gratuite
- Les embeddings sont plus stables
- Le cache réduit considérablement les appels API
