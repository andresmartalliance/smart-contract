# Smart Contract + MAIRA

**Bootstrap V5.1 — Base tecnológica, no MVP terminado.**

Plataforma SaaS multiempresa de contratación mediante workflows configurables. Primer dominio: contratación de red prestadora. No se codifican modalidades como enums fijos. Este paquete contiene un API funcional para validar, simular y crear borradores de workflows, controles tenant-aware en los endpoints, migración inicial y un frontend de referencia con Vue Flow. No contiene aún operación contractual completa ni un agente IA conectado.

## Estructura

- `api/`: FastAPI, ORM SQLAlchemy, migración Alembic, autenticación JWT + membresía de empresa, motor declarativo, pruebas.
- `web/`: Vue 3 + Vue Flow, panel de arquitectura (sin datos reales).
- `docs/`: decisiones y continuidad de versión.
- `.github/workflows/ci.yml`: tests y build por commit.

## Desarrollo local (requiere herramientas de desarrollo)

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/smartcontract
export SMART_AUTH_JWT_SECRET='a-long-dev-secret-replace-in-production'
alembic upgrade head
uvicorn app.main:app --reload
```

```bash
cd web
npm install
npm run dev
```

**Seguridad:** la API no emite tokens de acceso; requiere un JWT firmado de issuer `smart-contract`, audience `smart-contract`, usuario y tenant, más membresía activa en la base. Integración con Google Identity/OIDC pendiente. Nunca activar credenciales de prueba ni bypass de autenticación en Railway. Aún falta implantar RLS nativa de PostgreSQL, backup/restauración y políticas de almacenamiento antes de operar datos reales.

## Endpoints disponibles

- `GET /health` sin datos sensibles.
- `GET /api/v1/workflows` solo para usuarios autenticados con membresía activa.
- `GET /api/v1/workflows/{id}` restringido al tenant.
- `POST /api/v1/workflows/validate` valida definición y DAG.
- `POST /api/v1/workflows/simulate` previsualiza estados conservadores.
- `POST /api/v1/workflows` almacena borrador por tenant y audita.
- `GET /api/v1/maira/capabilities` reporta honestamente que MAIRA aún no está conectada.

## Railway

Proyecto existente: `smart-contract`, ambiente `development`. No conectar servicio hasta que GitHub autorice acceso al nuevo repositorio. En Railway, los servicios `api` y `web` usarán los Dockerfiles en `/api` y `/web`; PostgreSQL debe crearse con secret management y migración inicial. No poner secretos en GitHub ni Drive.

## Criterio de avance

Una release solo se declara completa con: commit SHA, CI verde, migración probada, despliegue healthy, smoke tests, documento maestro Drive sincronizado y manifiesto actualizado. Este bootstrap es **local**, no desplegado.

## Estado de integración V5.1

- GitHub: repositorio privado conectado, base de 38 archivos confirmada en `main`.
- Railway `smart-contract` / `development`: servicios `api` y `web` creados y configurados con `/api` y `/web`, pero **sin despliegue**.
- Bloqueo: la conexión GitHub de Railway no autoriza todavía este repositorio privado (`User does not have access to the repo`). La autorización de ChatGPT/GitHub es independiente de la de Railway.
- Próximo paso: conceder acceso a `andresmartalliance/smart-contract` desde la integración GitHub de Railway; conectar los servicios y verificar build/health sin datos reales.
- La app no tiene sesión Google ni MAIRA operativa. No utilizarla con datos de clientes.
