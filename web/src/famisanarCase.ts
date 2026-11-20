// Famisanar: source-backed FIRST CASE, not the entire 105-row workbook.
// The row text comes from Libro1 2.xlsx, Hoja1. Transitions, role assignments,
// and proposed Boolean field remain unconfirmed by the source owner.
type CaseKind='START'|'VALIDATION'|'FORM'|'DOCUMENT_REQUEST'|'DOCUMENT_REVIEW'|'HUMAN_DECISION'|'END'
type CasePolicy='ORG_REQUIRED'|'CONDITIONAL'
type CaseNode={
 id:string;label:string;kind:CaseKind;policy:CasePolicy;enabled:boolean;role:string|null;
 config:{source_step?:string;source_excerpt?:string;source_confidence?:string;
  actor_side?:'REVISAR';instructions?:string;fields?:{key:string;label:string;type:'boolean';required:boolean}[];
  position:{x:number;y:number}}
}
type CaseEdge={source:string;target:string;when?:{field:string;op:'eq';value:boolean}}
export type FamisanarFirstCase={
 key:string;name:string;modality_key:null;nodes:CaseNode[];edges:CaseEdge[];
 metadata:Record<string,unknown>
}
function sourced(row:number,label:string,kind:CaseKind,x:number,y:number,fields:CaseNode['config']['fields']=[]):CaseNode{
 return {id:'fam_a'+row,label,kind,policy:'ORG_REQUIRED',enabled:true,role:null,
  config:{source_step:'Hoja1!A'+row,source_excerpt:label,source_confidence:'documental',
   actor_side:'REVISAR',position:{x,y},instructions:'Fuente: Famisanar, Libro1 2.xlsx, Hoja1!A'+row+
    '. Responsable y plazo pendientes de validación por Famisanar.',
   fields}}
}
function terminal(id:string,label:string,x:number,y:number):CaseNode{
 return {id,label,kind:'END',policy:'CONDITIONAL',enabled:true,role:null,
  config:{position:{x,y},instructions:'La transición final requiere validación antes de publicar.'}}
}
export function buildFamisanarFirstCase():FamisanarFirstCase{
 const initial:CaseNode={id:'fam_inicio',label:'Inicio · necesidad de contratación',kind:'START',
  policy:'ORG_REQUIRED',enabled:true,role:null,
  config:{position:{x:40,y:50},instructions:'Inicio documental del primer caso; no activa un expediente.'}}
 return {
 key:'FAMISANAR_RED_PRESTADORA_CASO_01',
 name:'Famisanar · Red prestadora · Identificación y prefactibilidad',
 modality_key:null,
 nodes:[
  initial,
  sourced(3,'Identificar la necesidad de contratación','FORM',335,50),
  sourced(4,'Solicitar y realizar la verificación SARLAFT / FPADM del prestador','VALIDATION',630,50),
  sourced(5,'Diligenciar la Ficha de Presentación del Prestador (habilitación REPS, oferta CUPS / CUMS)','FORM',925,50),
  sourced(6,'Realizar el análisis de prefactibilidad. Si no se aprueba, finaliza el procedimiento',
   'HUMAN_DECISION',925,240,[{key:'prefactibilidad_aprobada',label:'¿Prefactibilidad aprobada? (campo propuesto)',type:'boolean',required:true}]),
  sourced(8,'Enviar la propuesta y solicitar oferta y documentos según la modalidad de contrato',
   'DOCUMENT_REQUEST',630,400),
  sourced(11,'Enviar la oferta, los formatos diligenciados y los documentos',
   'DOCUMENT_REQUEST',335,400),
  sourced(12,'Recibir la oferta y los documentos','DOCUMENT_REVIEW',40,400),
  terminal('fam_continua','Continúa la revisión documental · etapa posterior por diseñar',40,580),
  terminal('fam_no_aprobado','Finaliza · prefactibilidad no aprobada',1170,400)
 ],
 edges:[
  {source:'fam_inicio',target:'fam_a3'},
  {source:'fam_a3',target:'fam_a4'},
  {source:'fam_a4',target:'fam_a5'},
  {source:'fam_a5',target:'fam_a6'},
  {source:'fam_a6',target:'fam_no_aprobado',when:{field:'prefactibilidad_aprobada',op:'eq',value:false}},
  {source:'fam_a6',target:'fam_a8',when:{field:'prefactibilidad_aprobada',op:'eq',value:true}},
  {source:'fam_a8',target:'fam_a11'},
  {source:'fam_a11',target:'fam_a12'},
  {source:'fam_a12',target:'fam_continua'}
 ],
 metadata:{
  source:'famisanar-documental',source_file:'Libro1 2.xlsx',worksheet:'Hoja1',
  source_cells:['A3','A4','A5','A6','A8','A11','A12'],
  classification:'BORRADOR_PARA_REVISION',
  prior_pilot:'ARCHIVADO_COMO_REFERENCIA',
  draft:true,requires_review:true,review_confirmed:false,roles_verified:false,dependencies_verified:false,
  party_scope_verified:false,branch_logic_verified:false,
  maira_review_questions:[
   '¿Quién realiza y quién aprueba cada actividad? El Excel no contiene columnas completas de responsables.',
   'En A6, ¿qué evidencia determina que la prefactibilidad fue aprobada y quién la autoriza?',
   '¿Quién envía la oferta de A11 y cuál es el mecanismo de recepción de A12?',
   '¿Qué documentos corresponden a cada modalidad y cuáles son obligatorios?',
   '¿Cómo se coordinan las visitas de IPS nuevas o cuya última visita supera un año (A9 y A15)?',
   '¿Cuándo debe solicitarse la nota técnica de Modelos Económicos (A10)?',
   '¿Cuáles son las reglas de transición entre A6, A8, A11 y A12? La secuencia se propone y no está representada con flechas en el Excel.'
  ],
  maira_dialogue:{scope_decision:'',completed:false,questions_total:1,answers:[]},
  workflow_guidance:'Solo parte del documento de Famisanar. No publica ni activa expedientes. Las condiciones y responsables son propuestas.',
  modality_policy:'CATALOGO_ABIERTO'
 }
 }
}
