# Smart Contract V6.5.4 — Arquitectura integral y estado real

## V6.5.4 — Extractor documental y compilador determinista de workflows

La inferencia real del 19 nov 2026 con Gemini 3.6 Flash y PDF ~50 KB terminó en HTTP 422 después de ~53.6 s. La API recibía un objeto JSON del proveedor, pero la etapa de validación de grafo/estructura no lo aceptaba. No se guarda el cuerpo del proveedor (privacidad), así que la causa exacta de ese objeto no se conoce.

**Responsabilidades separadas:**

1. \`PROMPT\` pide lista \`steps\` con \`source_step\` (número visible), \`source_excerpt\` literal, \`label\`, \`role\`, \`kind\`, \`page\`, \`confidence\`, \`depends_on\` y \`questions/observations\`. No pide un grafo ejecutable ni IDs de frontend.
2. \`ExtractedDocument/ExtractedStep\` validan campos mínimos y duplicaciones; no eliminan pasos.
3. \`_compile_source_extraction\` genera nodos \`START/END\` y uno por cada paso citado; construye \`source_map\` coherente, conserva numeración/página/confianza, determina \`actor_side\` solo para roles conocidos explícitamente, y usa \`HUMAN_DECISION\` para una aprobación sin rol.
4. Si \`depends_on\` es null se usa el paso anterior como secuencia **provisional**, agregando aviso visible en observaciones. Dependencias declaradas deben apuntar a números existentes; se rechazan ciclos o referencias inexistentes. No se inventan anexos, ni se reinterpretan correos como tareas del destinatario.
5. \`_parse_proposal\` sigue siendo el validador final de integridad y conexión DAG, adjunta trazabilidad al nodo y prepara el layout; las versiones previas con workflow completo siguen funcionando.
6. La API devuelve **422 con motivo acotado en español** cuando la extracción está incompleta o supera límites, evitando el mensaje genérico previo. Los logs no incluyen documento, secretos, correo ni contenido de la respuesta.

**Seguridad y producto:** la importación conserva autorización Google allowlist, los previews por tercero se almacenan solo tras guardar explícitamente y validación de pertenencia al tenant. No existe ejecución autónoma ni firma. No hay inferencia que garantice cumplimiento jurídico; todo es borrador para revisión.

**Validación técnica:** CI run 44580869574 (68/68 pruebas API + Vue build PASS), API Railway SUCCESS commit 7867cc06a244ecd084123af75d80e7a4dad94c3d. Se verificó compilación simulada de 23 pasos con source excerpts, tipos de tarea, roles y dependencias, no una ejecución real de la IA con el PDF original. **Prueba final pendiente**: misma carga desde Hospital Smart, evaluación humana del número y contenido de pasos; no marcar como aceptado antes.

## V6.5.3 — Selección explícita de modelo Gemini operativo

La prueba autenticada ejecutada por el usuario devolvió 404 para `gemini-2.5-flash`; este era el default de `_gemini_model`. El cambio a `gemini-3.6-flash` se aplica tanto en el fallback de código como en `SMART_GEMINI_MODEL` del servicio API Railway Development. Los endpoints `POST /workflow-import/check-connection` y `POST /workflow-import` comparten la configuración, sin duplicar modelo ni clave. Google AI Studio documenta 3.6 Flash como estable con capacidades PDF y salida JSON estructurada. No se hace fallback silencioso a un modelo más caro, no se crea un segundo servicio y no se altera la autenticación.

La variable `SMART_GEMINI_API_KEY` continúa oculta y sin modificarse. El uso de inferencia real requiere el ID token Google del usuario autorizado; se debe confirmar éxito con la prueba del botón en el frontend. Una entrada de `models.list` no sería evidencia suficiente por sí sola de permiso de generación, ya que el recurso puede estar listado sin autorizar generateContent.

## V6.5.2 — Diagnóstico de inferencia Gemini

**Incidente observado:** Railway API HTTP POST /api/v1/maira/workflow-import a ~17:11:46Z del 19 nov 2026 devolvió HTTP 502 en 434 ms. La autenticación, validación de archivo y estado inicial se completaron. El código anterior de `_call_gemini` aplicaba `raise_for_status` y colapsaba cualquier fallo de Google a un genérico «Gemini could not analyze…», sin capturar el estado HTTP del proveedor. El status HTTP del upstream Google NO está en logs anteriores, por tanto no atribuirlo a cuota, clave o modelo todavía.

**Corrección:** helper `_post_gemini` efectúa POST HTTPS con `x-goog-api-key` exclusivamente en servidor. Maneja timeout, errores de transporte, HTTP 400/401/402/403/404/429/500/502/503/504, e identifica de forma acotada API_KEY_INVALID sin devolver contenido arbitrario del proveedor. Los logs nunca contienen clave, respuesta cruda del modelo, documento ni email. `_gemini_model` valida nombre seguro. `_call_gemini` sigue usando el prompt, PDF y _parse_proposal existentes y comparte diagnóstico.

**Verificación real de conectividad:** endpoint protegido `POST /api/v1/maira/workflow-import/check-connection` usa `_verify_identity` Google y una solicitud mínima de `generateContent` (respuesta «OK»), con tiempo máximo de 20 s. A diferencia de `models.list`, prueba que el proyecto pueda ejecutar inferencia, con coste mínimo por invocación. El frontend ofrece botón «Verificar conexión Gemini» junto a Analizar; el usuario decide cuándo activarlo. Fallos son específicos, no genéricos; mantener documentos de prueba sintéticos/autorizados.

**Control de calidad:** CI GitHub run `44575310655` con 58/58 tests Python PASS y Vue build PASS. Railway Web versión `5e37b1ec889aa8ac73e36e6d3fe776db1e012b40` SUCCESS, API versión `2702b12e973f9fb9322901762198deac4650fb40` SUCCESS, Postgres ONLINE. La inferencia con clave real NO se puede afirmar probada hasta que usuario pulse Verificar conexión Gemini y/o cargue PDF y el sistema muestre resultado. RLS institucional y Gemini workflow completo todavía pendientes.

## V6.5.1 — Estado de credenciales de Gemini y observabilidad UX

Railway Development API contiene `SMART_GEMINI_API_KEY` según lectura de nombres con conector Railway. Se verificaron además `SMART_GOOGLE_CLIENT_ID` y `SMART_MAIRA_ALLOWED_EMAILS`. Los valores están redactados y **no se copiaron ni expusieron**. El deployment API más reciente tiene estado SUCCESS, replica online, sin fallas recientes ni trabajo pendiente. La interfaz obtiene `ready`, `gemini_enabled` y `google_enabled` desde `/api/v1/maira/workflow-import/status`; está programada para mostrar el estado veraz. La nueva pantalla de Resumen/Maira ya no dice «Próxima integración» cuando `ready` es true: muestra «Gemini configurado · pendiente prueba». El código del endpoint de análisis es el mismo, y la clave no se lee en el navegador.

**Prueba NO ejecutada:** una inferencia autenticada a Gemini con el PDF de contratación. La presencia de variable no implica validez de API key ni modelo/cuota. El endpoint de importación requiere un Google ID token de cuenta permitida. La conexión de red hacia el endpoint público no pudo comprobarse desde el entorno externo de herramientas; la ejecución se debe verificar en la UI con la cuenta Google del administrador. No se usó documento real ni se generó propuesta artificial.

GitHub commit frontend `3b68670427bc35b319c8608f7115cc276260cd0d`; GitHub Actions run `44573188138` PASS; Railway Web SUCCESS, backend API/Postgres ONLINE. No hay cambios en modelos ni migraciones. Este hito actualiza solo textos y enlaces de estado; preserva V6.5 completa.

## V6.5 — Proceso documental contextual a un tercero

Vista previa trazable por tercero independiente de las plantillas publicadas: `ContractParty` no almacena workflows; `PartyProcessPreview` (nuevo modelo del tenant) referencia `party_id` y una propuesta JSON, mapeos de origen y dudas. Su creación no modifica `WorkflowVersion`, `ContractCase`, `ContractTask` ni `ContractCaseAccess`. Solo un usuario institucional con rol de configuración y acceso al tenant puede guardar la propuesta. Los externos nunca reciben este borrador antes de que se publique y se asocie a un caso.

Flujo técnico: ficha Personas y empresas → crear proceso con Maira (scoped partyId) → cliente añade `party_kind=NATURAL|JURIDICA` al multipart autorizado de Gemini → agente conserva pasos y asigna lados solo con rol explícito; detecta incompatibilidad aspirante/persona jurídica → API valida mapa y DAG → frontend ofrece revisión de actividades por lado (prestador/contratante/por definir) y dependencias → guardar vista previa por tenant en PostgreSQL → reabrir desde ficha del tercero → pasar a diseñador para revisión. No se genera ninguna obligación fuera del diagrama ni se convierte una notificación automáticamente en tarea del destinatario.

El diagrama fuente específico fue revisado: `Process Flowchart clico contract V2.pdf`, 2 páginas, 23 pasos numerados contando los subpasos. Distingue administración, aspirante, jurídica, supervisor, financiero, SST y sistema. Esta fuente es un flujo de contratación de personal; requiere validación humana para aplicarse a una IPS como Hospital Smart. El número de actividades es criterio de revisión de este documento, NO está codificado como regla fija del motor.

Migración `0004_party_process_previews` crea tabla sin modificar expedientes previos. Se guarda una nueva propuesta como `DRAFT_REVIEW`, con `workflow`, `source_map`, `questions`, `observations`, `filename`, `created_by`, `created_at`, `tenant_id` y `party_id`. El PDF no se conserva, solo propuesta. Restricción de 500 mapeos y validación por `_parse_proposal`. Endpoints con filtros y permisos de tenant; acceso externo denegado. Hay pruebas de no publicación, no invitación, aislamiento por institución y rechazo de pasos inventados.

Resultados verificados: CI 50/50 Python tests PASS y Vue-tsc/Vite PASS (commit `5ed5b0df2ad801b0761062b3ba0ba31bf01b0474`). Railway web, api y Postgres online con API SUCCESS. No se verificó el flujo con Gemini en navegador: falta SMART_GEMINI_API_KEY. No habilitar documentos institucionales reales sin RLS y seguridad documental.

## UX MAIRA V6.4.1 — Pulse elegante

El lanzador flotante `.maira-launcher` mantiene su comportamiento original y el estilo de marca aprobado, pero es más compacto: 136 × 50 px (mínimo, en escritorio), y 120 × 47 px en dispositivos móviles. El halo circular del icono usa `@keyframes maira-pulse` (2.7 s `ease-in-out`, iteración infinita), sin alterar botón, estado ni funciones de MAIRA. Respeta media query `prefers-reduced-motion` y conserva `aria-label` y `aria-expanded`. El despliegue modifica solo `web/src/App.vue` y `web/src/style.css`, además de documentación maestra.

## Estado arquitectónico integral V6.4

**Una sola plataforma**, con tres responsabilidades separadas:

- **Personas y empresas:** registro maestro de terceros por tenant, independiente del contrato y del workflow. Puede existir antes de cualquier proceso. Campos MVP: tipo NATURAL/JURIDICA, nombre y contacto Google opcional. El registro puede asociarse a múltiples expedientes. No equivale a una cuenta de usuario ni crea permisos institucionales.
- **Gestión Contractual:** el administrador/operador de una entidad contratante selecciona un tercero existente y crea el expediente `DRAFT` con o sin plantilla. Posteriormente puede asociar una versión publicada de un workflow. Cuando asocia la plantilla se generan tareas y acceso por correo verificado al expediente, siempre que el contacto exista.
- **Mi Contratación:** el contacto externo puede iniciar sesión con Google si su correo está registrado (aunque no tenga expedientes), pero únicamente ve procesos que se activaron y le concedieron `ContractCaseAccess`. No tiene acceso al directorio interno ni a las actividades de la contraparte. La pantalla refleja formularios dinámicos por tarea y permite responder devoluciones.

**Esquema relacional:** `Tenant` + `Membership`; `ContractParty` con `tenant_id`, `kind`, `name`, `contact_email: nullable`; `ContractCase` con `tenant_id`, `party_id: nullable` para compatibilidad con versiones anteriores y `workflow_version_id: nullable` para borradores. `ContractCaseAccess` representa la invitación *por expediente*, no la inscripción en el directorio. `ContractTask` registra tareas generadas por una versión publicada. El histórico de `AuditEvent` incluye PARTY_CREATED/PARTY_UPDATED/PILOT_CASE_CREATED/WORKFLOW_ASSIGNED, entre otros.

**Migración Alembic `0003_party_registry`:** hace `workflow_version_id` y `contact_email` opcionales, agrega índice + FK para `contract_cases.party_id` y rellena vínculos anteriores desde `contract_case_access`. No elimina tablas ni registros; el downgrade solo se permite si no hay datos nuevos incompatibles. Debe ejecutarse automáticamente por `alembic upgrade head` (preDeploy Railway API). **No existe aún comprobación independiente de la migración mediante consulta SQL directa.**

**API:** nuevo `GET /api/v1/portal/parties` (solo operador institucional), `POST /api/v1/portal/parties` (crea maestro), `PATCH /api/v1/portal/parties/{id}` (actualiza datos de contacto sin modificar silenciosamente invitaciones previas), `POST /api/v1/portal/cases` con `party_id` y `workflow_id` opcional, y `POST /api/v1/portal/cases/{id}/workflow` para asignación definitiva al borrador. La actualización del vínculo es transaccional, no se pueden re-asignar expedientes ya activados, se exige que la persona tenga contacto antes de generar invitación; la plantilla debe estar publicada y pertenecer al mismo tenant. El detalle de un borrador sin plantilla muestra tareas vacías, no un error. Se mantiene la forma antigua de payload `party` para no romper clientes de V6.3.

**Seguridad:** cada búsqueda del directorio y la apertura de casos valida membresía institucional o acceso de expediente; el contacto registrado puede iniciar sesión sin privilegios internos. No hay RLS real de PostgreSQL ni selector explícito para varias entidades, y el mecanismo de autenticación Google sigue siendo piloto con lista de usuarios Google Testing para externos. No usar datos de clientes ni documentos personales.

**Motor:** el contrato no lleva workflow hasta que se asocia una versión publicada; después se usa la misma `WorkflowDefinition` declarativa, `config.actor_side`, tareas, auditoría y bloqueos existentes. No existen automatizaciones ni firma real; el piloto restringe deliberadamente los tipos de nodos ejecutables. La UI no obliga a diseñar una plantilla antes de crear entidades o expedientes.

**CI y despliegue verificado:** commit de API `42fbc0fa8ea36deef52432417e0a560937bf1944` con 45/45 pruebas backend y compilación Vue PASS. Frontend `f6479ef2041a64033d9904a1984caf77d3d31c05` y API `42fbc0fa8ea36deef52432417e0a560937bf1944` Railway SUCCESS; Postgres ONLINE. El usuario debe realizar una prueba navegador de creación de tercero → borrador → asociación; no se ha verificado E2E por navegador automatizado.

**Pendientes productivos:** múltiples representantes por empresa; identificadores legales parametrizables (NIT, documento, REPS, etc.) y deduplicación jurídica; roles/SSO multiempresa; RLS; consentimiento/datos reales; notificaciones; versionado avanzado de procesos; firmas e integraciones; almacenamiento documental; Gemini para MAIRA. Los modos PGP, cápita, evento, etc. nunca deben fijarse en código.

## V6.3 — Experiencias duales (antecedente)

La versión previa introdujo las dos experiencias sobre un mismo backend y tareas por rol, con devolución/corrección, auditoría y ejemplo sintético de doble portal. V6.4 conserva ese núcleo, sustituyendo el alta de entidad acoplada a una plantilla obligatoria por el maestro independiente.

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


### V6.5.6 — Resiliencia Gemini: PDF multimodal a lectura textual

Ante 502/503/504 de generación inicial, la segunda solicitud puede ser exclusivamente textual, extraída por pypdf, con límite de dos llamadas total. La extracción es efímera; las dependencias de diagrama quedan provisionales y exige revisión. En ausencia de texto, se conserva un reintento multimodal. No hay alternancia automática de modelos. Pruebas simuladas aprobadas; inferencia real pendiente.
