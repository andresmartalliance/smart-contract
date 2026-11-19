# Smart Contract V6.3 — Arquitectura integral y estado real

## Dos experiencias sobre el mismo motor — V6.3

**Gestión Contractual:** experiencia de la entidad contratante, destinada al usuario con membresía y rol de `ADMIN`, `CONFIGURADOR` u `OPERADOR` dentro de una institución. Configura actividades, publica una plantilla manual de prueba y crea expedientes con invitaciones de correo. El piloto únicamente admite publicación de un grafo sin condiciones y con componentes manuales ejecutables. Acciones críticas quedan registradas en auditoría. Este permiso no se confiere por mera autenticación Google, sino por membresía de base de datos validada para cada petición.

**Mi Contratación:** experiencia para personas naturales y jurídicas identificadas por su correo Google verificado y expresamente invitadas a un expediente. Solo muestra expedientes vinculados al correo invitado y las actividades del lado `CONTRATISTA`. No puede ver ni completar tareas internas; sí responder sus formularios y corregir una tarea devuelta. En el piloto no existen adjuntos, firma electrónica ni notificaciones de correo automáticas.

**Modelo persistente:** se conservan `Tenant`, `Membership`, `WorkflowVersion`, `ContractCase` y `AuditEvent`. La migración Alembic `0002_portals` incorpora `ContractParty`, `ContractCaseAccess` y `ContractTask` para modelar la contraparte por institución, acceso por expediente y actividades con campos, estado y respuesta. Cada tabla nueva incluye `tenant_id` e índices/constraints relevantes. La API aplica el aislamiento mediante filtros tenant/expediente; **RLS PostgreSQL sigue sin verificarse/implementarse**. No usar esta versión con documentos reales.

**Declaratividad:** el nodo del workflow define `config.actor_side` (`CONTRATANTE` o `CONTRATISTA`), además de responsable, campos y dependencias. Los nodos producen tareas automáticamente, sin pantallas especializadas por PGP, cápita, evento ni otra modalidad. La aplicación permite configurar la parte ejecutora en Propiedades. Para facilitar la primera validación incluye una **plantilla sintética de doble portal**, pero esta no sustituye el diagrama que MAIRA deberá interpretar cuando Gemini se habilite.

**API piloto:** `GET /api/v1/portal/session` determina el acceso Google/membresías/invitaciones; `POST /demo/setup` crea únicamente institución ficticia y solo para el correo de la allowlist con feature flag habilitado; `GET /workflows` y `POST /workflows/publish`; `GET/POST /cases`; `GET /my-cases`; `GET /cases/{id}`; `POST /cases/{id}/tasks/{task_id}/complete` y `/return`. Publicación de piloto se limita a tipos de etapa manuales permitidos; no simula firma, integraciones, generación de documentos ni condiciones. Correo invitado obtiene acceso al expediente tras Google Sign-In sin enviar mensajes automáticos.

**Control de estados:** desde `START` se habilitan tareas cuya totalidad de dependencias estén completadas; `END` se completa automáticamente al finalizar. La devolución solo se permite si una tarea de contratista terminó y ninguna tarea posterior no terminal ha sido completada. Las acciones dejan `AuditEvent` con institución y actor; no hay historial visible en frontend aún.

**Pruebas y operación:** GitHub Actions final V6.3 pasó **37/37 tests backend** y frontend build; Railway web/API/Postgres online, servicio API tiene comando preDeploy `alembic upgrade head`. Se activó la bandera solo en Development `SMART_PORTAL_DEMO_ENABLED=true` para correo administrativo autorizado. No se han hecho pruebas con dos cuentas Google en navegador ni consulta independiente al esquema físico PostgreSQL; el éxito del despliegue no debe confundirse con E2E institucional. El login OAuth sigue dependiendo de que cualquier segundo correo invitado esté en Google Auth Platform como *test user*, mientras la aplicación esté en Testing.

**Pendiente antes de uso institucional:** selección multi-tenant explícita para administradores con varias membresías; gestión de usuarios/invitaciones con expiración y aceptación; RLS real; identidad de usuarios externos no Google; adjuntos cifrados; versionado más rico de expedientes; mensajería; firma; automatizaciones; auditoría visible; SLA; controles contractuales y seguridad jurídica.

## Acceso Google y marca Smart V6.2

UI: login centralizado con Google Identity Services; no hay acceso al workspace hasta que la API verifique ID token y correo permitido. Se mantiene la credencial exclusivamente en memoria, sin localStorage ni cookies accesibles desde JavaScript para credenciales. Al salir se descarta el token. Las cargas de MAIRA reutilizan la identidad. Endpoint /api/v1/maira/session usa _verify_identity y devuelve correo y alcance restringido de piloto.

La marca Smart se recortó de la captura entregada por el usuario (solo logo corporativo, PNG RGBA) y se coloca en login y sidebar. El favicon sólido azul sigue vigente.

Seguridad: identidad Google no equivale a sesión institucional multiempresa, ni habilita el REST API de workflows protegido por JWT y membresía. No hay asignación tenant, RLS operativa ni autorización de publicar. No usar datos reales. Falta realizar prueba E2E de OAuth en navegador y configurar Gemini API Key propia de Smart Contract.

## Controles ampliados MAIRA V6.1

La procedencia documental acompaña ahora al nodo (`config.source_step`, `config.source_excerpt`, `config.source_page`, `config.source_confidence`) durante la importación al frontend y la exportación. Las referencias se muestran en el inspector de propiedades. La API rechaza números de paso repetidos, varios pasos que apunten al mismo nodo y referencias contradictorias. Es control de consistencia del modelo; **no demuestra exhaustividad frente al PDF**: eso requiere comparar el resultado de IA con el documento original en una prueba real.

Una propuesta no se aplica al flujo en un solo clic: antes se confirma que el borrador local será reemplazado. Si la validación falla, se restaura el flujo previo. El esquema de campos y reglas es el existente; no se ha creado persistencia institucional.

La cuenta de prueba permitida está configurada en Railway como `SMART_MAIRA_ALLOWED_EMAILS=andres@wearesmart.co`. Todavía se requieren `SMART_GOOGLE_CLIENT_ID` (cliente web nuevo, origen HTTPS autorizado) y `SMART_GEMINI_API_KEY` (clave específica de Smart Contract); ni GitHub ni Drive deben recibir su valor.

Commit funcional `89a92fb6708a9cdbd0b7e47d46849961b074dddf`: GitHub Actions CI exitoso, **26 pruebas backend**, frontend build exitoso; Railway Web/API SUCCESS, Postgres ONLINE sin alertas. Gemini E2E y prueba de navegador aún **NO** ejecutadas. No presentar workflow fabricado como prueba.

## Flujo de prueba MAIRA V6.0 — Documentos a workflows

Entrada de usuario: **Flujos → Crear con MAIRA → subir PDF/imagen/TXT → analizar → comparar pasos originales → aceptar propuesta → editar**.  El texto original se manda a Gemini únicamente tras verificar un ID token de Google OAuth y que el correo pertenece a una lista explícita del proyecto Smart Contract. MAIRA genera JSON de nodes/edges (sin codificar modalidades). El servidor valida esquema, DAG, rol de aprobaciones y trazabilidad de los nodos a los pasos. Responde documento→paso→nodo y dudas/observaciones. La aceptación se realiza con acción explícita y conserva el flujo como borrador local.

API:
- GET `/api/v1/maira/workflow-import/status`: devuelve disponibilidad sin exponer secretos.
- POST `/api/v1/maira/workflow-import`: multipart con Google ID token; PDF, PNG, JPG y TXT hasta 6 MB.
- GET `/api/v1/maira/capabilities`: contrato de compatibilidad mantenido.

Variables de Railway API requeridas: `SMART_GOOGLE_CLIENT_ID`, `SMART_MAIRA_ALLOWED_EMAILS`, `SMART_GEMINI_API_KEY`, opcional `SMART_GEMINI_MODEL`. **La lista de correos está configurada para el piloto; faltan el client ID OAuth y la clave Gemini.** No copiarlas desde otros proyectos ni guardarlas en GitHub/Drive.

La primera prueba de archivo debe usar «Process Flowchart clico contract V2.pdf», con pasos numerados, correos, revisión jurídica, presupuestos, contrato/firma, póliza, ARL y acta de inicio. La IA no debe fingir que es un workflow de red prestadora de Famisanar. Su mapeo real no está comprobado porque faltan credenciales.

Validación: GitHub Actions para commit de código `62d2309ffd30679c118ca3672f886e20b1bb63d9` PASS con 22 tests backend y build web. Railway web SUCCESS `b25596f1cad95d3439fe70910baa40fd346d91e5` y API SUCCESS `62d2309ffd30679c118ca3672f886e20b1bb63d9`. No se ha ejecutado una prueba E2E de Gemini ni una captura automática del UI. Se preservaron flujos, diseño visual y arquitectura existentes.

Limitación de seguridad: la credencial Google en el piloto es independiente de la autenticación multiempresa productiva. No es base para publicación, expedientes reales, intercambio de documentos empresariales o uso institucional hasta implementar roles y políticas a nivel de tenant, auditoría y consentimiento específicos. No exponer documentación confidencial con este prototipo.

## Objetivo de producto
Plataforma SaaS multiempresa de workflows contractuales dinámicos, con bibliotecas de campos, bloques, políticas, reglas, cálculos y plantillas. Contratación de la red prestadora es el primer caso: no es una limitación de diseño. Las modalidades se registran como datos, nunca como condicionales de implementación codificados para evento, cápita, PGP u otra modalidad.

## Usuarios y separación de responsabilidades
- **Configurador:** diseña y modifica flujos, define políticas y reglas, compara versiones y solicita publicación.
- **Operador:** tramita expedientes y tareas con permisos granulares para Jurídica, Red, Financiera, Técnica, Actuarial y aprobadores.
El frontend V5.5 es un editor local público y todavía NO aplica permisos de usuario; el backend sí exige JWT + membresía de tenant. No conectar el editor a operaciones reales sin identidad segura.

## Multiempresa
Cada institución se asocia a `tenant_id`, todos los endpoints actuales resuelven la membresía en el backend, y los registros se filtran por tenant. La capa definitiva requiere además RLS PostgreSQL, almacenamiento segregado, logs y jobs tenant-aware, pruebas adversariales de autorización y aislamiento del conocimiento de MAIRA. Los documentos, tarifas y manuales pertenecen al cliente y jamás se convierten automáticamente en biblioteca global.

## Workflow core
- Esquema declarativo: `key`, `name`, `modality_key` libre, `nodes`, `edges`, `metadata`.
- Nodos: tipo, rol, política, habilitado, condición DSL, configuraciones y campos.
- Enlaces: dependencias con condición de ejecución opcional, soportando bifurcación y paralelismo por grafo.
- Restricciones: un inicio, una o más finalizaciones, DAG sin ciclos, todos los nodos alcanzables desde inicio y capaces de alcanzar un final, roles en aprobaciones, requisitos protegidos no apagables.
- Políticas: `LEGAL_LOCKED`, `ORG_REQUIRED`, `CONDITIONAL`, `OPTIONAL`; este editor no puede rebajar directamente la protección de una etapa existente. En producción el bloqueo se deberá cotejar con una biblioteca jurídica institucional firmada, no solo con el JSON del cliente.
- Validación local + backend con control de identidad. Simulación local con datos de ejemplo y reglas conocidas. El simulador no toma decisiones jurídicas ni ejecuta tareas.
- Borrador local: localStorage y JSON. **No** publicación ni persistencia institucional en frontend; un mismo navegador puede recuperar su borrador, pero no hay colaboración ni control de acceso allí.
- Las posiciones del grafo viven en `config.position`. Los campos propios usan `config.fields`, preparados para renderización futura de formularios sin pantallas dedicadas.

## MAIRA
MAIRA será el agente contractual para proponer flujos, recuperar políticas, analizar documentos, diligenciar minutas y orientar cada tarea. Se ejecutará con herramientas backend por tenant, auditoría y permisos. La interfaz actual comunica que Gemini no está conectado: no hay simulación engañosa de agente ni autonomía de publicación.

## Conocimiento y activos reutilizables
Smart puede reutilizar componentes, esquemas y plantillas genéricas de su propiedad. Los manuales institucionales, negociaciones, notas técnicas, tarifas, expedientes y comentarios son privados. MAIRA solo podrá convertir hallazgos en propuestas versionadas; un responsable autorizado decide si aplicarlas.

## Infraestructura y continuidad
GitHub privado `andresmartalliance/smart-contract` rama `main`, Railway `smart-contract` ambiente `development`, `api`, `web`, `Postgres`. El documento maestro de continuidad de Drive se actualiza **integralmente** tras cada paquete. Una release = mismo commit/código/reglas/API/frontend + pruebas + estado verificado. Evitar commits aislados y despliegues automáticos innecesarios. Los conectores de ChatGPT tienen permisos más amplios que estos recursos; operar exclusivamente dentro del proyecto conforme a la política documentada.

## Corrección visual V5.6 — Emblema y paleta MAIRA

Se conserva el gradiente original aprobado del Resumen `linear-gradient(114deg,#10223f,#153968 70%,#164578)`. La forma cuadrada superpuesta y rotulada SMART fue sustituida por emblema circular MAIRA / AI AGENT centrado dentro de los anillos. Los chips exteriores fueron reubicados y el CSS responsive mantiene la forma circular. El panel principal de identidad MAIRA también usa esta familia de azules en lugar del azul verdoso de V5.5.

Sin cambios en flujos, motor de reglas, integraciones, autenticación, backend, SQL ni políticas multiempresa. Se verificará compilación TypeScript/Vite y estado Railway; la prueba visual en navegador sigue pendiente.

## Identidad del agente MAIRA — V5.5

**MAIRA** es un acrónimo de marca: **Multi-tenant AI for Intelligent Review & Agreements**. El descriptor oficial es **Contract Intelligence Agent** y su explicación en español es **Inteligencia artificial multiempresa para revisión inteligente y acuerdos contractuales**.

La identidad visual retoma el lenguaje de NORA como referencia de agente, pero mantiene la paleta propia de Smart Contract: azul profundo y cian. La pantalla principal presenta un emblema MAIRA con círculos concéntricos, el acrónimo completo en inglés y su explicación en español; también se muestran en el panel flotante global y el bloque MAIRA del Resumen. Se conservaron los controles de contexto/acciones locales de V5.4, sin nuevas dependencias ni backend.

El acrónimo no supone que exista una IA activa: Gemini sigue sin conectarse; la interfaz lo indica de forma explícita. No existen inferencias de IA, revisión automatizada de contratos ni conocimiento multiempresa compartido. La separación de conocimiento y los permisos por tenant siguen siendo requisitos pendientes para el uso institucional.

**Verificación:** frontend Vue-tsc + Vite compiló y se desplegó en Railway sobre commit de código `877c27498b25b7110b7822c3ee3758b6dbdf4b3b`; web/API/Postgres figuran online y sin alertas. API omitió despliegue por watch patterns. No hubo pruebas E2E visuales independientes; la captura de referencia NORA es una guía estética, no un recurso externo incrustado.

## MAIRA contextual y persistente V5.4

MAIRA aparece mediante un botón flotante persistente en todo el producto, sin interferir con navegación ni con el Workflow Studio. Un panel a la derecha muestra el módulo actual, el flujo y la etapa seleccionada cuando aplica, métricas locales del borrador y acciones disponibles.

Las acciones expuestas en V5.4 invocan las funciones existentes del editor local (validar, simular, insertar aprobación, exportar JSON y navegar); **no** usan IA generativa ni escriben en el servidor. El panel muestra Gemini no conectado y tampoco ejecuta contratos, aprobaciones institucionales o acceso a documentos.

La futura integración con Gemini utilizará herramientas backend con autorización tenant, auditoría y publicación humana. El panel es el punto de entrada global a ese agente, no un sustituto de la política de permisos.

Los servicios Railway ahora utilizan watch patterns /web/** y /api/** para evitar despliegues automáticos por modificaciones documentales y por cambios del otro servicio. Son ajustes de despliegue, no separación de la base ni infraestructura adicional.

## Diseño visual V5.3 (capa transversal)

Diseño light-premium de Smart: superficies casi blancas, azul profundo, acentos cian/violeta discretos, jerarquía tipográfica, bordes y sombras ligeras. La identidad del producto se mantiene institucional, no videojuego.

- Pantalla Resumen: hero ejecutivo, cuatro métricas provenientes exclusivamente del borrador local (etapas, activas, conexiones y pasos protegidos), proceso actual y estado de MAIRA.
- Workflow Studio: bloques categorizados, nodos diferenciados por tipo en el canvas, panel de propiedades más legible, barra de acciones real (nuevo/importar/exportar), estados visuales y simulación.
- MAIRA: identidad diferenciada y capacidades expresadas en futuro, sin botones que pretendan ejecutar Gemini.
- Navegación: iconos vectoriales internos (sin librerías ni solicitudes externas), estado Development y layout responsive. Foco visible y ajuste de animaciones por preferencia de accesibilidad.
- No se han incorporado funciones contractuales nuevas ni permisos especiales. Todo el guardado sigue siendo local en navegador; no se procesan documentos ni datos reales.

## Estado de entrega V5.5
**Incluye:** editor visual funcional con bloqueos locales, formularios configurables, responsables, conexiones condicionadas, validación, simulación, importación/exportación y recuperación local; backend validado con 14 pruebas de motor y aislamiento.
**No incluye:** Google OAuth; escritura institucional desde navegador; publicación; RLS; integración Gemini; ejecución real de contratos; SIIFA/REPS; matriz de procesos de Famisanar; verificación jurídica de plantillas específicas.
**Antes de prometer MVP:** construir sesión, controles backend/RLS, biblioteca persistente y versionada, publicación formal, expediente operativo y MAIRA; luego probar rutas institucionales reales.
