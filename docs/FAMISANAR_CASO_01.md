# Famisanar — Caso 01: identificación y prefactibilidad de prestador de salud

**Fuente:** \`Libro1 2.xlsx\`, \`Hoja1\`, celdas exactas A3, A4, A5, A6, A8, A11 y A12.

**Ruta:** prestadores de salud. No mezclar con proveedores administrativos, que aparecen más adelante en el mismo Excel.

**Alcance propuesto:** identificación de necesidad (A3); verificación SARLAFT/FPADM (A4); ficha de presentación y oferta habilitada REPS/CUPS/CUMS (A5); análisis de prefactibilidad con salida negativa explícita (A6); solicitud de oferta y documentos según modalidad (A8); envío de oferta por la contraparte, sujeto a confirmación de responsable (A11); recepción de documentos (A12). El caso termina como borrador al alcanzar la recepción; la evaluación posterior (A14 y siguientes) será otro hito.

**Decisión explícita:** el documento A6 dice que el procedimiento finaliza si la prefactibilidad no se aprueba. El campo booleano y el camino de aprobación son **propuestos**, no metadatos originales del Excel. El motor no debe ejecutar esa decisión hasta validación de Famisanar.

**Responsables:** el Excel no asigna sistemáticamente cargos ni lados contratante/contratista. Todas las actividades quedan \`REVISAR\` y requieren responsable, rol y lado institucional; ni siquiera las inferidas por su redacción se publicarán automáticamente.

**Condiciones y preguntas pendientes:** visita precontractual para IPS nueva o con visita >1 año (A9, A15); nota técnica para las modalidades citadas por el archivo (A10); documentos por modalidad; validación del resultado SARLAFT; plazos, rutas de observación y permisos; papel del área de contratación y de la IPS. Estas condiciones quedan como cuestiones para MAIRA y configuración humana, no como reglas codificadas.

**Configurabilidad:** \`modality_key=null\` y catálogo abierto. Evento, cápita y PGP, mencionadas en la fuente, no constituyen una lista cerrada.

**Estado técnico:** borrador local editable en Workflow Studio, sin publicación de plantillas, sin expediente real ni activación de tareas.

**Contraparte:** el frontend /prestador consumirá únicamente \`/api/v1/portal/my-cases\` y \`/api/v1/portal/cases/{id}\` según identidad Google y autorizaciones existentes. El frontend nuevo no otorga permisos; el backend determina las tareas que puede ver y completar cada lado.

**Criterio próximo:** verificar visualmente el caso en Studio, revisar todas las preguntas y aprobar responsables/condiciones antes de contemplar publicación. Probar portal con dos cuentas autorizadas y datos sintéticos; no usar usuarios de Famisanar reales sin autorización.
