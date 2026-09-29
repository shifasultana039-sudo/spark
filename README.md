# ⚡ ReliefChain AI (SPARK)

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://spark-lbi8.onrender.com)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new?hide_repo_select=true&ref=main&repo=shifasultana039-sudo%2Fspark)
[![Smart Contract](https://img.shields.io/badge/MST%20Contract-0x84AB...9d14-blueviolet?style=for-the-badge)](https://mstscan.com/address/0x84AB4dC72536D55aDa9617b673dd33AC9d709d14)
[![API Docs](https://img.shields.io/badge/API%20Docs-Swagger-85EA2D?style=for-the-badge&logo=swagger&logoColor=black)](https://spark-lbi8.onrender.com/docs)
[![System Health](https://img.shields.io/badge/System-Healthy-success?style=for-the-badge)](https://spark-lbi8.onrender.com/health)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

> **Human-Supervised AI Platform for Disaster-Relief Allocation & Civic Resilience**  
> *AI decides faster. Humans stay in control. Every critical decision is verifiable.*

---

## 🌐 Live URLs

- **Production Web Application:** [https://spark-lbi8.onrender.com](https://spark-lbi8.onrender.com)
- **Deployed Smart Contract:** [https://mstscan.com/address/0x84AB4dC72536D55aDa9617b673dd33AC9d709d14](https://mstscan.com/address/0x84AB4dC72536D55aDa9617b673dd33AC9d709d14)
- **Interactive API Documentation:** [https://spark-lbi8.onrender.com/docs](https://spark-lbi8.onrender.com/docs)
- **API Health Diagnostic:** [https://spark-lbi8.onrender.com/health](https://spark-lbi8.onrender.com/health)

---

## 🌟 Key Capabilities

1. **Digital Asset Pre-Registration & Cryptographic Integrity**
   - Citizens register fixed and movable assets with geotagged imagery and provenance documents.
   - SHA-256 cryptographic hashing prevents retroactive post-disaster fraud.

2. **Computer Vision Damage Assessment**
   - Automated damage scoring (Minor, Moderate, Severe, Total) with visual confidence metrics and explainability factors.

3. **Field Inspector Ground Verification**
   - Field assessors upload GPS-verified post-incident imagery and confirm or adjust AI damage assessments.

4. **Explainable AI Loss Compensation**
   - Transparent calculation breakdowns considering pre-disaster valuation, verified damage level, deductible policies, and vulnerability factors.

5. **Tamper-Evident Audit Trail & Blockchain Anchoring**
   - Full immutability via cryptographic audit trails, with MST Testnet blockchain transaction anchoring.

---

## 🛠️ Technology Stack

- **Backend:** Python 3.11, FastAPI, Uvicorn, SQLite / PostgreSQL, Pydantic v2
- **Frontend:** React 18, TypeScript, Vite, Lucide Icons, Tailwind-inspired Vanilla Design Tokens
- **Blockchain Integration:** MST Testnet (EVM-compatible cryptographic anchoring)
- **Cloud Deployment:** Render, Docker, Procfile

---

## 🚀 Local Development

### 1. Backend Setup
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 3. Open in Browser
- Local Web App: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Vite Dev Server: [http://localhost:5173](http://localhost:5173)
- API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
