# Smart Contract + MAIRA

**V5.5 — Identidad MAIRA y significado internacional + Workflow Studio · ambiente Development**

Smart Contract es una plataforma SaaS multiempresa con motor declarativo de workflows de contratación, campos, políticas y modalidades configurables. La primera aplicación es contratación de red prestadora de salud, sin codificar PGP, cápita ni evento como flujos obligatorios. El workflow institucional de Famisanar aún no ha sido recibido y no forma parte de esta versión.

## Identidad MAIRA V5.5

Nombre de marca: **MAIRA — Multi-tenant AI for Intelligent Review & Agreements**.
Sentido operativo: inteligencia artificial multiempresa para revisión inteligente y acuerdos contractuales. Descriptor: **Contract Intelligence Agent** (agente de inteligencia contractual).

La pantalla MAIRA muestra una tarjeta de identidad azul profundo con círculos cian, la sigla visible, su significado en inglés y su traducción contextual al español, conforme a la referencia visual de NORA. El panel persistente de MAIRA y la tarjeta del Resumen también muestran el significado. No se cambia la arquitectura multiempresa ni se afirma que Gemini esté conectado.

## Qué cambia en V5.4

- Un botón MAIRA flotante visible en todas las pantallas, persistente al navegar; abre y cierra un panel lateral contextual sin bloquear el diseñador.
- El panel reconoce el módulo actual; en Flujos también reconoce el nombre y estado del borrador y la etapa seleccionada.
- Atajos reales y locales: verificar estructura, simular, agregar una aprobación y exportar JSON, además de navegación a Workflow Studio y vista MAIRA.
- El panel distingue claramente asistencia contextual local de inteligencia generativa: **Gemini aún NO está conectado**. No muestra respuestas falsas ni envía información del cliente.
- Diseño responsive, control accesible de apertura/cierre y advertencias claras sobre la ausencia de datos institucionales autenticados.
- Configuración Railway por watch paths: API /api/** y Web /web/**, para reducir compilaciones por commits exclusivamente documentales. No cambia la infraestructura.
- Las experiencias Configurador y Operador institucionales, RLS, publicación y MAIRA con Gemini siguen pendientes.

## Qué cambia en V5.3

- Sistema visual renovado, claro y futurista, sin efectos decorativos excesivos: tipografía, navegación vectorial, superficies, gradientes limitados, tarjetas y componentes unificados.
- Resumen convertido en centro de control: métricas estrictamente derivadas del borrador del navegador, acceso a Workflow Studio y estado real de MAIRA. No inventa contratos, proveedores, porcentajes ni tendencias.
- Workflow Studio con nueva jerarquía visual, biblioteca de categorías, canvas limpio, nodos identificados visualmente por su función, propiedades y conexiones más legibles.
- MAIRA tiene una pantalla de presentación propia, con cuatro capacidades planificadas, pero conserva la indicación clara de que Gemini aún NO está conectado.
- Pantallas aún no operativas mantienen estados vacíos honestos, sin datos de demostración presentados como reales.
- Diseño adaptable a pantallas medianas y móviles; foco visible y soporte de movimiento reducido.
- La navegación inicia en Resumen y abre el mismo Workflow Studio funcional de V5.2, preservando su persistencia local y JSON.
- No hay nuevas dependencias, cuentas ni servicios. No se alteraron esquemas de base de datos, API ni permisos.

## Qué funciona en V5.4

**Diseñador visual Vue 3 / Vue Flow:**

- Crear un flujo en blanco o partir de un ejemplo genérico de red prestadora.
- Insertar 14 bloques funcionales, arrastrar etapas, añadir conexiones y quitar conexiones o etapas no protegidas.
- Configurar nombres, roles abiertos, requisitos legales/institucionales/condicionales/opcionales, activación y reglas de igualdad, desigualdad, comparación, pertenencia o existencia.
- Configurar por etapa campos de formulario reutilizables (nombre, identificador, tipo y obligatoriedad), instrucciones y modo de ejecución (manual, IA asistida, API o RPA — los últimos requieren integraciones futuras).
- Validación estructural del grafo: entrada/salida, ciclos, rutas sin finalización, tareas protegidas, responsables y claves de campos.
- Simulación local con hechos JSON y lista de actividades completadas. Simulación conservadora: un dato desconocido bloquea la rama; no representa una aprobación real ni cumplimiento jurídico.
- Exportación e importación JSON compatible con el esquema FastAPI, preservando posiciones y condiciones de ruta.
- Recuperación automática del borrador en **este navegador**, usando localStorage. Es almacenamiento local, no compartido ni multiempresa. No ingresar expedientes ni datos reales de clientes.

**API FastAPI:** rutas con JWT y pertenencia al tenant, CRUD básico de borradores, validación del motor y simulación estructural. Los controles de servidor se extienden para rechazar enlaces hacia inicio/después de finalización, ramas huérfanas, aprobadores ausentes, campos duplicados y condiciones obligatorias sin regla. **La interfaz aún NO está conectada a estas rutas porque la autenticación corporativa falta.**

**Railway:** se usa el mismo proyecto `smart-contract`, ambiente `development`, con servicios `api`, `web` y `Postgres` conectados a GitHub `andresmartalliance/smart-contract` / `main`. La migración inicial Alembic se ejecuta como predeploy de API. No instalar otro ambiente de prueba.

## Qué no está operativo

- Google Sign-In y sesiones corporativas con roles Configurador/Operador.
- Persistencia institucional compartida, versionado de publicación, ejecución real de contratos y aprobaciones.
- PostgreSQL RLS, almacenamiento documental protegido por institución y auditoría productiva.
- MAIRA + Gemini; sigue en estado NO CONFIGURADO. No se simulan respuestas de IA.
- Integraciones REPS, SIIFA, ERP, firma, API y RPA.

**Restricción:** el acceso público a Development es solo para diseño con datos ficticios o plantillas genéricas. No cargar información real de IPS, documentos, contratos ni tarifas institucionales hasta implementar controles de identidad y privacidad.

## Arquitectura de código

- `api/` — FastAPI, modelos de tenants, JWT/membresía, versiones de workflows, reglas DSL, simulador, Alembic y pruebas pytest.
- `web/` — Vue 3 + Vue Flow. Visual Editor, panel de propiedades, condiciones, formularios, validación y simulación local.
- `docs/ARCHITECTURE.md` — arquitectura integral y límites de este paquete.
- `RELEASE_MANIFEST.json` — estado de verificación; la fuente de continuidad de negocio es el documento maestro de Google Drive.

## Verificación del paquete

- Backend: desde `api/`, `python -m pytest -q` — **14 pruebas** de backend superadas previamente; la capa visual conserva el mismo motor. El frontend V5.3 compila en Railway.
- Frontend: desde `web/`, `npm install && npm run build` — debe verificarse en Railway; el entorno local no pudo instalar las dependencias de npm por conectividad.
- Despliegue: GitHub hace despliegue automático de ambos servicios. Un solo commit consolidado por entrega para contener costos.
- Una release solo se cierra tras verificar despliegues, resultado de build, APIs, riesgos, actualización integral de Drive y SHA final.

## Continuidad

Repositorio privado: `andresmartalliance/smart-contract`. Proyecto Railway: `smart-contract` / `development`. Google Drive: carpeta `Smart Contract - Desarrollo y Continuidad`, documento `00 - SMART CONTRACT - CONTEXTO MAESTRO INTEGRAL - V5.4` (se actualiza al verificar el release).

El usuario autorizó trabajar únicamente en este repositorio, proyecto Railway y carpeta Drive; esa limitación es una **política de ejecución** porque los conectores tienen alcance técnico más amplio. No modificar otros productos.

Próxima versión integral: autenticación real y control multiempresa de configuración, guardado seguro de flujos, publicación con permisos, MAIRA conectada y procesamiento del workflow real cuando se reciba.
