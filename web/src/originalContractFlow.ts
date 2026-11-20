/**
 * First Smart Contract exercise. Transcribed from:
 * "Process Flowchart clico contract V2.pdf", two pages (Ciclo de contratación v2).
 *
 * The 23 numbered activities and 24 directional connections are from the PDF.
 * Actor-side mapping is only a proposal for preview (ASPIRANTE = counterpart).
 * No document fields, approvals, timing, legal validity or execution are invented.
 */
type ActorSide='CONTRATANTE'|'CONTRATISTA'
type ActivityKind='FORM'|'NOTIFICATION'|'DOCUMENT_REVIEW'|'DOCUMENT_REQUEST'|'DOCUMENT_GENERATION'|'APPROVAL'|'SIGNATURE'
type DocumentaryNode={
 id:string;label:string;kind:ActivityKind|'START'|'END';role:string|null;
 policy:'ORG_REQUIRED';enabled:boolean;
 config:{
   actor_side:ActorSide|'REVISAR';source_step?:string;source_excerpt?:string;
   source_page?:number;source_confidence?:string;execution_mode:'MANUAL';
   fields:never[];instructions:string;position:{x:number;y:number};
   party_scope_pending?:boolean
 }
}
export type OriginalFlow={
 key:string;name:string;modality_key:null;
 nodes:DocumentaryNode[];edges:{source:string;target:string}[];
 metadata:Record<string,unknown>
}
const activities=[
 ['1','CREACIÓN DE USUARIOS Y PROYECTOS','ADMINISTRADOR','FORM',1],
 ['2','REGISTRO DE PERSONAL A CONTRATAR','ASPIRANTE','FORM',1],
 ['2.1','CORREO CON DOCUMENTOS DEL ASPIRANTE','SISTEMA','NOTIFICATION',1],
 ['3','VERIFICACIÓN DE DOCUMENTOS CARGADOS','JURIDICO','DOCUMENT_REVIEW',1],
 ['4','CORREO APROBACIÓN DOCUMENTOS','SISTEMA','NOTIFICATION',1],
 ['4.1','CORREO SOLICITUD DE PRESUPUESTAL','SISTEMA','NOTIFICATION',1],
 ['5','SOLICITUD DE REGISTRO PRESUPUESTAL','SUPERVISOR','DOCUMENT_REQUEST',1],
 ['5.1','CORREO DE SOLICITUD REG. PRESUPUESTAL','SISTEMA','NOTIFICATION',1],
 ['6','CARGA Y APROBACIÓN DE REG. P','FINANCIERO','APPROVAL',1],
 ['6.1','CORREO CARGA R. PRESUPUESTAL','SISTEMA','NOTIFICATION',1],
 ['7','CREACION DEL CONTRATO','JURIDICO','DOCUMENT_GENERATION',1],
 ['7.1','CORREO CREACIÓN DE CONTRATO','SISTEMA','NOTIFICATION',2],
 ['8','FIRMA DE CONTRATO','ASPIRANTE','SIGNATURE',2],
 ['8.1','CORREO CON CONTRATO DEL ASPIRANTE','SISTEMA','NOTIFICATION',2],
 ['8.2','CORREO AL SUPERVISOR','SISTEMA','NOTIFICATION',2],
 ['9','TRÁMITE DE PÓLIZA Y CARGA DOCUMENTO','SUPERVISOR','DOCUMENT_REQUEST',2],
 ['9.1','CORREO DE CARGA','SISTEMA','NOTIFICATION',2],
 ['10','APROBACIÓN DE POLIZA','JURIDICO','APPROVAL',2],
 ['10.1','CORREO APROBACIÓN POLIZA','SISTEMA','NOTIFICATION',2],
 ['11','INFORMACIÓN AFILIACIÓN ARL','SUPERVISOR','FORM',2],
 ['12','CARGA CERTIFICACIÓN ARL','SST','DOCUMENT_REVIEW',2],
 ['12.1','NOTIFICACIÓN DE CERTIFICADO','SISTEMA','NOTIFICATION',2],
 ['13','ACTA DE INICIO','SUPERVISOR','DOCUMENT_GENERATION',2]
] as const
function point(index:number,total:number){
 const columns=Math.min(5,Math.ceil(Math.sqrt(total)))
 const row=Math.floor(index/columns)
 const col=row%2===0?index%columns:columns-1-index%columns
 return {x:col*315+35,y:row*175+30}
}
export function buildOriginalContractFlow():OriginalFlow{
 const nodes:DocumentaryNode[]=[
   {id:'original_start',label:'Inicio',kind:'START',role:null,
    policy:'ORG_REQUIRED',enabled:true,
    config:{actor_side:'REVISAR',execution_mode:'MANUAL',fields:[],
      instructions:'Inicio del diagrama original. No es una actividad contractual por sí mismo.',
      position:point(0,25)}},
   ...activities.map(([step,label,role,kind,page],i)=>{
      const side:ActorSide=role==='ASPIRANTE'?'CONTRATISTA':'CONTRATANTE'
      return {id:'original_'+step.replace('.','_'),label:step+' · '+label,
       kind:kind as ActivityKind,role,policy:'ORG_REQUIRED' as const,enabled:true,
       config:{
        actor_side:side,source_step:step,source_excerpt:label,
        source_page:page,source_confidence:'alta',
        party_scope_pending:role==='ASPIRANTE',
        execution_mode:'MANUAL' as const,fields:[] as never[],
        instructions:'Rol literal del PDF: '+role+'. Página '+page+
          '. El lado ejecutor de '+(side==='CONTRATISTA'?'ASPIRANTE':'la entidad contratante')+
          ' se utiliza únicamente para previsualizar; confirmar antes de publicar.',
        position:point(i+1,25)
       }}
    }),
   {id:'original_end',label:'Fin del diagrama',kind:'END',role:null,
    policy:'ORG_REQUIRED',enabled:true,
    config:{actor_side:'REVISAR',execution_mode:'MANUAL',fields:[],
      instructions:'Final documental después de ACTA DE INICIO, sin atribuirle una aprobación legal.',
      position:point(24,25)}}
 ]
 const edges=nodes.slice(0,-1).map((n,i)=>({source:n.id,target:nodes[i+1].id}))
 return {
   key:'SMART_CICLO_CONTRATACION_V2',
   name:'Ciclo de contratación v2 · Documento original',
   modality_key:null,nodes,edges,
   metadata:{
    source:'smart-contract-original-pdf',
    source_file:'Process Flowchart clico contract V2.pdf',
    source_pages:2,source_steps:23,
    source_actors:['ADMINISTRADOR','ASPIRANTE','SISTEMA','JURIDICO','SUPERVISOR','FINANCIERO','SST'],
    scope:'contratacion-de-personal-aspirante',
    draft:true,requires_review:true,review_confirmed:false,
    source_reviewed:false,presentation_only:true,
    maira_review_questions:[
      'El documento original describe un ASPIRANTE (persona natural). ¿La prueba conserva ese alcance o pretende adaptarse a una persona jurídica?',
      'Confirma si ASPIRANTE corresponde al portal externo y los otros roles al contratante. No se han aprobado las asignaciones.',
      '¿Qué datos y documentos específicos se deben solicitar en cada formulario o solicitud? El PDF no define campos obligatorios.',
      'Confirma el alcance de la firma, la póliza, el registro presupuestal y las notificaciones antes de habilitar cualquier ejecución.'
    ],
    maira_dialogue:{scope_decision:'',completed:false,questions_total:5,answers:[]},
    source_connections_verified:'transcribed-from-original-two-page-arrows',
    publication_status:'BLOCKED_PENDING_REVIEW'
   }
 }
}
