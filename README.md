# Zola Serviços — Backend FastAPI conectado ao Frontend React

Este pacote cria o backend do marketplace local estilo GetNinjas usando **FastAPI** e deixa os arquivos de integração do frontend prontos para substituir o fake API/JSON Server.

## Estrutura

```txt
zola_backend_fastapi/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   └── schemas/
│   ├── requirements.txt
│   └── .env.example
└── frontend-integration/
    ├── .env.example
    └── src/services/
```

## Como rodar o backend

Entre na pasta `backend`:

```bash
cd backend
```

Crie o ambiente virtual:

```bash
python -m venv .venv
```

Ative no Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Ou no CMD:

```cmd
.venv\Scripts\activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Crie o `.env`:

```bash
copy .env.example .env
```

Rode a API:

```bash
uvicorn app.main:app --reload
```

Acesse:

```txt
http://localhost:8000/docs
```

## Usuários de teste

Cliente:

```txt
email: cliente@zola.com
senha: 123456
```

Profissional (diarista):

```txt
email: diarista@zola.com
senha: 123456
```

Profissional (babá):

```txt
email: baba@zola.com
senha: 123456
```

## Endpoints principais

```txt
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
GET  /api/v1/categories
GET  /api/v1/professionals
GET  /api/v1/professionals/{id}
GET  /api/v1/reviews/professional/{professional_id}
POST /api/v1/requests
GET  /api/v1/requests/me
GET  /api/v1/messages/request/{request_id}
POST /api/v1/messages
```

## Como conectar no frontend Vite

No seu projeto React, crie o arquivo `.env` na raiz do `front`:

```txt
VITE_API_URL=http://localhost:8000/api/v1
```

Copie os arquivos de:

```txt
frontend-integration/src/services
```

para:

```txt
front/src/services
```

Depois substitua as chamadas mockadas por chamadas como:

```ts
import { marketplaceService } from '@/services/marketplaceService';

const professionals = await marketplaceService.professionals({
  city: 'Santos',
  min_rating: 4,
});
```

Login:

```ts
import { authService } from '@/services/authService';

await authService.login({
  email: 'cliente@zola.com',
  password: '123456',
});
```

## Observação

O banco padrão é SQLite para facilitar o desenvolvimento. Para produção, troque o `DATABASE_URL` por PostgreSQL:

```txt
DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/zola
```

Nesse caso, instale também o driver PostgreSQL.

## Upload de imagens (produção)

No **Render**, o disco é **temporário**: arquivos em `uploads/` somem no redeploy. Use **Supabase Storage**:

1. Supabase → **Storage** → **New bucket** → `zola-uploads` → marque **Public**
2. **Project Settings → API** → copie **Project URL** e **service_role** key
3. No Render, adicione:

```txt
PUBLIC_API_BASE_URL=https://zola-back.onrender.com
SUPABASE_URL=https://SEU_PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sua-service-role-key
SUPABASE_STORAGE_BUCKET=zola-uploads
```

Sem essas variáveis, o upload até funciona, mas a URL pode apontar para `localhost` ou a imagem some após redeploy.
