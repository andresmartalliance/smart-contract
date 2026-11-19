# Smart Contract + MAIRA

**V6.4 — Personas y empresas independientes de plantillas · Development**

Smart Contract es una plataforma SaaS multiempresa con motor declarativo de workflows de contratación, campos, políticas y modalidades configurables. La primera aplicación es contratación de red prestadora de salud, sin codificar PGP, cápita ni evento como flujos obligatorios. El workflow institucional de Famisanar aún no ha sido recibido y no forma parte de esta versión.

## V6.4 — Directorio de personas y empresas, independiente de los contratos

**La entidad, el usuario y el expediente no son el mismo registro.** La necesidad del usuario es registrar primero a un prestador, persona natural o jurídica, y después asociarle un proceso existente o una plantilla nueva. Ahora la plataforma lo permite sin obligar a construir un workflow para crear la entidad.

### Recorrido correcto para el piloto (solo datos ficticios)
1. Ingresar con el administrador Google habilitado y abrir **Personas y empresas**.
2. Registrar razón social/nombre, tipo de persona y correo de contacto (opcional hasta iniciar el proceso). El registro vive en PostgreSQL y se reutiliza en tantas contrataciones como sean necesarias.
3. Desde el directorio pulsar **Crear expediente** para ese registro. En **Gestión Contractual**, indicar título y opcionalmente seleccionar una plantilla existente.
4. Si no hay plantilla, **Crear expediente sin plantilla**. Se guarda con estado `DRAFT`, sin crear tareas ni dar acceso al expediente. Se podrá diseñar una plantilla después en **Flujos** (manual o mediante MAIRA cuando Gemini esté configurado).
5. Desde el detalle del borrador, seleccionar una plantilla publicada y **Asociar plantilla e iniciar proceso**. Esto genera tareas, activa las dependencias y vincula el correo de contacto para acceso al expediente.
6. El usuario externo puede entrar antes de tener procesos si su correo Google está registrado como contacto (y está autorizado como Test user en Google Auth Platform Testing). Su panel **Mi Contratación** estará vacío hasta que se active un expediente para él.
7. Probar diligenciamiento externo, devolución, corrección y revisión interna desde sesiones separadas.

Se agregó `GET/POST /api/v1/portal/parties`, `PATCH /api/v1/portal/parties/{id}` y `POST /api/v1/portal/cases/{id}/workflow`. `POST /cases` acepta `party_id` de un registro existente y `workflow_id` opcional; la forma anterior de crear una persona inline se mantiene por compatibilidad, sin afectar expedientes previos. `GET /cases/{id}` devuelve un borrador sin tareas de manera válida. No se hace envío automático de invitaciones por email.

**Persistencia y migración:** Alembic `0003_party_registry` habilita `contract_cases.party_id`, permite `workflow_version_id` nulo y correo de contacto nulo, y recupera vínculos existentes por `contract_case_access` (sin borrar datos). La migración se ejecuta por el comando preDeploy de Railway API. **No hay RLS institucional completa** y el piloto sigue limitado a datos sintéticos. La entidad tiene un contacto único en este MVP: representantes múltiples, identificación legal/NIT, roles propios del contratista e invitaciones por canales son posteriores.

**Verificaciones de V6.4:** GitHub Actions commit funcional `42fbc0fa8ea36deef52432417e0a560937bf1944`: **45 pruebas backend aprobadas**, `vue-tsc` + Vite aprobado. Despliegues Railway Web `f6479ef2041a64033d9904a1984caf77d3d31c05` y API `42fbc0fa8ea36deef52432417e0a560937bf1944` exitosos; PostgreSQL en línea. Aún no se ha recorrido manualmente la nueva UI con dos cuentas Google. MAIRA sigue sin GEMINI API Key, por lo que no genera flujos del PDF.

## V6.3 — Historia de la primera ejecución entre dos portales

La V6.3 introdujo Gestión Contractual y Mi Contratación, versiones publicadas, expedientes, actividades por lado, correcciones y auditoría. En esa versión el alta de un contratista estaba incrustada en la creación de un expediente con plantilla obligatoria. **Ese acoplamiento fue eliminado en V6.4.** Se conserva el motor, la seguridad por tenant del piloto y la funcionalidad de doble portal.

## Smart Contract V6.2 — Pantalla de acceso corporativo

- Página de acceso Google con el mismo lenguaje visual de Smart Service Desk: fondo gris claro, tarjeta blanca centrada, logotipo Smart de la referencia, título Smart Contract, texto directo y un botón auténtico Google Identity Services.
- Marca Smart con su wordmark multicolor y texto extraído y depurado de la imagen facilitada por el usuario. El logo aparece en el login y en la navegación. Se conserva el favicon azul sólido ya aprobado para el navegador.
- La interfaz no muestra el espacio de trabajo sin identidad verificada. El servidor valida el ID token de Google, la audiencia y la lista de usuarios permitidos en GET /api/v1/maira/session; la sesión del piloto se mantiene únicamente en memoria (se pierde al recargar).
- La carga con MAIRA reutiliza la sesión Google del login, sin segundo botón ni doble inicio de sesión.
- **Límite:** este login es una puerta controlada para Development y la prueba MAIRA; NO confiere roles, pertenencia a tenant, RLS ni derechos de publicación institucional. Los endpoints multiempresa existentes siguen requiriendo sus propias credenciales. Sin Gemini aún no habrá interpretación documental.

## MAIRA V6.1 — Validaciones de procedencia y borradores

- MAIRA registra el número de paso, cita original, página y confianza dentro de la configuración de cada nodo propuesto. Se muestran en **Propiedades** al seleccionar una etapa.
- La API rechaza pasos de origen duplicados, nodos con mapeos contradictorios y referencias de origen incompatibles; conserva la validación del grafo acíclico.
- **Aplicar propuesta** requiere una confirmación adicional para evitar sustituir el borrador que existe en el navegador. Si falla la validación local, restablece el estado anterior.
- El inicio de sesión Google puede prepararse cuando el cliente OAuth esté configurado aunque Gemini siga pendiente.
- GitHub Actions V6.1: 26 pruebas Python correctas y compilación Vue correcta; servicios Railway Web/API en SUCCESS. No se ha realizado la prueba de un documento real contra Gemini.

**Estado de credenciales en Railway:** la lista de prueba `SMART_MAIRA_ALLOWED_EMAILS` está configurada para `andres@wearesmart.co`. Siguen ausentes `SMART_GOOGLE_CLIENT_ID` y `SMART_GEMINI_API_KEY`. No subir claves a repositorio, Drive ni al chat. Sin esas dos configuraciones el análisis queda correctamente bloqueado.

## MAIRA V6.0 — Primera prueba de interpretación (piloto limitado)

Desde **Flujos → Crear con MAIRA** el Configurador puede seleccionar un archivo PDF, PNG, JPG o TXT (máximo 6 MB), autenticarse con una cuenta Google explícitamente permitida y solicitar que Gemini analice el documento. MAIRA propone un workflow declarativo con nodos y dependencias, una tabla de pasos originales con citas cortas, páginas, nivel de confianza y dudas para validación humana. El borrador debe revisarse antes de aplicarse al editor.

**Estado actual:** UI y API desplegadas, GitHub Actions completa (22 pruebas) y Railway API/Web SUCCESS. El cliente OAuth Google y la clave Gemini **NO** están configurados en este proyecto: el botón muestra una indicación de configuración pendiente y **no puede analizar ningún documento aún**. Esto es deliberado para no crear una carga pública de documentos. Variables requeridas en API: `SMART_GOOGLE_CLIENT_ID` (cliente OAuth Web del dominio Development), `SMART_MAIRA_ALLOWED_EMAILS` (lista de correos autorizados) y `SMART_GEMINI_API_KEY` (clave de Google AI Studio); opcional `SMART_GEMINI_MODEL` con valor predeterminado `gemini-2.5-flash`. No subir credenciales a GitHub ni a Drive.

El análisis devuelve un borrador **sin persistencia en el servidor**; el archivo se envía a Gemini con el consentimiento del usuario autenticado, la carga se limita a tipos reconocidos, validación de cabeceras y tamaño, y la propuesta se valida con el motor existente. Al aceptar, se guarda únicamente en localStorage del navegador. Solo pruebas con documentos sintéticos/autorizados; faltan RLS, gobierno del tenant, retención institucional y revisión de seguridad.

## Ajuste de identidad V5.6

- Resumen: el emblema **MAIRA / AI AGENT** reemplaza la figura cuadrada SMART; ahora es circular, centrada dentro de los anillos y sin la sensación de objeto superpuesto.
- Se conserva **exactamente** el degradado original del Resumen `#10223f → #153968 → #164578` y se aplica la misma familia cromática a la identidad de MAIRA, sustituyendo el azul verdoso previo.
- Chips externos reubicados para no tapar el emblema y ajuste responsive. Sin cambios en API, BD, flujos ni integración Gemini.

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

## Favicon y marca visual · V6.1.1

Smart Contract utiliza el icono aprobado del usuario: geometría abstracta de nube y tres barras ascendentes en azul sólido `#0040DB`, fondo transparente, sin degradado ni 3D. Está disponible como `web/public/favicon.svg` y `web/public/favicon-64.png`. `web/index.html` referencia SVG con respaldo PNG, y la marca de la barra lateral utiliza el mismo emblema en lugar de la S provisional. No afecta la identidad separada de MAIRA ni el backend.

Entrega funcional: commit `d15d44dae6dfaf2ca3f03810a3b0ac916549f74b`; GitHub Actions PASS y Railway Web SUCCESS, API y Postgres sin cambios. La integración Gemini continúa pendiente de credenciales propias de Smart Contract. La marca de Google Auth Platform deberá llamarse `Smart Contract` y utilizar un OAuth Web Client con origen `https://web-development-80ecf771.up.railway.app`, sin redirección, dado que la app usa Google Identity Services por callback de JavaScript.
