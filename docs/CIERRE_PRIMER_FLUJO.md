# Cierre del primer workflow — Smart Contract

## Fuente única

`Process Flowchart clico contract V2.pdf` (2 páginas, título fuente «Ciclo de contratación v2»). La fuente fue revisada visualmente y extraída por texto. Contiene 23 pasos numerados, identificados por 1, 2, 2.1, …, 13. Todos están conectados por las flechas del diagrama: 25 nodos en total con Inicio y Fin, 24 conexiones documentales. No hay compuertas condicionales dibujadas.

## Experiencia que debe terminarse

1. Workflow Studio conserva los **23 pasos y su numeración original**, sus flechas y los roles originales: ADMINISTRADOR, ASPIRANTE, SISTEMA, JURIDICO, SUPERVISOR, FINANCIERO y SST.
2. «Vista operativa» convierte **ese mismo workflow**, sin modelos paralelos, en la interfaz de las dos partes. El ASPIRANTE se visualiza por ahora como contraparte externa y los demás roles como organización, **solo para revisar la interfaz**.
3. La visualización no debe presentarse como contrato ejecutable, ni crear expedientes, enviar mensajes, cargar documentos o firmar. Los campos que no constan en el PDF se dejan sin configurar.
4. La pregunta de alcance sobre aspirante/persona natural y la confirmación de responsables y campos debe resolverse antes de cualquier publicación.
5. Una vez validada la vista interna, el configurador podrá compartir explícitamente la **misma representación** con una cuenta externa registrada; desde /prestador verá solo su proyección de lectura.

## Aislamiento de Famisanar

La iniciativa Famisanar y `web/src/famisanarCase.ts` permanecen como trabajo futuro en el historial del repositorio. **No se cargan al inicio, no aparecen como recomendación ni como opción en la navegación del ejercicio original.** No se alteran sus datos, archivos ni versiones de workflow.

## Criterio de cierre técnico

- El navegador muestra `Ciclo de contratación v2 · Documento original` como proceso inicial.
- La Vista operativa contiene 23 actividades y el diseñador los 25 nodos/24 enlaces.
- Los botones Contratante/Contratista muestran la misma secuencia con diferentes roles y permisos visuales.
- Una segunda cuenta puede abrir la vista compartida de lectura sin activar un expediente.
- El borrador local antiguo de dos tareas se archiva sin borrarse.
- Cualquier publicación legal sigue bloqueada hasta confirmación humana de responsabilidades, alcance y reglas.


## Continuidad Smart Contract 3 · V6.6.10

- En Development, después del inicio de sesión del configurador, el flujo `Ciclo de contratación v2` de Hospital Smart se recupera desde PostgreSQL (borrador asociado a su registro), no desde la copia local del navegador.
- Personas y empresas muestra un botón **Editar diagrama** para el último borrador del diseñador y mantiene **Abrir ficha** para consultar otros flujos y expedientes.
- El editor inicia en **Lienzo** para ver las 25 tarjetas y 24 conexiones en un único espacio; **Recorrido** y **Vista operativa** siguen disponibles como perspectivas alternativas del mismo workflow.
- Se distingue la **versión guardada en PostgreSQL** de los **cambios sin guardar**. Guardar cambios actualiza el mismo borrador institucional, sin crear duplicados ni contratos.
- La fuente documental original continúa disponible como copia de referencia. No altera el borrador institucional salvo que el configurador guarde explícitamente esa copia.
- Se conservan los controles de revisión y publicación; no se activa expediente ni se infieren campos ausentes del PDF.

### Validación funcional aún necesaria

- Acceso Google autorizado → apertura del diagrama guardado de Hospital Smart → mover una etapa → editar/conectar → guardar cambios → cerrar sesión → volver a ingresar y verificar persistencia.
- Revisar por separado publicación y ejecución real con dos participantes; no confundir vistas previas con contratos activos.

## Administrador institucional · V6.6.11

- Alta inicial autorizada para la cuenta Google verificada indicada en la variable de Railway API `SMART_CONTRACT_INITIAL_ADMIN_EMAIL`, únicamente en Smart Contract Development.
- La cuenta recibe los tres roles institucionales actuales: `ADMIN`, `CONFIGURADOR` y `OPERADOR`, dentro del único tenant que contiene el flujo original de Hospital Smart. No tiene acceso global a otras instituciones ni privilegios de infraestructura.
- La pertenencia se crea en `memberships` en el primer inicio de sesión Google; los eventos se auditan como `DESIGNATED_ADMIN_FIRST_LOGIN_GRANTED`.
- El alta falla cerrada si hay más de un tenant candidato, si no existe el borrador original o si el usuario fue desactivado. Si se revocan permisos después, el marcador de auditoría impide recrearlos.
- El acceso MAIRA reconoce miembros `ADMIN` activos y verificados por Google además de la lista piloto actual; no autoriza por correo arbitrario ni solo por variable de invitación.
- No se crean expedientes, contratos ni registros sintéticos para dar el acceso. Mantener la verificación de Google y retirar la variable de alta inicial una vez utilizado este mecanismo.
- Esta habilitación no reemplaza una pantalla institucional de administración y revocación de usuarios, pendiente de diseño posterior.
