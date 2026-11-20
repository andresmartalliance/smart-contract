<script setup lang="ts">
import { computed, nextTick, onMounted, ref, shallowRef, watch } from 'vue'
import { VueFlow, Position, type Node, type Edge, type Connection } from '@vue-flow/core'
import ProviderPortal from './ProviderPortal.vue'
import WorkflowPresentation from './WorkflowPresentation.vue'
import CompactWorkflowDiagram from './CompactWorkflowDiagram.vue'
import { buildEditableLayout } from './compactFlowLayout'
import { buildOriginalContractFlow } from './originalContractFlow'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

type Screen = 'resumen' | 'personas' | 'contrataciones' | 'prestadores' | 'flujos' | 'maira' | 'configuracion'
type Kind = 'START'|'FORM'|'DOCUMENT_REQUEST'|'DOCUMENT_REVIEW'|'VALIDATION'|'APPROVAL'|'NEGOTIATION'|'CALCULATION'|'DOCUMENT_GENERATION'|'SIGNATURE'|'NOTIFICATION'|'INTEGRATION'|'TIMER'|'JOIN'|'HUMAN_DECISION'|'END'
type Policy = 'LEGAL_LOCKED' | 'ORG_REQUIRED' | 'CONDITIONAL' | 'OPTIONAL'
type Condition = {field:string;op:'eq'|'neq'|'gt'|'gte'|'lt'|'lte'|'in'|'exists';value?: unknown}
type FieldType = 'text'|'number'|'date'|'currency'|'boolean'|'select'
type WorkField = {key:string;label:string;type:FieldType;required:boolean}
type ExecutionMode = 'MANUAL'|'AI_ASSISTED'|'API'|'RPA'
type WorkNode = {id:string;label:string;kind:Kind;policy:Policy;enabled:boolean;role:string|null;when?:Condition|null;config:{position?:{x:number;y:number};instructions?:string;execution_mode?:ExecutionMode;fields?:WorkField[];source_step?:string;source_excerpt?:string;source_page?:number|null;source_confidence?:string;actor_side?:'CONTRATANTE'|'CONTRATISTA'|'REVISAR';party_scope_pending?:boolean}}
type WorkEdge = {source:string;target:string;when?:Condition|null}
type Workflow = {key: string; name: string; modality_key: string | null; nodes: WorkNode[]; edges: WorkEdge[]; metadata: Record<string, unknown>}

const current = ref<Screen>('resumen')
const studioTab=ref<'pantallas'|'editor'>('pantallas')
const previewSide=ref<'CONTRATANTE'|'CONTRATISTA'>('CONTRATANTE')
const previewPartyId=ref('')
const previewShareBusy=ref(false)
const previewShareMessage=ref('')
const previewShareError=ref('')

const providerPortalMode=ref(window.location.pathname.replace(/\/$/,'')==='/prestador' ||
 new URLSearchParams(window.location.search).get('view')==='mi-contratacion')
function openProviderPortal(){
 providerPortalMode.value=true;current.value='prestadores';activeCase.value=null
 window.history.pushState({},'','/prestador')
}
function closeProviderPortal(){
 if(!hasInstitution.value)return
 providerPortalMode.value=false;current.value='contrataciones';activeCase.value=null
 window.history.pushState({},'','/')
}
const mairaOpen = ref(false)
const mairaLastAction = ref('')
const menu: { key: Screen; title: string; glyph: string }[] = [
  { key:'resumen',title:'Resumen',glyph:'▦' },
  { key:'personas',title:'Personas y empresas',glyph:'♙' },
  { key:'contrataciones',title:'Gestión Contractual',glyph:'▤' },
  { key:'prestadores',title:'Portal de prestadores',glyph:'⌂' },
  { key:'flujos',title:'Flujos',glyph:'◇' },
  { key:'maira',title:'MAIRA',glyph:'✳' },
  { key:'configuracion',title:'Configuración',glyph:'⚙' }
]
const screenTitle = computed(() => menu.find(m => m.key === current.value)?.title ?? '')
const visibleMenu = computed(() => hasInstitution.value || portalSession.value?.can_setup ? menu : menu.filter(m=>m.key==='prestadores'))
const iconPaths: Record<Screen,string[]> = {
  resumen: ['M3 3h8v8H3z','M13 3h8v8h-8z','M3 13h8v8H3z','M13 13h8v8h-8z'],
  personas: ['M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2','M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8','M18 8a3 3 0 0 1 0 6','M22 21v-2a4 4 0 0 0-3-3.87'],
  contrataciones: ['M8 3h9l4 4v14H8z','M17 3v5h5','M11 12h7','M11 16h7','M4 7v14'],
  prestadores: ['M3 21V9l9-6 9 6v12','M9 21v-8h6v8','M3 10h18'],
  flujos: ['M12 2 3 12l9 10 9-10z','M12 8v8','M8 12h8'],
  maira: ['M12 2v3','M12 19v3','M2 12h3','M19 12h3','M5 5l2 2','M17 17l2 2','M19 5l-2 2','M7 17l-2 2','M12 7l2 5-2 5-2-5z'],
  configuracion: ['M12 3a3 3 0 0 1 3 3c0 1.2-.6 2-1.5 2.6A5 5 0 0 1 17 12a5 5 0 1 1-10 0 5 5 0 0 1 3.5-4.4C9.6 7 9 6.2 9 6a3 3 0 0 1 3-3z','M12 10v4','M12 17h.01']
}
const activeDependencyCount = computed(() => edges.value.length)
const catalogCount = computed(() => blocks.length)
const blocks: {kind:Kind; title:string; glyph:string; category:string}[] = [
  {kind:'FORM',title:'Formulario',glyph:'▤',category:'Captura'},
  {kind:'DOCUMENT_REQUEST',title:'Solicitar documentos',glyph:'▣',category:'Captura'},
  {kind:'DOCUMENT_REVIEW',title:'Revisar documentos',glyph:'▧',category:'Control'},
  {kind:'VALIDATION',title:'Validación',glyph:'✓',category:'Control'},
  {kind:'APPROVAL',title:'Aprobación',glyph:'◇',category:'Control'},
  {kind:'HUMAN_DECISION',title:'Decisión humana',glyph:'◆',category:'Control'},
  {kind:'NEGOTIATION',title:'Negociación',glyph:'⇄',category:'Contrato'},
  {kind:'CALCULATION',title:'Cálculo',glyph:'∑',category:'Contrato'},
  {kind:'DOCUMENT_GENERATION',title:'Generar documento',glyph:'▤',category:'Contrato'},
  {kind:'SIGNATURE',title:'Firma',glyph:'✎',category:'Contrato'},
  {kind:'NOTIFICATION',title:'Notificación',glyph:'◉',category:'Automatización'},
  {kind:'INTEGRATION',title:'Integración',glyph:'↗',category:'Automatización'},
  {kind:'TIMER',title:'Plazo / espera',glyph:'◷',category:'Automatización'},
  {kind:'JOIN',title:'Unir ramas',glyph:'⋈',category:'Automatización'}
]
const categories = ['Captura','Control','Contrato','Automatización']
const policies: {value:Policy; label:string}[] = [
  {value:'OPTIONAL',label:'Opcional'},
  {value:'CONDITIONAL',label:'Condicional'},
  {value:'ORG_REQUIRED',label:'Obligatoria institucional'},
  {value:'LEGAL_LOCKED',label:'Obligatoria legal'}
]
const roles = ['RED','JURIDICO','FINANCIERO','TECNICO','ACTUARIAL','APROBADOR','OPERADOR','SUPERVISOR']
const conditionOperators = [{value:'eq',label:'Igual a'},{value:'neq',label:'Distinto de'},{value:'gt',label:'Mayor que'},{value:'gte',label:'Mayor o igual'},{value:'lt',label:'Menor que'},{value:'lte',label:'Menor o igual'},{value:'in',label:'Está en la lista'},{value:'exists',label:'Existe'}]
const fieldTypes:FieldType[] = ['text','number','date','currency','boolean','select']
const executionModes: {value:ExecutionMode;label:string}[] = [{value:'MANUAL',label:'Manual'},{value:'AI_ASSISTED',label:'Asistida por MAIRA (futura)'},{value:'API',label:'API (requiere conector)'},{value:'RPA',label:'RPA (requiere conector)'}]
const LOCAL_DRAFT_KEY = 'smart-contract:workflow-studio:v5.2:local-only'
const ARCHIVED_PILOT_DRAFT_KEY = 'smart-contract:workflow-studio:archive:two-portal-example:v6.6.3'
const archivedPilotDraft=ref<Partial<Workflow>|null>(null)
const selectedId = ref<string | null>(null)
const selectedEdgeId = ref<string | null>(null)
const lastSavedAt = ref('')
const simulationVisible = ref(false)
const simulationFacts = ref('{}')
const simulationCompleted = ref('')
const simulationStatuses = ref<Record<string,string>>({})
const simulationError = ref('')
const nodeCounter = ref(1)
const workflowName = ref('Contratación de red prestadora')
const workflowKey = ref('RED_PRESTADORA_BASE')
const workflowMetadata=ref<Record<string,unknown>>({source:'smart-contract-workflow-studio',draft:true})
const reviewRolesConfirmed=ref(false)
const reviewRoutesConfirmed=ref(false)
const reviewedSignature=ref('')
function sourceReviewSignature(){
 return JSON.stringify({key:workflowKey.value,name:workflowName.value,modality:modalityKey.value,
   nodes:nodes.value.map(n=>({id:n.id,data:n.data,position:n.position})),
   edges:edges.value.map(e=>({source:e.source,target:e.target,data:e.data}))})
}
const sourceReviewRequired=computed(()=>workflowMetadata.value.source==='maira-document-import' ||
 nodes.value.some(n=>Boolean((n.data as WorkNode).config?.source_step)))
const sourceReviewConfirmed=computed(()=>sourceReviewRequired.value&&reviewRolesConfirmed.value&&reviewRoutesConfirmed.value&&
 reviewedSignature.value.length>0&&reviewedSignature.value===sourceReviewSignature())
function resetSourceReview(){reviewRolesConfirmed.value=false;reviewRoutesConfirmed.value=false;reviewedSignature.value=''}
function confirmSourceReview(){
 if(sourceReviewRequired.value&&studioMairaDialogue.value?.completed!==true){flowMessage.value='Debes responder las preguntas de MAIRA antes de confirmar la revisión.';return}
 if(!reviewRolesConfirmed.value||!reviewRoutesConfirmed.value){flowMessage.value='Debes confirmar la revisión de responsables y conexiones.';return}
 if(!validateDraft()){flowMessage.value='Corrige las observaciones del flujo antes de confirmar.';return}
 reviewedSignature.value=sourceReviewSignature()
 flowMessage.value='Revisión documental confirmada para esta versión del borrador. Cualquier cambio requiere una nueva verificación.'
}
const modalityKey = ref('')
const flowMessage = ref('')
const errors = ref<string[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const showCatalog = ref(true)

type MairaStatus={ready:boolean;google_enabled:boolean;gemini_enabled:boolean;google_client_id:string|null;max_mb:number;extensions:string[]}
type MairaMapping={source_step:string;source_excerpt:string;node_id:string;page:number|null;confidence:string}
type MairaProposal={workflow:Workflow;source_map:MairaMapping[];questions:string[];observations:string[];node_count:number;mapped_steps:number;notice:string;analysis_method?:string}
type PartyProcessPreview = {id:string;party_id:string;filename:string;status:string;workflow:Workflow;source_map:MairaMapping[];questions:string[];observations:string[];created_at:string}
type PreviewStage={id:string;step:string;label:string;role:string;kind:string;side:'CONTRATISTA'|'CONTRATANTE'|'REVISAR';source:string;page:number|null;confidence:string;dependencies:string[]}
function previewStages(proposal:{workflow:Workflow;source_map:MairaMapping[]},partyKind?:'NATURAL'|'JURIDICA'):PreviewStage[]{
 const nodes=new Map(proposal.workflow.nodes.map(n=>[n.id,n]))
 const steps=new Map(proposal.source_map.map(m=>[m.node_id,m.source_step]))
 return proposal.source_map.map(m=>{
  const n=nodes.get(m.node_id)
  const role=(n?.role||'Por definir').toUpperCase()
  const side=(partyKind==='JURIDICA'&&role==='ASPIRANTE')||n?.config?.actor_side==='REVISAR'?'REVISAR':
    n?.config?.actor_side==='CONTRATISTA'?'CONTRATISTA':
    n?.config?.actor_side==='CONTRATANTE'?'CONTRATANTE':
    ['ASPIRANTE','CONTRATISTA','PRESTADOR','PROVEEDOR'].includes(role)?'CONTRATISTA':
    ['JURIDICO','JURÍDICO','SISTEMA','SUPERVISOR','FINANCIERO','SST','ADMINISTRADOR'].includes(role)?'CONTRATANTE':'REVISAR'
  const dependencies=proposal.workflow.edges.filter(e=>e.target===m.node_id)
    .map(e=>steps.get(e.source)||'Inicio')
  return {id:m.node_id,step:m.source_step,label:n?.label||m.source_excerpt,
    kind:n?.kind||'VALIDATION',role,side,source:m.source_excerpt,
    page:m.page,confidence:m.confidence,dependencies}
 })
}
function numericStepOrder(x:PreviewStage,y:PreviewStage){
 const split=(s:string)=>s.split('.').map(v=>Number(v)||0)
 const a=split(x.step),b=split(y.step)
 for(let i=0;i<Math.max(a.length,b.length);i++){
   if((a[i]||0)!==(b[i]||0))return(a[i]||0)-(b[i]||0)
 }
 return 0
}
const MAIRA_API=import.meta.env.VITE_SMART_API_URL||'https://api-development-18b59fbb.up.railway.app'
const mairaImportOpen=ref(false)
const mairaImportStatus=ref<MairaStatus|null>(null)
const mairaImportBusy=ref(false)
type MairaStreamEvent={event:'progress'|'heartbeat'|'done'|'error';phase?:string;label?:string;message?:string;result?:MairaProposal}
type MairaProgressLine={phase:string;label:string}
const mairaLivePhase=ref('')
const mairaLiveLabel=ref('')
const mairaLiveHistory=ref<MairaProgressLine[]>([])
const mairaSeconds=ref(0)
let mairaTimer:ReturnType<typeof setInterval>|null=null
const mairaStages=computed(()=>mairaSourceOnly.value?
 ['Documento validado','Texto identificado','Borrador documental organizado','Vista previa disponible']:
 ['Documento validado','Lectura de Gemini completada','Workflow construido','Vista previa disponible'])
const mairaConfirmed=computed(()=>{
 if(mairaLivePhase.value==='TERMINADO')return 4
 if(mairaLiveHistory.value.some(x=>x.phase==='FINALIZANDO'))return 3
 if(mairaLiveHistory.value.some(x=>x.phase==='COMPILACION'))return 2
 if(mairaLiveHistory.value.some(x=>x.phase==='VALIDADO'))return 1
 return 0
})
const mairaRingLength=2*Math.PI*49
const mairaRingOffset=computed(()=>mairaRingLength*(1-mairaConfirmed.value/4))
function mairaClockDisplay(s:number){return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0')}
function mairaProgress(phase:string,label:string){
 if(mairaLivePhase.value===phase&&mairaLiveLabel.value===label)return
 mairaLivePhase.value=phase;mairaLiveLabel.value=label
 mairaLiveHistory.value=[...mairaLiveHistory.value,{phase,label}].slice(-12)
}
function startMairaClock(){
 if(mairaTimer!==null)clearInterval(mairaTimer)
 const start=Date.now();mairaSeconds.value=0
 mairaTimer=setInterval(()=>{mairaSeconds.value=Math.floor((Date.now()-start)/1000)},1000)
}
function stopMairaClock(){if(mairaTimer!==null){clearInterval(mairaTimer);mairaTimer=null}}

const mairaConnectionBusy=ref(false)
const mairaConnectionResult=ref('')
const mairaModelChoice=ref('')
const mairaSourceOnly=ref(false)
const mairaImportError=ref('')
const mairaImportInfo=ref('')
const mairaSourceFile=ref<File|null>(null)
const mairaProposal=ref<MairaProposal|null>(null)
const mairaTargetPartyId=ref('')
const mairaTargetParty=computed(()=>partyRecords.value.find(x=>x.id===mairaTargetPartyId.value)||null)
const mairaPreviewStages=computed(()=>mairaProposal.value?previewStages(mairaProposal.value,mairaTargetParty.value?.kind).sort(numericStepOrder):[])
const sourceOnlyPreview=computed(()=>mairaProposal.value?.workflow.metadata?.source_method==='PDF_TEXT_ONLY')

// MAIRA: ask about intended process before treating a generated graph as final.
type MairaIntent='KEEP_ORIGINAL'|'ADAPT_TO_ENTITY'|''
type MairaDialogue={scope_decision:MairaIntent;scope_question?:string;completed:boolean;questions_total:number;answers:{question:string;answer:string}[]}
const mairaIntent=ref<MairaIntent>('')
const mairaQuestionCursor=ref(0)
const mairaAnswerText=ref('')
const mairaAnswers=ref<Record<string,string>>({})
const mairaQuestionError=ref('')
const mairaScopeMismatch=computed(()=>mairaTargetParty.value?.kind==='JURIDICA'&&Boolean(
 mairaProposal.value?.source_map.some(x=>/aspirante|personal a contratar|arl/i.test(x.source_excerpt))))
const mairaScopePrompt=computed(()=>mairaScopeMismatch.value?
 'Este diagrama describe la contratación de aspirantes, pero el destinatario es '+(mairaTargetParty.value?.name||'una persona jurídica')+
 '. ¿Quieres conservar el proceso original o adaptarlo a la contratación de una IPS?':
 '¿Deseas conservar el proceso original del documento o adaptarlo a la entidad seleccionada?')
/** A Gemini observation about the same scope mismatch is evidence for the scope
 * question, not a second decision. Never delete the provider's original text. */
function sameDocumentScopeConcern(note:string,scope:string):boolean{
 const normalized=(text:string)=>text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase()
 const n=normalized(note),s=normalized(scope)
 return /aspirant|personal a contratar/.test(n)&&/persona juridica|destinatario|institucion/.test(n)&&
        /aspirant|personal a contratar/.test(s)
}
const mairaScopeEvidence=computed(()=>mairaProposal.value?.questions.filter(q=>
 sameDocumentScopeConcern(q,mairaScopePrompt.value))||[])
const mairaQuestions=computed(()=>{
 if(!mairaProposal.value)return [] as string[]
 const independent=mairaProposal.value.questions.filter(q=>!sameDocumentScopeConcern(q,mairaScopePrompt.value))
 return [mairaScopePrompt.value,
 ...(mairaIntent.value==='ADAPT_TO_ENTITY'?['¿Qué reglas, documentos y responsables necesitarían cambiar para esta entidad? Indica qué información falta por definir.']:[]),
 ...independent]
})
const mairaTotalQuestions=computed(()=>mairaQuestions.value.length)
const mairaAnsweredQuestions=computed(()=>mairaQuestions.value.filter((q,i)=>i===0?Boolean(mairaIntent.value):Boolean(mairaAnswers.value[q]?.trim())).length)
const mairaQuestionsDone=computed(()=>Boolean(mairaProposal.value&&mairaIntent.value&&mairaAnsweredQuestions.value===mairaTotalQuestions.value))
const mairaCurrentQuestion=computed(()=>mairaQuestions.value[mairaQuestionCursor.value]||'')
function resetMairaQuestions(){mairaIntent.value='';mairaQuestionCursor.value=0;mairaAnswerText.value='';mairaAnswers.value={};mairaQuestionError.value=''}
function mairaBack(){if(mairaQuestionCursor.value<=0)return;mairaQuestionCursor.value--;mairaQuestionError.value='';
 mairaAnswerText.value=mairaAnswers.value[mairaCurrentQuestion.value]||''}
function mairaAnswer(){
 mairaQuestionError.value=''
 if(mairaQuestionCursor.value===0){
  if(!mairaIntent.value){mairaQuestionError.value='Elige cómo utilizar este documento.';return}
 }else{
  const answer=mairaAnswerText.value.trim()
  if(answer.length<4){mairaQuestionError.value='Escribe una respuesta o indica qué dato falta por definir.';return}
  mairaAnswers.value={...mairaAnswers.value,[mairaCurrentQuestion.value]:answer.slice(0,650)}
 }
 mairaQuestionCursor.value++
 mairaAnswerText.value=mairaAnswers.value[mairaCurrentQuestion.value]||''
}
function mairaDialogue():MairaDialogue{return {
 scope_decision:mairaIntent.value,scope_question:mairaScopePrompt.value,completed:mairaQuestionsDone.value,questions_total:mairaTotalQuestions.value,
 answers:mairaQuestions.value.slice(1).map(question=>({question:question.slice(0,700),
  answer:(mairaAnswers.value[question]||'').trim().slice(0,650)}))
}}
function workflowWithMairaDialogue(p:MairaProposal):Workflow{
 const wf=workflowWithEvidence(p,mairaTargetParty.value?.kind)
 return {...wf,metadata:{...wf.metadata,maira_dialogue:mairaDialogue()}}
}
const studioMairaDialogue=computed(()=>workflowMetadata.value.maira_dialogue as MairaDialogue|undefined)

const originalScopeChoice=ref<'KEEP_ORIGINAL'|'ADAPT_TO_ENTITY'|''>('')
const originalClarificationAnswers=ref<Record<string,string>>({})
const isOriginalFirstFlow=computed(()=>workflowMetadata.value.source==='smart-contract-original-pdf')
function saveOriginalFlowClarifications(){
 if(!isOriginalFirstFlow.value)return
 if(!originalScopeChoice.value){
  flowMessage.value='Define primero si conservarás o adaptarás el alcance del diagrama original.';return
 }
 const questions=studioReviewQuestions.value
 const answers=questions.map(question=>({question,answer:(originalClarificationAnswers.value[question]||'').trim()}))
 if(answers.some(item=>item.answer.length<4)){
  flowMessage.value='Responde todas las preguntas. Si el dato no está confirmado, indícalo explícitamente como pendiente.';return
 }
 const dialogue:MairaDialogue={scope_decision:originalScopeChoice.value,completed:true,
  questions_total:answers.length+1,answers}
 workflowMetadata.value={...workflowMetadata.value,maira_dialogue:dialogue,review_confirmed:false}
 resetSourceReview()
 flowMessage.value='Respuestas documentadas en el borrador local. No se cambiaron las tareas ni las condiciones. Revisa la estructura antes de publicar.'
}

const studioReviewQuestions=computed(()=>{
 const original=workflowMetadata.value.maira_review_questions
 const raw=Array.isArray(original)?original.filter((q):q is string=>typeof q==='string'&&q.trim().length>0):[]
 const scope=studioMairaDialogue.value?.scope_question||''
 const independent=raw.filter(q=>!sameDocumentScopeConcern(q,scope))
 return [...(scope.trim()?[scope]:[]),...independent]
})


/** The visual preview uses the actual MAIRA nodes, edges and source references. */
function workflowWithEvidence(proposal:{workflow:Workflow;source_map:MairaMapping[]},partyKind?:'NATURAL'|'JURIDICA'):Workflow{
 const byNode=new Map(proposal.source_map.map(m=>[m.node_id,m]))
 return {...proposal.workflow,
  metadata:{...proposal.workflow.metadata,source:'maira-document-import',draft:true,
    requires_review:true,review_confirmed:false,
    maira_review_questions:('questions' in proposal&&Array.isArray(proposal.questions))?
      proposal.questions:proposal.workflow.metadata?.maira_review_questions||[]},
  nodes:proposal.workflow.nodes.map(n=>{
   const ref=byNode.get(n.id)
   const applicant=partyKind==='JURIDICA'&&(n.role||'').trim().toUpperCase()==='ASPIRANTE'
   return {...n,config:{...n.config,
    ...(ref?{source_step:ref.source_step,source_excerpt:ref.source_excerpt,
             source_page:ref.page,source_confidence:ref.confidence}:{}),
    ...(applicant?{actor_side:'REVISAR' as const,party_scope_pending:true}:{})}}
  })}
}
function mairaGraphPosition(index:number,total:number){
 const cols=Math.min(5,Math.max(2,Math.ceil(Math.sqrt(total))))
 const row=Math.floor(index/cols)
 const col=row%2===0?index%cols:cols-1-index%cols
 return {x:col*295+28,y:row*165+24}
}

type MairaGraphicQuestion={text:string;step:string|null;node_ids:string[];steps:string[];context:string}
function normalizeReviewText(value:string):string{
 return value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\s+/g,' ').trim()
}
/** Attach only quoted source wording or literal acronyms that are present in
 * the original activity. This is a citation match, NOT a causal dependency. */
function literalReviewReferences(note:string):string[]{
 const quoted=[...note.matchAll(/['"“”‘’]([^'"“”‘’]{3,80})['"“”‘’]/g)].map(m=>m[1])
 const acronyms=[...note.matchAll(/\b[A-Z]{3,6}\b/g)].map(m=>m[0])
 return [...new Set([...quoted,...acronyms].map(normalizeReviewText).filter(x=>x.length>=3))]
}
function assignDiagramReviewQuestions(questions:string[],sources:MairaMapping[],
 scope:string,scopeEvidence:string[]):MairaGraphicQuestion[]{
 const byStep=new Map(sources.map(source=>[source.source_step,source.node_id]))
 return questions.filter(q=>typeof q==='string'&&q.trim()).map((text,index)=>{
  const isScope=index===0&&text===scope
  const evidence=isScope?scopeEvidence.join(' '):text
  const references=literalReviewReferences(evidence)
  const related=sources.filter(source=>references.some(term=>
    normalizeReviewText(source.source_excerpt).includes(term)))
  const match=text.match(/\b(?:paso|etapa|actividad)\s*(\d+(?:\.\d+)*)\b/i)
  const explicitlyNamed=match&&byStep.has(match[1])?match[1]:null
  const ids=[...new Set([...related.map(x=>x.node_id),
    ...(explicitlyNamed?[byStep.get(explicitlyNamed)!]:[])])]
  const steps=[...new Set([...related.map(x=>x.source_step),
    ...(explicitlyNamed?[explicitlyNamed]:[])])]
  return {text,step:explicitlyNamed,node_ids:ids,steps,context:isScope?scopeEvidence.join(' · '):''}
 })
}
const mairaGraphReviewQuestions=computed(()=>mairaProposal.value?
 assignDiagramReviewQuestions(mairaQuestions.value,mairaProposal.value.source_map,
  mairaScopePrompt.value,mairaScopeEvidence.value):[])
const mairaGraphReviewMarkers=computed(()=>
 new Set(mairaGraphReviewQuestions.value.flatMap(q=>q.node_ids)))
const mairaVerifiedBranchCount=computed(()=>{
 const p=mairaProposal.value
 if(!p)return 0
 return p.workflow.nodes.filter(n=>n.kind==='HUMAN_DECISION'&&
  p.workflow.edges.filter(e=>e.source===n.id).length>1).length
})

const mairaDiagram=computed(()=>{
 const p=mairaProposal.value
 if(!p)return {nodes:[] as Node[],edges:[] as Edge[]}
 const wf=workflowWithEvidence(p,mairaTargetParty.value?.kind)
 const indexes=new Map(p.source_map.map((m,i)=>[m.node_id,i]))
 const original=[...wf.nodes].sort((a,b)=>{
   if(a.kind==='START')return -1
   if(b.kind==='START')return 1
   if(a.kind==='END')return 1
   if(b.kind==='END')return -1
   return (indexes.get(a.id)??999)-(indexes.get(b.id)??999)
 })
 const count=original.length
 const columns=Math.min(5,Math.max(2,Math.ceil(Math.sqrt(count))))
 const citations=new Map(p.source_map.map(m=>[m.node_id,m]))
 const graphNodes:Node[]=original.map((n,i)=>{
  const col=i%columns,row=Math.floor(i/columns)
  const forward=row%2===0
  const last=col===columns-1||i===count-1
  const citation=citations.get(n.id)
  const fullLabel=(citation?citation.source_step+' · ':'')+n.label
  return {id:n.id,type:n.kind==='START'?'input':n.kind==='END'?'output':'default',
   position:mairaGraphPosition(i,count),
   sourcePosition:last?Position.Bottom:(forward?Position.Right:Position.Left),
   targetPosition:col===0?Position.Top:(forward?Position.Left:Position.Right),
   class:'maira-preview-node '+(n.kind==='START'?'preview-start':n.kind==='END'?'preview-end':'')+
    (mairaGraphReviewMarkers.value.has(n.id)?' preview-review-marked':'')+
    (n.kind==='HUMAN_DECISION'?' preview-decision-node':''),
   data:{label:(mairaGraphReviewMarkers.value.has(n.id)?'❓ ':'')+
      (fullLabel.length>84?fullLabel.slice(0,81)+'…':fullLabel),
    original_role:n.role,source_step:citation?.source_step}}
 })
 const ids=new Set(graphNodes.map(n=>n.id))
 const graphEdges:Edge[]=wf.edges.filter(e=>ids.has(e.source)&&ids.has(e.target))
  .map((e,i)=>({id:'maira_map_edge_'+i,source:e.source,target:e.target,type:'smoothstep',
  style:{stroke:'#84a5c5',strokeWidth:2},animated:false}))
 return {nodes:graphNodes,edges:graphEdges}
})
const mairaDiagramVersion=ref(0)
const studioDiagramVersion=ref(0)

const mairaPreviewSaving=ref(false)
const partyPreview=ref<PartyProcessPreview|null>(null)
const partyPreviewTarget=ref<PartyRecord|null>(null)
const partyPreviewBusy=ref(false)
const savedPreviewStages=computed(()=>partyPreview.value?previewStages(partyPreview.value,partyPreviewTarget.value?.kind).sort(numericStepOrder):[])
const savedSourceOnly=computed(()=>partyPreview.value?.workflow.metadata?.source_method==='PDF_TEXT_ONLY')

const mairaApplyConfirm=ref(false)
const loginGoogleMount=ref<HTMLElement|null>(null)
const loginEmail=ref('')
type PortalSession={email:string;institutions:{id:string;roles:string[]}[];invited_cases:number;can_setup:boolean;pilot:boolean;original_flow_preload_enabled?:boolean}
type CaseSummary={id:string;title:string;state:string;workflow_version_id:string|null;party_id:string|null;party_name:string|null;party_email?:string|null;invited:boolean;total:number;completed:number}
type PartyProcessIndex={id:string;name:string;status:string;kind:'PROPOSAL'|'PRESENTATION'|'DESIGN';activity_count:number;created_at:string;source?:string|null}
type PartyRecord={id:string;name:string;kind:'NATURAL'|'JURIDICA';email:string|null;case_count:number;process_count?:number;has_original_first_flow?:boolean;latest_process?:PartyProcessIndex|null}
type PartyPortfolio={party:PartyRecord;cases:CaseSummary[];processes:PartyProcessIndex[]}
type ContractTaskView={id:string;node_id:string;label:string;kind:string;side:string;state:string;fields:WorkField[];answer?:Record<string,unknown>;note?:string}
type CaseView={case:CaseSummary;side:'CONTRATANTE'|'CONTRATISTA';tasks:ContractTaskView[]}
type TemplateOption={id:string;name:string;key:string;version:number}
const portalSession=ref<PortalSession|null>(null)
const hasInstitution=computed(()=>Boolean(portalSession.value?.institutions?.length))
const templates=ref<TemplateOption[]>([])
const partyRecords=ref<PartyRecord[]>([])
const partySearch=ref('')
const partyName=ref('')
const partyEmail=ref('')
const partyKind=ref<'NATURAL'|'JURIDICA'>('JURIDICA')
const selectedPartyId=ref('')
const selectedParty=computed(()=>partyRecords.value.find(x=>x.id===selectedPartyId.value)||null)
const filteredParties=computed(()=>partyRecords.value.filter(p=>(p.name+' '+(p.email||'')).toLocaleLowerCase('es-CO').includes(partySearch.value.toLocaleLowerCase('es-CO'))))
const showNewPartyForm=ref(false)
const expandedPartyId=ref('')
const partyPortfolio=ref<PartyPortfolio|null>(null)
const partyPortfolioBusy=ref(false)
const editingLinkedDraft=ref<{partyId:string;draftId:string;partyName:string}|null>(null)
const draftSaving=ref(false)
const partyPresentationPreview=ref<SharedPresentationDetail|null>(null)
const partyPreviewSide=ref<'CONTRATANTE'|'CONTRATISTA'>('CONTRATANTE')
function processTypeLabel(p:PartyProcessIndex){
 return p.kind==='DESIGN'?'Borrador del diseñador':p.kind==='PRESENTATION'?'Vista compartida':'Propuesta de MAIRA'
}
function caseStateLabel(value:string){
 return ({DRAFT:'Borrador',IN_PROGRESS:'En curso',COMPLETED:'Finalizado',CANCELLED:'Cancelado'} as Record<string,string>)[value]||value
}
const editingPartyId=ref('')
const editingPartyEmail=ref('')
const draftWorkflowId=ref('')
const internalCases=ref<CaseSummary[]>([])

type SharedPresentation={id:string;name:string;status:string;created_at:string}
type SharedPresentationDetail=SharedPresentation&{workflow:Workflow}
const mySharedPresentations=ref<SharedPresentation[]>([])
const selectedSharedPresentation=ref<SharedPresentationDetail|null>(null)
async function openSharedPresentation(id:string){
 portalError.value='';selectedSharedPresentation.value=null
 try{
  selectedSharedPresentation.value=await portalRequest<SharedPresentationDetail>('/my-workflow-presentations/'+id)
  activeCase.value=null
 }catch(e){portalError.value=e instanceof Error?e.message:'No se pudo abrir la vista previa'}
}
async function shareWorkflowPreview(){
 const party=partyRecords.value.find(p=>p.id===previewPartyId.value)
 previewShareError.value='';previewShareMessage.value=''
 if(!party?.email){
  previewShareError.value='Selecciona una persona jurídica registrada con correo de contacto autorizado.'
  return
 }
 previewShareBusy.value=true
 try{
  const result=await portalRequest<{id:string;recipient:string;case_created:boolean}>(
   '/parties/'+party.id+'/workflow-presentations','POST',{workflow:definition()})
  previewShareMessage.value='Vista previa compartida para '+result.recipient+
   '. Al iniciar sesión en Portal de Prestadores verá las pantallas del proceso. No se creó un expediente.'
 }catch(e){previewShareError.value=e instanceof Error?e.message:'No se pudo compartir la vista previa'}
 finally{previewShareBusy.value=false}
}

const myCases=ref<CaseSummary[]>([])
const activeCase=ref<CaseView|null>(null)
const portalError=ref('')
const portalMessage=ref('')
const portalBusy=ref(false)
const portalPartySaving=ref(false)
const pilotName=ref('Institución de pruebas')
const newCaseTitle=ref('')
const selectedWorkflowId=ref('')
const answers=ref<Record<string,string>>({})
const taskNote=ref('')
const returnReason=ref('')

async function togglePartyRecord(party:PartyRecord,force=false){
 if(!force&&expandedPartyId.value===party.id){
   expandedPartyId.value='';partyPortfolio.value=null
   partyPreview.value=null;partyPresentationPreview.value=null
   return
 }
 expandedPartyId.value=party.id;partyPortfolioBusy.value=true
 partyPortfolio.value=null;partyPreview.value=null;partyPreviewTarget.value=null
 partyPresentationPreview.value=null;portalError.value=''
 try{
   partyPortfolio.value=await portalRequest<PartyPortfolio>('/parties/'+party.id+'/portfolio')
 }catch(e){portalError.value=e instanceof Error?e.message:'No se pudo abrir la ficha del registro'}
 finally{partyPortfolioBusy.value=false}
}
async function openPartyExistingProcess(party:PartyRecord,item:PartyProcessIndex){
 portalError.value='';partyPresentationPreview.value=null
 if(item.kind==='PROPOSAL'){
   await viewPartyProcessPreview(party,item.id)
   return
 }
 try{
   if(item.kind==='PRESENTATION'){
     partyPresentationPreview.value=await portalRequest<SharedPresentationDetail>(
       '/parties/'+party.id+'/workflow-presentations/'+item.id)
     partyPreview.value=null;partyPreviewTarget.value=null
     return
   }
   const record=await portalRequest<{workflow:Workflow}>(
     '/parties/'+party.id+'/workflow-drafts/'+item.id)
   loadDefinition(record.workflow)
   studioCanvasMode.value='guided'
   guidedPage.value=0
   editingLinkedDraft.value={partyId:party.id,draftId:item.id,partyName:party.name}
   studioTab.value='editor';current.value='flujos'
   flowMessage.value='Diagrama de '+party.name+' abierto para edición. Usa «Guardar cambios» para conservar tu trabajo.'
 }catch(e){portalError.value=e instanceof Error?e.message:'No se pudo abrir el proceso guardado'}
}
async function saveCurrentWorkflowForParty(party:PartyRecord){
 portalPartySaving.value=true;portalError.value='';portalMessage.value=''
 try{
  const linked=editingLinkedDraft.value?.partyId===party.id?editingLinkedDraft.value:null
  const saved=await portalRequest<{id:string;name:string}>(
    '/parties/'+party.id+'/workflow-drafts'+(linked?'/'+linked.draftId:''),
    linked?'PATCH':'POST',{workflow:definition()})
  editingLinkedDraft.value={partyId:party.id,draftId:saved.id,partyName:party.name}
  await refreshPortal()
  await togglePartyRecord(party,true)
  portalMessage.value='«'+saved.name+'» está guardado en '+party.name+' como borrador editable. No se creó un contrato.'
 }catch(e){portalError.value=e instanceof Error?e.message:'No se pudo guardar el flujo en este registro'}
 finally{portalPartySaving.value=false}
}
async function openPartyExistingCase(id:string){
 await openCase(id)
 if(activeCase.value?.case.id===id){
   current.value='contrataciones'
   portalMessage.value='Expediente «'+activeCase.value.case.title+'» abierto desde Personas y empresas.'
 }
}


async function saveLinkedWorkflowDraft(){
 const linked=editingLinkedDraft.value
 if(!linked)return
 draftSaving.value=true
 try{
  const result=await portalRequest<{id:string;name:string}>(
    '/parties/'+linked.partyId+'/workflow-drafts/'+linked.draftId,
    'PATCH',{workflow:definition()})
  flowMessage.value='Cambios guardados en '+linked.partyName+': '+result.name+
    '. El proceso sigue en borrador; no se ha activado ningún contrato.'
  await refreshPortal()
 }catch(e){flowMessage.value='No se pudieron guardar los cambios: '+(e instanceof Error?e.message:'error de conexión')}
 finally{draftSaving.value=false}
}

async function preloadFirstOriginalWorkflow(){
 if(!portalSession.value?.original_flow_preload_enabled)return
 const hospital=partyRecords.value.find(p=>p.name.trim().toLocaleLowerCase('es-CO')==='hospital smart')
 if(!hospital||hospital.has_original_first_flow)return
 // The exact source definition is used, not a potentially changed local draft.
 const workflow=buildOriginalContractFlow()
 const result=await portalRequest<{id:string;already_exists:boolean}>(
   '/parties/'+hospital.id+'/workflow-drafts','POST',
   {workflow,initialize_original:true})
 partyRecords.value=await portalRequest<PartyRecord[]>('/parties')
 if(expandedPartyId.value===hospital.id){
  partyPortfolio.value=await portalRequest<PartyPortfolio>('/parties/'+hospital.id+'/portfolio')
 }
 if(!result.already_exists){
  portalMessage.value='El diagrama original de 23 actividades quedó precargado en Hospital Smart como borrador editable.'
 }
}

async function portalRequest<T>(path:string,method='GET',payload?:unknown):Promise<T>{
 const response=await fetch(MAIRA_API+'/api/v1/portal'+path,{
  method,headers:{Authorization:'Bearer '+loginToken.value,...(payload!==undefined?{'Content-Type':'application/json'}:{})},
  ...(payload!==undefined?{body:JSON.stringify(payload)}:{}),cache:'no-store'
 })
 let data:unknown
 try{data=await response.json()}catch{data={}}
 if(!response.ok){
  const message=(data as {detail?:unknown}).detail
  throw new Error(typeof message==='string'?message:JSON.stringify(message||'Error del servidor ('+response.status+')'))
 }
 return data as T
}
async function refreshPortal(){
 if(!loginToken.value)return
 portalError.value=''
 try{
  portalSession.value=await portalRequest<PortalSession>('/session')
  myCases.value=await portalRequest<CaseSummary[]>('/my-cases')
  mySharedPresentations.value=await portalRequest<SharedPresentation[]>('/my-workflow-presentations')
  if(hasInstitution.value){
   templates.value=await portalRequest<TemplateOption[]>('/workflows')
   partyRecords.value=await portalRequest<PartyRecord[]>('/parties')
   await preloadFirstOriginalWorkflow()
   internalCases.value=await portalRequest<CaseSummary[]>('/cases')
  }else{templates.value=[];partyRecords.value=[];internalCases.value=[]}
 }catch(e){portalError.value=e instanceof Error?e.message:'No se pudo consultar la plataforma'}
}
async function setupPilot(){
 portalBusy.value=true;portalError.value=''
 try{
  await portalRequest('/demo/setup','POST',{name:pilotName.value})
  await refreshPortal()
  portalMessage.value='Espacio de prueba creado. Solo utiliza información sintética.'
 }catch(e){portalError.value=e instanceof Error?e.message:'No se pudo crear el espacio'}
 finally{portalBusy.value=false}
}
async function publishPilot(){
 if(sourceReviewRequired.value&&studioMairaDialogue.value?.completed!==true){portalError.value='Faltan las respuestas de MAIRA para completar el proceso.';return}
 if(sourceReviewRequired.value&&!sourceReviewConfirmed.value){
  portalError.value='Antes de publicar debes verificar roles, pertinencia y dependencias del documento en Workflow Studio.'
  return
 }
 portalBusy.value=true;portalError.value='';portalMessage.value=''
 try{
  const result=await portalRequest<{id:string;version:number}>('/workflows/publish','POST',{workflow:definition()})
  await refreshPortal()
  selectedWorkflowId.value=result.id
  portalMessage.value='Plantilla de prueba publicada, versión '+result.version+'. No es una aprobación jurídica.'
 }catch(e){portalError.value=e instanceof Error?e.message:'No se pudo publicar'}
 finally{portalBusy.value=false}
}
async function registerParty(){
 portalPartySaving.value=true;portalError.value='';portalMessage.value=''
 try{
  const record=await portalRequest<PartyRecord>('/parties','POST',{
    name:partyName.value.trim(),kind:partyKind.value,email:partyEmail.value.trim()||null
  })
  partyName.value='';partyEmail.value=''
  await refreshPortal()
  selectedPartyId.value=record.id
  portalMessage.value='Persona o empresa registrada. Ahora puedes vincularla a un expediente, con o sin plantilla.'
 }catch(e){portalError.value=e instanceof Error?e.message:'No se pudo registrar'}
 finally{portalPartySaving.value=false}
}
async function savePartyEmail(id:string){
 portalPartySaving.value=true;portalError.value='';portalMessage.value=''
 try{
  await portalRequest('/parties/'+id,'PATCH',{email:editingPartyEmail.value.trim()||null})
  editingPartyId.value='';editingPartyEmail.value=''
  await refreshPortal()
  portalMessage.value='Contacto actualizado. No modifica automáticamente los accesos concedidos a expedientes anteriores.'
 }catch(e){portalError.value=e instanceof Error?e.message:'No se pudo actualizar el contacto'}
 finally{portalPartySaving.value=false}
}
function selectPartyForContract(p:PartyRecord){
 selectedPartyId.value=p.id
 newCaseTitle.value='Contratación con '+p.name
 selectedWorkflowId.value=''
 current.value='contrataciones'
 activeCase.value=null
 portalMessage.value='Seleccionaste '+p.name+'. Puedes abrir el expediente sin plantilla.'
 portalError.value=''
}
async function attachWorkflowToCase(){
 if(!activeCase.value?.case.id||!draftWorkflowId.value)return
 portalBusy.value=true;portalError.value='';portalMessage.value=''
 try{
  const id=activeCase.value.case.id
  await portalRequest('/cases/'+id+'/workflow','POST',{workflow_id:draftWorkflowId.value})
  portalMessage.value='Plantilla asociada y proceso activado. El correo registrado puede acceder a Mi Contratación; comparte el enlace manualmente.'
  await refreshPortal()
  await openCase(id)
 }catch(e){portalError.value=e instanceof Error?e.message:'No se pudo asociar la plantilla'}
 finally{portalBusy.value=false}
}
async function createPilotCase(){
 portalBusy.value=true;portalError.value=''
 try{
  const result=await portalRequest<CaseSummary>('/cases','POST',{
   title:newCaseTitle.value,party_id:selectedPartyId.value,
   ...(selectedWorkflowId.value?{workflow_id:selectedWorkflowId.value}:{})
  })
  portalMessage.value=result.invited
    ?'Expediente creado y plantilla activada. Comparte el enlace con el correo registrado; no se envía email automáticamente.'
    :'Expediente creado como borrador sin plantilla. Puedes asociar una existente o diseñar una nueva cuando quieras.'
  await refreshPortal()
  await openCase(result.id)
 }catch(e){portalError.value=e instanceof Error?e.message:'No se pudo crear el expediente'}
 finally{portalBusy.value=false}
}
async function openCase(id:string){
 portalError.value='';answers.value={};taskNote.value='';returnReason.value=''
 try{activeCase.value=await portalRequest<CaseView>('/cases/'+id);draftWorkflowId.value='' }
 catch(e){portalError.value=e instanceof Error?e.message:'No se pudo abrir el expediente'}
}
async function completeProviderPortalTask(payload:{taskId:string;data:Record<string,unknown>;note:string}){
 const opened=activeCase.value
 if(!opened||opened.side!=='CONTRATISTA'){portalError.value='La cuenta no está autorizada como contratista en este expediente.';return}
 const task=opened.tasks.find(t=>t.id===payload.taskId)
 if(!task||task.side!=='CONTRATISTA'||!['PENDING','RETURNED'].includes(task.state)){
  portalError.value='La actividad no está disponible para esta cuenta.';return
 }
 portalBusy.value=true;portalError.value='';portalMessage.value=''
 try{
  await portalRequest('/cases/'+opened.case.id+'/tasks/'+task.id+'/complete','POST',{
   data:payload.data,note:payload.note
  })
  portalMessage.value='Actividad registrada con trazabilidad.'
  await refreshPortal();await openCase(opened.case.id)
 }catch(e){portalError.value=e instanceof Error?e.message:'No se pudo registrar la actividad'}
 finally{portalBusy.value=false}
}
async function completePortalTask(task:ContractTaskView){
 if(!activeCase.value)return
 portalBusy.value=true;portalError.value=''
 const fields=task.fields||[]
 const data:Record<string,unknown>={}
 for(const field of fields){const v=answers.value[field.key];if(v!==undefined&&v!=='')data[field.key]=field.type==='number'||field.type==='currency'?Number(v):field.type==='boolean'?v==='true':v}
 try{
  await portalRequest('/cases/'+activeCase.value.case.id+'/tasks/'+task.id+'/complete','POST',{data,note:taskNote.value})
  portalMessage.value='Actividad registrada con trazabilidad.'
  await refreshPortal();await openCase(activeCase.value.case.id)
 }catch(e){portalError.value=e instanceof Error?e.message:'No se pudo completar'}
 finally{portalBusy.value=false}
}
async function returnPortalTask(task:ContractTaskView){
 if(!activeCase.value)return
 portalBusy.value=true;portalError.value=''
 try{
  await portalRequest('/cases/'+activeCase.value.case.id+'/tasks/'+task.id+'/return','POST',{reason:returnReason.value})
  portalMessage.value='Actividad devuelta al contratista para corrección.'
  await refreshPortal();await openCase(activeCase.value.case.id)
 }catch(e){portalError.value=e instanceof Error?e.message:'No se pudo devolver'}
 finally{portalBusy.value=false}
}
function inviteLink(){
 const url=window.location.origin+'/prestador'
 if(!navigator.clipboard){portalMessage.value='Comparte esta dirección con el usuario invitado: '+url;return}
 void navigator.clipboard.writeText(url).then(()=>{portalMessage.value='Enlace copiado. El invitado debe usar el correo registrado en Google Testing.'}).catch(()=>{portalMessage.value='Comparte esta dirección con el invitado: '+url})
}

const loginToken=ref('')
const loginPending=ref(false)
const loginError=ref('')
const loginChecking=ref(true)
const mairaGoogleToken=ref('')
let mairaGoogleScript:Promise<void>|null=null
type GoogleIdentity={
  initialize:(args:{client_id:string;callback:(data:{credential:string})=>void})=>void;
  renderButton:(root:HTMLElement,options:{type:string;theme:string;size:string;text:string})=>void;
  disableAutoSelect?:()=>void
}
async function acceptGoogleCredential(credential:string){
 loginPending.value=true;loginError.value=''
 try{
  const result=await fetch(MAIRA_API+'/api/v1/portal/session',{headers:{Authorization:'Bearer '+credential},cache:'no-store'})
  const payload=await result.json() as PortalSession & {detail?:string}
  if(!result.ok)throw new Error(typeof payload.detail==='string'?payload.detail:'La cuenta no está habilitada para Smart Contract.')
  if(!payload.email)throw new Error('Google no devolvió una cuenta verificada.')
  loginToken.value=credential
  mairaGoogleToken.value=credential
  loginEmail.value=payload.email
  portalSession.value=payload
  await refreshPortal()
  if(providerPortalMode.value||(!hasInstitution.value&&!payload.can_setup)){
   providerPortalMode.value=true;current.value='prestadores'
  }else if(!hasInstitution.value)current.value='contrataciones'
 }catch(e){
  loginToken.value='';mairaGoogleToken.value='';loginEmail.value=''
  loginError.value=e instanceof Error?e.message:'No se pudo validar la sesión'
 }finally{loginPending.value=false}
}
function logoutGoogle(){
 loginToken.value='';mairaGoogleToken.value='';loginEmail.value='';mairaImportOpen.value=false
 portalSession.value=null;templates.value=[];partyRecords.value=[];selectedPartyId.value='';internalCases.value=[];myCases.value=[];activeCase.value=null;current.value='resumen'
 googleIdentity()?.disableAutoSelect?.()
 void nextTick(()=>{void initializeLoginGoogle()})
}
async function initializeLoginGoogle(){
 await nextTick()
 if(!loginGoogleMount.value||!mairaImportStatus.value?.google_enabled)return
 try{
  await loadGoogleIdentity()
  const google=googleIdentity()
  const client_id=mairaImportStatus.value.google_client_id
  if(!google||!client_id)throw new Error('Google no está disponible')
  google.initialize({client_id,callback:({credential})=>{void acceptGoogleCredential(credential)}})
  loginGoogleMount.value.replaceChildren()
  google.renderButton(loginGoogleMount.value,{type:'standard',theme:'outline',size:'large',text:'signin_with'})
 }catch(e){loginError.value=e instanceof Error?e.message:'No se pudo abrir Google'}
}
onMounted(async()=>{
 await loadMairaImportStatus()
 loginChecking.value=false
 await initializeLoginGoogle()
})
function googleIdentity():GoogleIdentity|null{
  return (window as unknown as {google?:{accounts?:{id?:GoogleIdentity}}}).google?.accounts?.id||null
}
function loadGoogleIdentity():Promise<void>{
 if(googleIdentity())return Promise.resolve()
 if(mairaGoogleScript)return mairaGoogleScript
 mairaGoogleScript=new Promise<void>((resolve,reject)=>{
  const script=document.createElement('script')
  script.src='https://accounts.google.com/gsi/client';script.async=true;script.defer=true
  script.onload=()=>googleIdentity()?resolve():reject(new Error('No se pudo iniciar Google Sign-In'))
  script.onerror=()=>reject(new Error('No se pudo cargar Google Sign-In'))
  document.head.appendChild(script)
 }).catch(e=>{mairaGoogleScript=null;throw e})
 return mairaGoogleScript
}
async function loadMairaImportStatus(){
 try{
  const resp=await fetch(MAIRA_API+'/api/v1/maira/workflow-import/status',{cache:'no-store'})
  if(!resp.ok)throw new Error('La API MAIRA no está disponible')
  mairaImportStatus.value=await resp.json() as MairaStatus
 }catch(e){mairaImportStatus.value=null;mairaImportError.value=e instanceof Error?e.message:'No se pudo consultar MAIRA'}
}
async function openMairaDocumentImport(partyId?:string){
 mairaTargetPartyId.value=partyId||''
 current.value='flujos';mairaOpen.value=false;mairaImportOpen.value=true
 mairaImportError.value='';mairaImportInfo.value='';mairaProposal.value=null;mairaApplyConfirm.value=false
 resetMairaQuestions()
 mairaLivePhase.value='';mairaLiveLabel.value='';mairaLiveHistory.value=[];mairaSeconds.value=0;mairaSourceOnly.value=false
 await loadMairaImportStatus()
}
function chooseMairaSource(event:Event){
 const target=event.target as HTMLInputElement, file=target.files?.[0]||null
 mairaImportError.value='';mairaProposal.value=null;mairaApplyConfirm.value=false
 resetMairaQuestions()
 mairaLivePhase.value='';mairaLiveLabel.value='';mairaLiveHistory.value=[];mairaSourceOnly.value=false
 if(file&&(file.size>6*1024*1024||!/\.(pdf|png|jpe?g|txt)$/i.test(file.name))){
  mairaImportError.value='Formatos PDF, imagen o TXT, hasta 6 MB.';mairaSourceFile.value=null
 }else mairaSourceFile.value=file
}
async function checkMairaConnection(){
 if(!mairaGoogleToken.value){mairaImportError.value='Debes iniciar sesión con Google para diagnosticar Gemini.';return}
 if(mairaImportBusy.value)return
 mairaConnectionBusy.value=true
 mairaConnectionResult.value=''
 mairaImportError.value=''
 mairaModelChoice.value=''
 try{
  const response=await fetch(MAIRA_API+'/api/v1/maira/workflow-import/diagnose-models',{
   method:'POST',headers:{Authorization:'Bearer '+mairaGoogleToken.value},cache:'no-store'
  })
  const body=await response.json() as {
   configured_model?:string;recommended_model?:string|null;verified?:boolean;detail?:string;
   results?:{model:string;state:string;http:number|null}[]
  }
  if(!response.ok)throw new Error(body.detail||'No fue posible diagnosticar los modelos ('+response.status+').')
  const states=(body.results||[]).map(x=>x.model+': '+(x.state==='OK'?'respondió correctamente':x.http?'HTTP '+x.http:x.state)).join(' · ')
  if(!body.verified||!body.recommended_model){
   throw new Error('Ningún modelo respondió a la prueba mínima. '+states+'. Evita volver a procesar el PDF hasta restablecer Gemini.')
  }
  if(body.recommended_model!==body.configured_model){
   mairaModelChoice.value=body.recommended_model
   mairaConnectionResult.value='Modelo alternativo verificado: '+body.recommended_model+'. Se usará en este análisis. '+states+'.'
  }else{
   mairaModelChoice.value=''
   mairaConnectionResult.value='Modelo configurado respondió correctamente. '+states+'.'
  }
 }catch(e){mairaImportError.value=e instanceof Error?e.message:'Error de diagnóstico'}
 finally{mairaConnectionBusy.value=false}
}
async function analyzeMairaDocument(){
 if(!mairaImportStatus.value?.ready){mairaImportError.value='MAIRA no tiene Google y Gemini configurados.';return}
 if(!mairaGoogleToken.value){mairaImportError.value='Inicia sesión con Google para continuar.';return}
 if(!mairaSourceFile.value){mairaImportError.value='Selecciona un documento para analizar.';return}
 mairaImportBusy.value=true;mairaImportError.value='';mairaImportInfo.value='';mairaProposal.value=null;mairaApplyConfirm.value=false
 resetMairaQuestions()
 mairaSourceOnly.value=false
 mairaLiveHistory.value=[];mairaProgress('ENVIANDO','Enviando documento a MAIRA.')
 startMairaClock()
 let resultReceived=false
 try{
  const data=new FormData();data.append('file',mairaSourceFile.value,mairaSourceFile.value.name)
  if(mairaTargetParty.value)data.append('party_kind',mairaTargetParty.value.kind)
  if(mairaModelChoice.value)data.append('model_choice',mairaModelChoice.value)
  const response=await fetch(MAIRA_API+'/api/v1/maira/workflow-import/stream',{
    method:'POST',headers:{Authorization:'Bearer '+mairaGoogleToken.value},body:data
  })
  if(!response.ok){
   const body=await response.json().catch(()=>({detail:'No se pudo iniciar el análisis.'})) as {detail?:string}
   throw new Error(body.detail||'No se pudo iniciar el análisis ('+response.status+').')
  }
  if(!response.body)throw new Error('El servidor no proporcionó seguimiento del análisis.')
  const reader=response.body.getReader()
  const decoder=new TextDecoder()
  let pending=''
  const handleLine=(line:string)=>{
   if(!line.trim())return
   const event=JSON.parse(line) as MairaStreamEvent
   if(event.event==='progress'&&event.phase&&event.label)mairaProgress(event.phase,event.label)
   if(event.event==='done'&&event.result){
    mairaProposal.value=event.result;resultReceived=true;mairaDiagramVersion.value++
    mairaProgress('TERMINADO','Propuesta lista: '+event.result.mapped_steps+' actividades identificadas.')
    mairaImportInfo.value='MAIRA generó una propuesta. Revisa los pasos antes de aplicarla.'
   }
   if(event.event==='error')throw new Error(event.message||'MAIRA no pudo completar el análisis.')
  }
  while(true){
   const {done,value}=await reader.read()
   if(done)break
   pending+=decoder.decode(value,{stream:true})
   let pos=pending.indexOf('\n')
   while(pos!==-1){handleLine(pending.slice(0,pos));pending=pending.slice(pos+1);pos=pending.indexOf('\n')}
  }
  pending+=decoder.decode()
  if(pending.trim())handleLine(pending)
  if(!resultReceived)throw new Error('El análisis terminó sin propuesta. No se aplicaron cambios.')
 }catch(e){
  mairaImportError.value=e instanceof Error?e.message:'Error de análisis'
  mairaProgress('ERROR','El análisis no pudo finalizar. No se aplicaron cambios.')
 }finally{stopMairaClock();mairaImportBusy.value=false}
}

async function extractMairaPdfWithoutGemini(){
 if(!mairaImportStatus.value?.ready){mairaImportError.value='Verifica tu sesión de Smart Contract.';return}
 if(!mairaGoogleToken.value){mairaImportError.value='Debes iniciar sesión con Google.';return}
 if(!mairaSourceFile.value||!/\.pdf$/i.test(mairaSourceFile.value.name)){
  mairaImportError.value='Selecciona un PDF con texto seleccionable.';return
 }
 mairaImportBusy.value=true
 mairaImportError.value='';mairaImportInfo.value='';mairaProposal.value=null;mairaApplyConfirm.value=false
 resetMairaQuestions()
 mairaSourceOnly.value=true
 mairaLiveHistory.value=[];mairaProgress('ENVIANDO','Extrayendo pasos del PDF sin Gemini.')
 startMairaClock()
 try{
  const data=new FormData()
  data.append('file',mairaSourceFile.value,mairaSourceFile.value.name)
  if(mairaTargetParty.value)data.append('party_kind',mairaTargetParty.value.kind)
  const response=await fetch(MAIRA_API+'/api/v1/maira/workflow-import/source-preview',{
   method:'POST',headers:{Authorization:'Bearer '+mairaGoogleToken.value},body:data
  })
  const result=await response.json() as MairaProposal & {detail?:string;analysis_method?:string}
  if(!response.ok)throw new Error(result.detail||'No se pudo recuperar el texto del PDF.')
  if(result.analysis_method!=='PDF_TEXT_ONLY'||!result.workflow||!Array.isArray(result.source_map))
   throw new Error('No se recibió una vista documental válida.')
  mairaProposal.value=result;mairaDiagramVersion.value++
  mairaProgress('TERMINADO','Vista documental lista: '+result.mapped_steps+' actividades recuperadas.')
  mairaImportInfo.value='Extracción sin Gemini. Revisa cuidadosamente responsables, numeración y flechas antes de guardar.'
 }catch(e){
  mairaImportError.value=e instanceof Error?e.message:'No fue posible recuperar el PDF.'
  mairaProgress('ERROR','No se pudo completar la extracción local. No se aplicaron cambios.')
 }finally{stopMairaClock();mairaImportBusy.value=false}
}

async function saveMairaPreview(){
 if(!mairaProposal.value||!mairaTargetParty.value)return
 mairaPreviewSaving.value=true;mairaImportError.value=''
 try{
  const id=mairaTargetParty.value.id
  const preview=await portalRequest<PartyProcessPreview>('/parties/'+id+'/process-previews','POST',{
    filename:mairaSourceFile.value?.name||'Documento analizado',
    workflow:workflowWithMairaDialogue(mairaProposal.value),
    source_map:mairaProposal.value.source_map,
    questions:mairaProposal.value.questions,
    observations:mairaProposal.value.observations
  })
  partyPreview.value=preview
  partyPreviewTarget.value=mairaTargetParty.value
  mairaImportInfo.value='Vista previa guardada en '+mairaTargetParty.value.name+'. No se han activado tareas ni publicado el proceso.'
  await refreshPortal()
  if(expandedPartyId.value===id)await togglePartyRecord(mairaTargetParty.value,true)
 }catch(e){mairaImportError.value=e instanceof Error?e.message:'No se pudo guardar la vista previa'}
 finally{mairaPreviewSaving.value=false}
}
async function viewPartyProcessPreview(party:PartyRecord,previewId?:string){
 partyPreviewTarget.value=party;partyPreview.value=null;partyPreviewBusy.value=true
 portalError.value=''
 try{
  let id=previewId
  if(!id){
   const items=await portalRequest<{id:string}[]>('/parties/'+party.id+'/process-previews')
   id=items[0]?.id
  }
  if(!id){portalMessage.value='Este registro no tiene una propuesta de MAIRA guardada.';return}
  partyPreview.value=await portalRequest<PartyProcessPreview>('/parties/'+party.id+'/process-previews/'+id)
 }catch(e){portalError.value=e instanceof Error?e.message:'No se pudo consultar el proceso guardado'}
 finally{partyPreviewBusy.value=false}
}
function openReviewInDesigner(){
 if(!partyPreview.value)return
 try{
  loadDefinition(workflowWithEvidence(partyPreview.value,partyPreviewTarget.value?.kind))
  current.value='flujos'
  mairaImportOpen.value=false
  flowMessage.value='Propuesta en revisión para '+(partyPreviewTarget.value?.name||'tercero')+'. Revisa responsabilidades, requisitos y dependencias antes de publicar.'
 }catch(e){portalError.value=e instanceof Error?e.message:'No se pudo abrir el diseñador'}
}
function applyMairaProposal(){
 if(!mairaProposal.value)return
 if(!mairaQuestionsDone.value){mairaQuestionError.value='Responde las preguntas de MAIRA antes de continuar al diseñador.';return}
 const previous=definition()
 try{
  const proposal=mairaProposal.value
  const imported=workflowWithMairaDialogue(proposal)
  if(imported.nodes.length!==proposal.node_count||
     imported.nodes.filter(n=>Boolean(n.config?.source_step)).length!==proposal.mapped_steps){
    throw new Error('No coinciden los pasos del documento y los nodos del workflow.')
  }
  loadDefinition(imported)
  if(!validateDraft())throw new Error(errors.value.slice(0,3).join('; '))
  current.value='flujos'
  mairaImportOpen.value=false
  flowMessage.value='Workflow importado: '+proposal.mapped_steps+' actividades / '+
   imported.nodes.length+' nodos. Revisa responsables y conexiones; no se publicó ningún contrato.'
 }catch(e){
  loadDefinition(previous)
  mairaImportError.value=e instanceof Error?e.message:'No se pudo abrir el workflow generado'
 }
}

watch(mairaImportOpen,open=>{if(!open){mairaSourceFile.value=null;mairaProposal.value=null;mairaApplyConfirm.value=false}})

const nodes = shallowRef<Node[]>([])
const edges = shallowRef<Edge[]>([])
const studioCanvasMode=ref<'guided'|'canvas'>('guided')
const freeformMode=ref(false)
const directedChain=computed(()=>{
 const ordered=guidedOrderedNodes.value
 if(ordered.length<2||edges.value.length!==ordered.length-1)return false
 if(new Set(ordered.map(n=>n.id)).size!==ordered.length)return false
 return ordered.every((n,i)=>i===ordered.length-1||
   edges.value.some(e=>e.source===n.id&&e.target===ordered[i+1].id))
})

const compactSavedPositions=computed<Record<string,{x:number;y:number}>|null>(()=>{
 if(workflowMetadata.value.canvas_layout!=='manual')return null
 return Object.fromEntries(nodes.value.map(n=>[n.id,{x:n.position.x,y:n.position.y}]))
})
function onCompactMove(id:string,point:{x:number;y:number}){
 if(!nodes.value.some(n=>n.id===id))return
 const positions=compactSavedPositions.value
 const initial=buildEditableLayout(
   guidedOrderedNodes.value.map(n=>n.id),
   edges.value.map(e=>({id:e.id,source:e.source,target:e.target})),
   positions||{})
 const byId=new Map(initial.points.map(p=>[p.id,{x:p.x,y:p.y}]))
 nodes.value=nodes.value.map(n=>{
   const position=n.id===id?point:(positions?.[n.id]||byId.get(n.id)||n.position)
   return {...n,position:{x:position.x,y:position.y}}
 })
 workflowMetadata.value={...workflowMetadata.value,canvas_layout:'manual'}
 errors.value=[]
 flowMessage.value='Etapa movida. Guarda cambios en '+(editingLinkedDraft.value?.partyName||'tu borrador')+' para conservar la posición.'
}
function organizeCompactLayout(){
 const model=buildEditableLayout(
   guidedOrderedNodes.value.map(n=>n.id),
   edges.value.map(e=>({id:e.id,source:e.source,target:e.target})))
 const byId=new Map(model.points.map(p=>[p.id,{x:p.x,y:p.y}]))
 nodes.value=nodes.value.map(n=>({...n,position:{...(byId.get(n.id)||n.position)}}))
 workflowMetadata.value={...workflowMetadata.value,canvas_layout:'manual'}
 errors.value=[]
 flowMessage.value='Distribución reorganizada. Los pasos y conexiones no cambiaron; guarda para conservar las posiciones.'
}
function connectCompactNodes(source:string,target:string){
 onConnect({source,target} as Connection)
}
function selectCompactEdge(edgeId:string){
 if(!edges.value.some(e=>e.id===edgeId))return
 selectedId.value=null
 selectedEdgeId.value=edgeId
}

const guidedPage=ref(0)
const guidedPageSize=5
const guidedOrderedNodes=computed(()=>{
 const ordered:Node[]=[]
 const byId=new Map(nodes.value.map(n=>[n.id,n]))
 const rank=new Map(nodes.value.map((n,i)=>[n.id,i]))
 const incoming=new Map(nodes.value.map(n=>[n.id,0]))
 const outgoing=new Map(nodes.value.map(n=>[n.id,[] as string[]]))
 for(const edge of edges.value){
   if(incoming.has(edge.target)&&incoming.has(edge.source)){
     incoming.set(edge.target,(incoming.get(edge.target)||0)+1)
     outgoing.get(edge.source)?.push(edge.target)
   }
 }
 const available=nodes.value.filter(n=>incoming.get(n.id)===0).sort((a,b)=>(rank.get(a.id)||0)-(rank.get(b.id)||0))
 while(available.length){
   const currentNode=available.shift()!
   ordered.push(currentNode)
   for(const to of outgoing.get(currentNode.id)||[]){
     incoming.set(to,(incoming.get(to)||1)-1)
     if(incoming.get(to)===0){
       const candidate=byId.get(to)
       if(candidate){available.push(candidate);available.sort((a,b)=>(rank.get(a.id)||0)-(rank.get(b.id)||0))}
     }
   }
 }
 return ordered.length===nodes.value.length?ordered:nodes.value
})
const guidedActivities=computed(()=>guidedOrderedNodes.value.filter(n=>{
 const kind=(n.data as WorkNode).kind
 return kind!=='START'&&kind!=='END'
}))
const guidedPages=computed(()=>Math.max(1,Math.ceil(guidedActivities.value.length/guidedPageSize)))
const guidedCurrentPage=computed(()=>Math.min(guidedPage.value,guidedPages.value-1))
const guidedVisible=computed(()=>guidedActivities.value.slice(guidedCurrentPage.value*guidedPageSize,
 (guidedCurrentPage.value+1)*guidedPageSize))
function selectGuidedStage(id:string){
 selectedId.value=id;selectedEdgeId.value=null
}
function guidedSide(n:Node){
 const side=(n.data as WorkNode).config?.actor_side
 return side==='CONTRATANTE'?'Contratante':side==='CONTRATISTA'?'Contratista':'Por confirmar'
}
function guidedStageLabel(n:Node){
 const type=(n.data as WorkNode).kind
 return blocks.find(b=>b.kind===type)?.title||'Actividad'
}
function guidedHasDirectEdge(source:string,target:string){
 return edges.value.some(e=>e.source===source&&e.target===target)
}
function changeGuidedPage(page:number){
 guidedPage.value=Math.max(0,Math.min(guidedPages.value-1,page))
 const first=guidedVisible.value[0]
 if(first)selectGuidedStage(first.id)
}
function originalPoint(i:number){
 return {x:260,y:i*152+48}
}
function isLegacySerpentineOriginal(nodesList:Node[]){
 if(workflowKey.value!=='SMART_CICLO_CONTRATACION_V2'||
   workflowMetadata.value.source!=='smart-contract-original-pdf'||nodesList.length!==25)return false
 let matching=0
 for(let i=0;i<nodesList.length;i++){
   const col=i%5
   const row=Math.floor(i/5)
   const oldX=(row%2===0?col:4-col)*315+35
   const oldY=row*175+30
   if(Math.abs(nodesList[i].position.x-oldX)<3&&Math.abs(nodesList[i].position.y-oldY)<3)matching++
 }
 return matching>=23
}
function organizeOriginalCanvas(){
 // Positions only, never changes the 23 activities, roles, metadata or edges.
 if(workflowKey.value!=='SMART_CICLO_CONTRATACION_V2')return
 const ordered=guidedOrderedNodes.value
 const placement=new Map(ordered.map((n,i)=>[n.id,originalPoint(i)]))
 nodes.value=nodes.value.map(n=>{
   const p=placement.get(n.id)
   return p?{...n,position:p,targetPosition:Position.Top,sourcePosition:Position.Bottom}:n
 })
 edges.value=edges.value.map(e=>({...e,type:'smoothstep'}))
 studioDiagramVersion.value++
 flowMessage.value='Organización vertical aplicada a la vista. Las 23 actividades y las 24 conexiones permanecen intactas. Guarda los cambios para conservar las posiciones.'
}
watch(guidedPages,()=>{guidedPage.value=Math.min(guidedPage.value,guidedPages.value-1)})


function nodeInfo(id:string, kind:Kind, label:string, x:number,y:number,role:string|null=null,policy:Policy='OPTIONAL'):Node {
  return {id,type:kind==='START'?'input':kind==='END'?'output':'default',position:{x,y},data:{label,kind,role,policy,enabled:true,config:{execution_mode:'MANUAL',fields:[]}},class:kind==='START'?'node-start':kind==='END'?'node-end':'node-'+kind.toLowerCase()}
}
function loadOriginalContractFlowDraft(){
 studioCanvasMode.value='guided'
 guidedPage.value=0
 studioTab.value='pantallas'
 originalScopeChoice.value='';originalClarificationAnswers.value={}
 const draft=buildOriginalContractFlow()
 loadDefinition(draft)
 selectedId.value='original_1';selectedEdgeId.value=null
 flowMessage.value='Flujo original del PDF cargado: 23 actividades, 25 nodos y 24 conexiones. Puedes revisar ambos portales sin publicar.'
}
function newWorkflow(){
 editingLinkedDraft.value=null
 workflowMetadata.value={source:'smart-contract-workflow-studio',draft:true};resetSourceReview()
  workflowName.value='Nuevo proceso de contratación';workflowKey.value='NUEVO_PROCESO';modalityKey.value=''
  nodes.value=[nodeInfo('inicio','START','Inicio',230,60,null,'ORG_REQUIRED'),nodeInfo('fin','END','Finalización',230,270,null,'ORG_REQUIRED')]
  edges.value=[{id:'e-inicio-fin',source:'inicio',target:'fin'}]
  selectedId.value=null;selectedEdgeId.value=null;nodeCounter.value=1;errors.value=[];simulationVisible.value=false;flowMessage.value='Proceso en blanco. Agrega bloques desde el catálogo.'
}
loadOriginalContractFlowDraft()
const selectedNode = computed(() => nodes.value.find(n=>n.id===selectedId.value))
const selectedEdge = computed(() => edges.value.find(e=>e.id===selectedEdgeId.value))
const selectedEdgeCondition = computed(() => (selectedEdge.value?.data as {when?:Condition}|undefined)?.when)
const incidentEdges = computed(() => edges.value.filter(e=>e.source===selectedId.value||e.target===selectedId.value))
function onNodeDragStop(){nodes.value=nodes.value.map(n=>({...n,position:{...n.position}}))}
function labelFor(id:string){return String((nodes.value.find(n=>n.id===id)?.data as WorkNode|undefined)?.label||id)}
function castValue(text:string):unknown{
 const trimmed=text.trim()
 if(trimmed==='true')return true
 if(trimmed==='false')return false
 if(trimmed==='null')return null
 if(trimmed!==''&&Number.isFinite(Number(trimmed))&&trimmed.length<20)return Number(trimmed)
 if(trimmed.startsWith('[')&&trimmed.endsWith(']')){try{const v=JSON.parse(trimmed);if(Array.isArray(v))return v}catch{}}
 return text
}
function createCondition(field:string,old?:Condition|null):Condition|null{
 return field.trim()?{field:field.trim(),op:old?.op||'eq',value:old?.value??''}:null
}
function conditionValueText(value:unknown){return typeof value==='string'?value:JSON.stringify(value)??''}
const selectedData = computed(() => selectedNode.value?.data as WorkNode | undefined)
const nodeCount = computed(() => nodes.value.length)
const activeCount = computed(() => nodes.value.filter(n=>(n.data as WorkNode).enabled).length)
const policyCount = computed(() => nodes.value.filter(n=>['ORG_REQUIRED','LEGAL_LOCKED'].includes((n.data as WorkNode).policy)).length)
const stageLabel = computed(() => selectedData.value?.label || 'Selecciona una etapa')
const mairaContext = computed(() => {
  switch (current.value) {
    case 'resumen':
      return {title:'Tu centro de control',detail:'Aquí puedes consultar el borrador local y continuar diseñando procesos. No hay información de contratos reales.'}
    case 'flujos':
      return {title:selectedData.value ? 'Etapa: '+selectedData.value.label : 'Diseño del workflow',
        detail:selectedData.value
          ? 'Tipo: '+selectedData.value.kind+' · Responsable: '+(selectedData.value.role||'sin asignar')+'. Puedes editar esta etapa desde Propiedades.'
          : 'Tu borrador tiene '+nodeCount.value+' etapas y '+edges.value.length+' conexiones. Selecciona una etapa para ver su contexto.'}
    case 'personas':
      return {title:'Personas y empresas',detail:'Registra terceros una sola vez; no necesitan un workflow para existir.'}
    case 'contrataciones':
      return {title:'Gestión Contractual',detail:'Publica plantillas y crea expedientes de prueba, cada uno con tareas para contratante y contratista.'}
    case 'prestadores':
      return {title:'Mi Contratación',detail:'Aquí solo verás expedientes a los que tu correo haya sido invitado.'}
    case 'configuracion':
      return {title:'Configuración',detail:'Los roles y las políticas de cada empresa se administrarán aquí cuando esté habilitado el acceso multiempresa.'}
    case 'maira':
      return {title:'MAIRA Intelligence',detail:'La asistencia contextual está disponible en toda la plataforma. La interpretación mediante Gemini todavía no está conectada.'}
  }
})
const mairaShortcuts = computed(() => !hasInstitution.value ? [{key:'mine',label:'Mi Contratación',icon:'▤'}] : current.value==='flujos'
  ? [{key:'verify',label:'Verificar estructura',icon:'✓'},{key:'simulate',label:'Simular borrador',icon:'◇'},{key:'approval',label:'Agregar aprobación',icon:'+'},{key:'export',label:'Exportar JSON',icon:'↧'}]
  : [{key:'workflow',label:'Abrir Workflow Studio',icon:'◇'},{key:'maira',label:'Conocer capacidades de MAIRA',icon:'✧'}]
)
function mairaShortcut(key:string){
  mairaLastAction.value=''
  if(key==='workflow'){if(hasInstitution.value)current.value='flujos';else openProviderPortal();mairaLastAction.value='Espacio disponible abierto.'}
  else if(key==='mine'){openProviderPortal();mairaLastAction.value='Portal de prestadores abierto.'}
  else if(key==='maira'){current.value='maira';mairaLastAction.value='Vista de MAIRA abierta.'}
  else if(key==='verify'){
    const valid=validateDraft()
    mairaLastAction.value=valid?'El borrador pasó la verificación estructural local. No es una aprobación jurídica.':'La verificación encontró '+errors.value.length+' observación(es). Revisa los detalles en el diseñador.'
  }
  else if(key==='simulate'){simulateDraft();mairaLastAction.value=simulationError.value||'Simulación local calculada. Revisa sus resultados debajo del diagrama.'}
  else if(key==='approval'){addBlock('APPROVAL');mairaLastAction.value='Agregué una etapa de aprobación en el borrador local. Configura su responsable y verifica las dependencias.'}
  else if(key==='export'){exportDraft();mairaLastAction.value='Borrador exportado a JSON desde este navegador.'}
}

function editNode(field:'label'|'role'|'enabled'|'policy'|'instructions'|'conditionField'|'conditionValue'|'conditionOperator'|'executionMode'|'actorSide', val:string|boolean){
  if(!selectedNode.value || !selectedData.value)return
  const target=selectedData.value
  if(field==='enabled' && val===false && ['ORG_REQUIRED','LEGAL_LOCKED'].includes(target.policy)){
    flowMessage.value='Una etapa protegida no se puede desactivar.';return
  }
  const next:Record<string,unknown>={...target}
  if(field==='instructions') next.config={...target.config,instructions:String(val)}
  else if(field==='conditionField')next.when=createCondition(String(val),target.when)
   else if(field==='conditionOperator'&&target.when)next.when={...target.when,op:val}
   else if(field==='conditionValue'&&target.when)next.when={...target.when,value:castValue(String(val))}
   else if(field==='executionMode')next.config={...target.config,execution_mode:String(val)}
   else if(field==='actorSide')next.config={...target.config,actor_side:String(val)}
   else if(field==='policy') {
     if(['LEGAL_LOCKED','ORG_REQUIRED'].includes(target.policy)&&!['LEGAL_LOCKED','ORG_REQUIRED'].includes(String(val))){flowMessage.value='No puedes rebajar la protección de una etapa obligatoria desde el editor.';return}
     next.policy=val; if(['ORG_REQUIRED','LEGAL_LOCKED'].includes(String(val)))next.enabled=true
   }
  else if(field==='role')next.role=val===''?null:val
  else next[field]=val
  nodes.value=nodes.value.map(n=>n.id===selectedId.value?{...n,data:next,class:next.enabled===false?'node-disabled':n.type==='input'?'node-start':n.type==='output'?'node-end':'node-'+String(next.kind||'').toLowerCase()}:n)
  errors.value=[]
}
function editField(index:number,property:keyof WorkField,value:string|boolean){
 if(!selectedNode.value||!selectedData.value)return
 const conf=selectedData.value.config||{}
 const fields=[...(conf.fields||[])]
 if(!fields[index])return
 fields[index]={...fields[index],[property]:value}
 updateNodeConfig({...conf,fields})
}
function updateNodeConfig(config:WorkNode['config']){
 if(!selectedNode.value||!selectedData.value)return
 nodes.value=nodes.value.map(n=>n.id===selectedId.value?{...n,data:{...n.data,config}}:n)
 errors.value=[]
}
function addField(){
 if(!selectedData.value)return
 const fields=[...(selectedData.value.config?.fields||[])]
 const used=new Set(fields.map(f=>f.key))
 let i=fields.length+1;while(used.has('campo_'+i))i++
 fields.push({key:'campo_'+i,label:'Nuevo campo',type:'text',required:false})
 updateNodeConfig({...selectedData.value.config,fields})
}
function removeField(index:number){
 if(!selectedData.value)return
 const fields=(selectedData.value.config?.fields||[]).filter((_,i)=>i!==index)
 updateNodeConfig({...selectedData.value.config,fields})
}
function editEdge(field:'field'|'operator'|'value',value:string){
 if(!selectedEdge.value)return
 const old=(selectedEdge.value.data as {when?:Condition}|undefined)?.when
 const when=field==='field'?createCondition(value,old):old?({...old,...(field==='operator'?{op:value}:{value:castValue(value)})}):null
 edges.value=edges.value.map(e=>e.id===selectedEdgeId.value?{...e,data:{...e.data,when}}:e)
 errors.value=[]
}
function removeEdge(id:string){
 edges.value=edges.value.filter(e=>e.id!==id)
 selectedEdgeId.value=null;errors.value=[];flowMessage.value='Conexión eliminada. Verifica que no haya etapas aisladas.'
}
function nextNodeId(){nodeCounter.value+=1;return 'etapa_'+Date.now().toString(36)+'_'+nodeCounter.value}
function addBlock(kind:Kind){
  const block=blocks.find(b=>b.kind===kind)
  if(!block)return
  let point=nodes.value.find(n=>n.id===selectedId.value) || nodes.value.find(n=>n.type==='input')
  if(!point)return
  const id=nextNodeId()
  // Insert between the selected node and all outgoing connections.
  let outbound=edges.value.filter(e=>e.source===point?.id)
  if(point.type==='output'){
    const incoming=edges.value.filter(e=>e.target===point?.id)
    if(incoming.length===1){point=nodes.value.find(n=>n.id===incoming[0].source)||point;const anchorId=point.id;outbound=edges.value.filter(e=>e.source===anchorId)}
  }
  const newY=point.position.y+136
  const newX=point.position.x
  const added=nodeInfo(id,kind,block.title,newX,newY,kind==='APPROVAL'?'JURIDICO':null)
  nodes.value=nodes.value.map(n=>(n.position.y>=newY)?{...n,position:{...n.position,y:n.position.y+138}}:n).concat(added)
  if(outbound.length){
    edges.value=edges.value.filter(e=>!outbound.some(o=>o.id===e.id)).concat(
      {id:'edge_'+id,source:point.id,target:id},
      ...outbound.map(e=>({...e,id:e.id+'_'+id,source:id}))
    )
  }else{
    edges.value=edges.value.concat({id:'edge_'+id,source:point.id,target:id})
  }
  selectedId.value=id;selectedEdgeId.value=null;errors.value=[];flowMessage.value='Etapa agregada. Configura sus propiedades a la derecha.'
}
function removeNode(){
  const n=selectedNode.value
  if(!n)return
  const data=n.data as WorkNode
  if(n.type==='input'||n.type==='output'||['LEGAL_LOCKED','ORG_REQUIRED'].includes(data.policy)){
    flowMessage.value='Las etapas de inicio, finalización y las protegidas no se pueden eliminar.';return
  }
  const incoming=edges.value.filter(e=>e.target===n.id)
  const outgoing=edges.value.filter(e=>e.source===n.id)
  edges.value=edges.value.filter(e=>e.source!==n.id&&e.target!==n.id)
  if(incoming.length===1&&outgoing.length===1&&incoming[0].source!==outgoing[0].target){
    edges.value.push({id:'bridge_'+n.id,source:incoming[0].source,target:outgoing[0].target})
  }
  nodes.value=nodes.value.filter(x=>x.id!==n.id)
  selectedId.value=null;selectedEdgeId.value=null;errors.value=[];flowMessage.value='Etapa retirada. Revisa las conexiones resultantes.'
}
function onConnect(connection:Connection){
  const source=connection.source,target=connection.target
  if(!source||!target||source===target)return
  if(nodes.value.some(n=>n.id===source&&n.type==='output')||nodes.value.some(n=>n.id===target&&n.type==='input')){
    flowMessage.value='No puedes conectar desde la finalización ni hacia el inicio.';return
  }
  if(edges.value.some(e=>e.source===source&&e.target===target))return
  edges.value=[...edges.value,{id:'link_'+source+'_'+target,source,target}]
  if(hasCycle()){
    edges.value=edges.value.filter(e=>!(e.source===source&&e.target===target))
    flowMessage.value='Esa conexión crearía una dependencia circular.';return
  }
  errors.value=[];flowMessage.value='Conexión creada.'
}
function hasCycle():boolean{
  const indeg=new Map<string,number>(nodes.value.map(n=>[n.id,0] as const))
  for(const e of edges.value) indeg.set(e.target,(indeg.get(e.target)||0)+1)
  const q=Array.from(indeg.keys()).filter(id=>indeg.get(id)===0);let visited=0
  while(q.length){const id=q.shift()!;visited++;for(const e of edges.value.filter(e=>e.source===id)){indeg.set(e.target,(indeg.get(e.target)||0)-1);if(indeg.get(e.target)===0)q.push(e.target)}}
  return visited!==nodes.value.length
}
function validateDraft():boolean{
  const problems:string[]=[]
  const ids=new Set(nodes.value.map(n=>n.id))
  const starts=nodes.value.filter(n=>(n.data as WorkNode).kind==='START'),ends=nodes.value.filter(n=>(n.data as WorkNode).kind==='END')
  if(!workflowName.value.trim()||!workflowKey.value.trim())problems.push('Define el nombre y la clave del proceso.')
   if(!/^[a-zA-Z0-9_-]{1,120}$/.test(workflowKey.value.trim()))problems.push('El identificador solo permite letras, números, guiones y guion bajo.')
   if(ids.size!==nodes.value.length)problems.push('Existen identificadores de etapas repetidos.')
  if(starts.length!==1)problems.push('Debe existir exactamente una etapa de inicio.')
  if(ends.length===0)problems.push('Debe existir al menos una etapa de finalización.')
  for(const e of edges.value){
     if(!ids.has(e.source)||!ids.has(e.target))problems.push('Hay una conexión con una etapa inexistente.')
     if(e.source===e.target)problems.push('No se permiten autoconexiones.')
     if((nodes.value.find(n=>n.id===e.source)?.data as WorkNode)?.kind==='END')problems.push('Una etapa final no puede tener salidas.')
     if((nodes.value.find(n=>n.id===e.target)?.data as WorkNode)?.kind==='START')problems.push('Una etapa inicial no puede recibir entradas.')
   }
  for(const n of nodes.value){const d=n.data as WorkNode
    if(!String(d.label||'').trim())problems.push('Hay una etapa sin nombre.')
    if(!d.enabled&&['LEGAL_LOCKED','ORG_REQUIRED'].includes(d.policy))problems.push('La etapa '+d.label+' está protegida y no puede desactivarse.')
    if(d.enabled&&d.kind==='APPROVAL'&&!d.role)problems.push('Asigna responsable a la aprobación '+d.label+'.')
    if(d.enabled&&d.policy==='CONDITIONAL'&&!d.when?.field)problems.push('Define la condición de activación de '+d.label+'.')
     const fields=d.config?.fields||[]
     if(new Set(fields.map(f=>f.key)).size!==fields.length)problems.push('Hay campos duplicados en '+d.label+'.')
     for(const f of fields)if(!/^[a-zA-Z0-9_-]{1,120}$/.test(f.key)||!f.label.trim())problems.push('Revisa los identificadores y nombres de campos en '+d.label+'.')
  }
  if(hasCycle())problems.push('El flujo contiene dependencias circulares.')
  if(starts.length===1){
    const seen=new Set<string>(),q=[starts[0].id]
    while(q.length){const id=q.shift()!;if(seen.has(id))continue;seen.add(id);q.push(...edges.value.filter(e=>e.source===id).map(e=>e.target))}
    for(const n of nodes.value)if(!seen.has(n.id))problems.push('No se puede acceder desde el inicio a '+String((n.data as WorkNode).label)+'.')
    const reverse=new Set<string>(),r=ends.map(e=>e.id)
    while(r.length){const id=r.shift()!;if(reverse.has(id))continue;reverse.add(id);r.push(...edges.value.filter(e=>e.target===id).map(e=>e.source))}
    for(const n of nodes.value)if(!reverse.has(n.id))problems.push('La etapa '+String((n.data as WorkNode).label)+' no llega a una finalización.')
  }
  errors.value=Array.from(new Set(problems))
  flowMessage.value=problems.length?'Hay '+errors.value.length+' observación(es) por resolver.':'Estructura validada. La aprobación normativa y publicación aún requieren controles institucionales.'
  return problems.length===0
}
function definition():Workflow{
  return {key:workflowKey.value.trim(),name:workflowName.value.trim(),modality_key:modalityKey.value.trim()||null,
    nodes:nodes.value.map(n=>{const d=n.data as WorkNode;return {id:n.id,label:String(d.label),kind:d.kind,role:d.role||null,policy:d.policy,enabled:d.enabled,when:d.when||null,config:{...d.config,position:{x:n.position.x,y:n.position.y}}}}),
    edges:edges.value.map(e=>({source:e.source,target:e.target,when:(e.data as {when?:Condition}|undefined)?.when||null})),
    metadata:{...workflowMetadata.value,draft:true,review_confirmed:sourceReviewRequired.value?sourceReviewConfirmed.value:false}}
}
function exportDraft(){
  const result=definition()
  const blob=new Blob([JSON.stringify(result,null,2)],{type:'application/json'})
  const url=URL.createObjectURL(blob),link=document.createElement('a')
  link.href=url;link.download=(workflowKey.value.trim()||'workflow').replace(/[^a-zA-Z0-9_-]/g,'_')+'.json';link.click()
  URL.revokeObjectURL(url)
  flowMessage.value='Borrador exportado. No se ha guardado en el servidor.'
}
function loadDefinition(parsed:Partial<Workflow>){
 editingLinkedDraft.value=null
 if(!parsed.key||!parsed.name||!Array.isArray(parsed.nodes)||!Array.isArray(parsed.edges)||parsed.nodes.length>2000||parsed.edges.length>6000)throw new Error('El archivo no contiene un workflow válido.')
 const validKinds=new Set<Kind>(['START','FORM','DOCUMENT_REQUEST','DOCUMENT_REVIEW','VALIDATION','APPROVAL','NEGOTIATION','CALCULATION','DOCUMENT_GENERATION','SIGNATURE','NOTIFICATION','INTEGRATION','TIMER','JOIN','HUMAN_DECISION','END'])
 const validPolicies=new Set<Policy>(['LEGAL_LOCKED','ORG_REQUIRED','CONDITIONAL','OPTIONAL'])
 const validOps=new Set(conditionOperators.map(x=>x.value))
 const validFields=new Set<FieldType>(fieldTypes)
 function safeCondition(c:unknown):Condition|null{
   if(c==null)return null
   if(typeof c!=='object'||!c||Array.isArray(c))throw new Error('Condición inválida.')
   const value=c as Condition
   if(typeof value.field!=='string'||!value.field.trim()||!validOps.has(value.op))throw new Error('Condición incompleta o no admitida.')
   return {field:value.field.trim(),op:value.op,value:value.value}
 }
 const documentary=parsed.metadata?.source==='maira-document-import'
 const imported:Node[]=parsed.nodes.map((raw,i)=>{
   if(typeof raw.id!=='string'||!raw.id.trim()||raw.id.length>120||typeof raw.label!=='string'||!raw.label.trim()||!validKinds.has(raw.kind)||!validPolicies.has(raw.policy)||typeof raw.enabled!=='boolean')throw new Error('La etapa '+(i+1)+' tiene valores inválidos.')
   if(!raw.enabled&&['LEGAL_LOCKED','ORG_REQUIRED'].includes(raw.policy))throw new Error('El archivo intenta desactivar un requisito protegido.')
   const fields=(raw.config?.fields||[]).map(f=>{
     if(typeof f.key!=='string'||typeof f.label!=='string'||!validFields.has(f.type)||typeof f.required!=='boolean')throw new Error('Campo inválido en '+raw.label)
     return {key:f.key,label:f.label,type:f.type,required:f.required}
   })
   const position=raw.config?.position
   const suggested=documentary?mairaGraphPosition(i,parsed.nodes!.length):{x:260,y:i*130}
   const x=typeof position?.x==='number'&&Number.isFinite(position.x)?position.x:suggested.x
   const y=typeof position?.y==='number'&&Number.isFinite(position.y)?position.y:suggested.y
   const n=nodeInfo(raw.id,raw.kind,raw.label,x,y,raw.role||null,raw.policy);if(!raw.enabled)n.class='node-disabled'
   const mode=raw.config?.execution_mode
   n.data={label:raw.label,kind:raw.kind,role:raw.role||null,policy:raw.policy,enabled:raw.enabled,when:safeCondition(raw.when),config:{position:{x,y},instructions:String(raw.config?.instructions||'').slice(0,5000),execution_mode:executionModes.some(x=>x.value===mode)?mode:'MANUAL',fields,
     source_step:typeof raw.config?.source_step==='string'?raw.config.source_step.slice(0,40):undefined,
     source_excerpt:typeof raw.config?.source_excerpt==='string'?raw.config.source_excerpt.slice(0,650):undefined,
     source_page:typeof raw.config?.source_page==='number'?raw.config.source_page:null,
     source_confidence:typeof raw.config?.source_confidence==='string'?raw.config.source_confidence.slice(0,25):undefined,
     actor_side:raw.config?.actor_side==='REVISAR'?'REVISAR':raw.config?.actor_side==='CONTRATISTA'?'CONTRATISTA':'CONTRATANTE',
     party_scope_pending:raw.config?.party_scope_pending===true}}
   return n
 })
 const parsedEdges:Edge[]=parsed.edges.map((e,i)=>{
   if(typeof e.source!=='string'||typeof e.target!=='string')throw new Error('Conexión inválida '+(i+1))
   return{id:'import_'+i,source:e.source,target:e.target,data:{when:safeCondition(e.when)}}
 })
 if(new Set(imported.map(n=>n.id)).size!==imported.length)throw new Error('Hay identificadores de etapa repetidos.')
 const ids=new Set(imported.map(n=>n.id))
 if(parsedEdges.some(e=>!ids.has(e.source)||!ids.has(e.target)))throw new Error('Hay conexiones con etapas inexistentes.')
 workflowKey.value=parsed.key;workflowName.value=parsed.name;modalityKey.value=parsed.modality_key||''
 workflowMetadata.value={...(parsed.metadata||{}),draft:true}
 resetSourceReview()
 // Old two-dimensional serpentine diagram caused unreadable crossings when
 // rendered with Vue Flow's default vertical input/output handles.
 const originalKey=parsed.key==='SMART_CICLO_CONTRATACION_V2' &&
   parsed.metadata?.source==='smart-contract-original-pdf'
 const legacySerpentine=originalKey&&imported.length===25&&imported.every((n,i)=>{
    const col=i%5, row=Math.floor(i/5)
    return Math.abs(n.position.x-((row%2===0?col:4-col)*315+35))<3 &&
      Math.abs(n.position.y-(row*175+30))<3
 })
 nodes.value=legacySerpentine?imported.map((n,i)=>({...n,
   position:originalPoint(i),sourcePosition:Position.Bottom,targetPosition:Position.Top})):
   imported.map(n=>originalKey?{...n,sourcePosition:Position.Bottom,targetPosition:Position.Top}:n)
 edges.value=originalKey?parsedEdges.map(e=>({...e,type:'smoothstep'})):parsedEdges
 selectedId.value=null;selectedEdgeId.value=null;simulationVisible.value=false
 guidedPage.value=0
 nodeCounter.value=imported.length+1;errors.value=[];studioDiagramVersion.value++
}
async function importDraft(event:Event){
 const input=event.target as HTMLInputElement,file=input.files?.[0]
 if(!file)return
 try{
   if(file.size>1500000)throw new Error('Archivo demasiado grande (máximo 1,5 MB).')
   loadDefinition(JSON.parse(await file.text()) as Partial<Workflow>)
   validateDraft()
   flowMessage.value='Archivo importado como borrador local. Verifica el flujo antes de utilizarlo.'
 }catch(e){flowMessage.value='No se pudo importar: '+(e instanceof Error?e.message:'archivo incorrecto')}
 finally{input.value=''}
}
function isLegacyTwoPortalExample(draft:Partial<Workflow>):boolean{
 if(draft.name!=='Ciclo de contratación · prueba entre dos portales')return false
 if(!Array.isArray(draft.nodes)||draft.nodes.length!==4)return false
 const labels=new Set(draft.nodes.map(n=>n.label))
 return labels.has('Datos del contratista')&&labels.has('Revisión interna')
}
function openArchivedPilotDraft(){
 if(!archivedPilotDraft.value)return
 try{
  loadDefinition(archivedPilotDraft.value)
  studioTab.value='pantallas'
  flowMessage.value='Se abrió el ejercicio histórico de dos tareas. Para cerrar el proceso completo, vuelve al flujo original de 23 actividades.'
 }catch(e){flowMessage.value='No se pudo abrir el ejercicio anterior: '+(e instanceof Error?e.message:'borrador inválido')}
}
function restoreLocalDraft(){
 // Preserve previous local work without allowing an unrelated Famisanar draft
 // or the two-task demonstration to replace the original 23-step PDF on entry.
 try{
   const archived=localStorage.getItem(ARCHIVED_PILOT_DRAFT_KEY)
   if(archived){
    const parsedArchive=JSON.parse(archived) as Partial<Workflow>
    if(isLegacyTwoPortalExample(parsedArchive))archivedPilotDraft.value=parsedArchive
   }
   const raw=localStorage.getItem(LOCAL_DRAFT_KEY)
   if(!raw)return
   const parsed=JSON.parse(raw) as Partial<Workflow>
   const legacy=isLegacyTwoPortalExample(parsed)
   const unrelated=parsed.key==='FAMISANAR_RED_PRESTADORA_CASO_01'||
     parsed.metadata?.source==='famisanar-documental'
   if(legacy||unrelated){
     const archiveKey=legacy?ARCHIVED_PILOT_DRAFT_KEY:
       'smart-contract:workflow-studio:archive:famisanar-deferred:v6.6.4'
     try{
       localStorage.setItem(archiveKey,raw)
       if(legacy)archivedPilotDraft.value=parsed
       loadOriginalContractFlowDraft()
       flowMessage.value=legacy?
         'El ejemplo anterior de dos actividades quedó respaldado. Se cargó el flujo completo del PDF.':
         'El borrador de Famisanar quedó respaldado para otra fase. Continuamos con el primer workflow.'
     }catch{
       // Keep current user work rather than risk irreversible data loss.
       loadDefinition(parsed)
       flowMessage.value='No se pudo respaldar el borrador previo. No se ha eliminado; abre el Flujo original para continuar.'
     }
     return
   }
   loadDefinition(parsed)
   flowMessage.value='Se recuperó el borrador que estabas editando.'
 }catch{flowMessage.value='No se pudo recuperar el borrador local. Se cargó el flujo original de 23 actividades.'}
}
restoreLocalDraft()
watch([nodes,edges,workflowKey,workflowName,modalityKey],()=>{
 try{localStorage.setItem(LOCAL_DRAFT_KEY,JSON.stringify(definition()));lastSavedAt.value=new Date().toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit'})}
 catch{lastSavedAt.value='No disponible'}
},{deep:true})
function getValue(data:Record<string,unknown>,path:string):unknown{
 let current:unknown=data
 for(const token of path.split('.')){
   if(!current||typeof current!=='object'||!(token in current))return undefined
   current=(current as Record<string,unknown>)[token]
 }
 return current
}
function evaluateCondition(c:Condition|null|undefined,facts:Record<string,unknown>):boolean|null{
 if(!c)return true
 const actual=getValue(facts,c.field)
 if(c.op==='exists')return actual!==undefined&&actual!==null
 if(actual===undefined)return null
 const expected=c.value
 try{
   switch(c.op){
     case 'eq':return actual===expected
     case 'neq':return actual!==expected
     case 'gt':return typeof actual==='number'&&typeof expected==='number'?actual>expected:null
     case 'gte':return typeof actual==='number'&&typeof expected==='number'?actual>=expected:null
     case 'lt':return typeof actual==='number'&&typeof expected==='number'?actual<expected:null
     case 'lte':return typeof actual==='number'&&typeof expected==='number'?actual<=expected:null
     case 'in':return Array.isArray(expected)?expected.includes(actual):null
   }
 }catch{return null}
 return null
}
function simulateDraft(){
 simulationError.value='';simulationStatuses.value={};simulationVisible.value=true
 if(!validateDraft()){simulationError.value='Corrige las observaciones del flujo antes de simular.';return}
 let facts:Record<string,unknown>
 try{
   const data:unknown=JSON.parse(simulationFacts.value)
   if(!data||typeof data!=='object'||Array.isArray(data))throw Error('Objeto JSON requerido')
   facts=data as Record<string,unknown>
 }catch{simulationError.value='Datos de simulación inválidos: utiliza un objeto JSON.';return}
 const done=new Set(simulationCompleted.value.split(',').map(x=>x.trim()).filter(Boolean))
 const indegree=new Map(nodes.value.map(n=>[n.id,0]))
 const connected=new Map(nodes.value.map(n=>[n.id,[] as string[]]))
 for(const e of edges.value){indegree.set(e.target,(indegree.get(e.target)||0)+1);connected.get(e.source)?.push(e.target)}
 const queue=nodes.value.map(n=>n.id).filter(id=>(indegree.get(id)||0)===0)
 const status:Record<string,string>={}
 while(queue.length){
   const id=queue.shift()!,n=nodes.value.find(x=>x.id===id)!,d=n.data as WorkNode
   const incoming=edges.value.filter(e=>e.target===id)
   const pre=evaluateCondition(d.when,facts)
   if(!d.enabled)status[id]='OMITIDA'
   else if(pre===false)status[id]='NO_APLICA'
   else if(pre===null)status[id]='FALTA_DATO'
   else if(done.has(id))status[id]='COMPLETADA'
   else if(incoming.some(e=>evaluateCondition((e.data as {when?:Condition}|undefined)?.when,facts)===null))status[id]='FALTA_DATO'
   else {
     const active=incoming.filter(e=>evaluateCondition((e.data as {when?:Condition}|undefined)?.when,facts)===true)
     if(incoming.length&&!active.length)status[id]='RUTA_NO_APLICA'
     else if(active.every(e=>status[e.source]==='COMPLETADA'))status[id]='DISPONIBLE'
     else status[id]='PENDIENTE'
   }
   for(const target of connected.get(id)||[]){indegree.set(target,(indegree.get(target)||0)-1);if(indegree.get(target)===0)queue.push(target)}
 }
 simulationStatuses.value=status
 flowMessage.value='Simulación estructural local finalizada. No aprueba ni ejecuta contratos.'
}

</script>

<template>
  <div v-if="!loginToken" class="login-screen">
    <div class="login-panel">
      <img src="/smart-wordmark.png" class="login-logo" alt="Smart" />
      <h1>{{providerPortalMode?'Portal de prestadores':'Smart Contract'}}</h1>
      <p>{{providerPortalMode?'Ingresa con el correo que recibió la invitación contractual.':'Inicia sesión con tu cuenta Google para acceder a la plataforma contractual.'}}</p>
      <div v-if="loginChecking" class="login-loading" role="status">Verificando acceso…</div>
      <div v-else-if="!mairaImportStatus?.google_enabled" class="login-warning" role="status">El inicio de sesión aún no está configurado. Comprueba el servicio API de Smart Contract.</div>
      <div v-else ref="loginGoogleMount" class="login-google-button" aria-label="Iniciar sesión con Google"></div>
      <div v-if="loginPending" class="login-loading" role="status">Validando cuenta Google…</div>
      <div v-if="loginError" class="login-warning" role="alert">{{loginError}}</div>
    </div>
  </div>
  <div v-else-if="providerPortalMode" class="provider-standalone">
    <ProviderPortal :email="loginEmail" :cases="myCases" :detail="activeCase"
      :presentations="mySharedPresentations" :presentation="selectedSharedPresentation" :busy="portalBusy"
      :error="portalError" :message="portalMessage" :can-return-to-admin="hasInstitution"
      @refresh="refreshPortal" @open-case="openCase" @close-case="activeCase=null"
      @open-presentation="openSharedPresentation" @close-presentation="selectedSharedPresentation=null"
      @complete="completeProviderPortalTask" @logout="logoutGoogle" @back-office="closeProviderPortal"/>
  </div>
  <div v-else class="shell">
    <aside class="sidebar">
      <div class="brand">
        <img src="/smart-wordmark.png" class="sidebar-smart-logo" alt="Smart" />
        <div class="sidebar-product-name"><strong>Smart Contract</strong><small>INTELLIGENCE PLATFORM</small></div>
      </div>
      <div class="nav-section">Workspace</div>
      <nav aria-label="Navegación principal">
        <button v-for="entry in visibleMenu" :key="entry.key" :class="{active:current===entry.key,'nav-ai':entry.key==='maira'}" @click="entry.key==='prestadores'?openProviderPortal():current=entry.key" :aria-current="current===entry.key?'page':undefined">
          <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
            <path v-for="(path,i) in iconPaths[entry.key]" :key="i" :d="path" />
          </svg>
          <span class="menu-title">{{entry.title}}</span>
        </button>
      </nav>
      <div class="sidebar-spacer"></div>
      <div class="sidebar-foot"><div class="foot-icon">SA</div><div><strong>Smart Alliance</strong><small>Plataforma multiempresa</small></div></div>
    </aside>
    <main class="main">
      <header class="top-header">
        <div><small>Workspace / Smart Contract / {{screenTitle}}</small><h1>{{screenTitle}}</h1></div>
        <div class="top-meta"><span class="top-product">Smart Contract · Primer flujo</span><span class="context-pill">Development</span><button type="button" class="logout-button" @click="logoutGoogle" title="Cerrar sesión Google">Salir</button></div>
      </header>
      <section v-if="current==='flujos'&&hasInstitution" class="stack">
        <div class="heading"><div><span class="eyebrow">Diseño inteligente de procesos</span><h2>Workflow Studio</h2><p>{{editingLinkedDraft?'Editando un diagrama guardado en '+editingLinkedDraft.partyName+'. Los cambios se conservan al guardar.':'Diseña y revisa un flujo antes de asociarlo o publicarlo.'}}</p></div><div class="header-actions"><button v-if="editingLinkedDraft" class="primary-button" :disabled="draftSaving" @click="saveLinkedWorkflowDraft">{{draftSaving?'Guardando…':'Guardar cambios · '+editingLinkedDraft.partyName}}</button><button class="primary-button" @click="studioTab='editor';openMairaDocumentImport()">✧ Crear con MAIRA</button><button class="ghost-button" @click="loadOriginalContractFlowDraft">Flujo original · 23 actividades</button><button class="ghost-button" @click="newWorkflow">＋ Nuevo flujo</button><button class="ghost-button" @click="fileInput?.click()">↥ Importar</button><button class="primary-button" @click="exportDraft">↧ Exportar JSON</button><button class="ghost-button" :disabled="portalBusy" @click="publishPilot">Publicar plantilla</button></div></div>

        <div class="workflow-mode-select" role="group" aria-label="Modo de visualización del proceso">
          <button type="button" :class="{active:studioTab==='pantallas'}" @click="studioTab='pantallas'">Vista operativa</button>
          <button type="button" :class="{active:studioTab==='editor'}" @click="studioTab='editor'">Diseñar workflow</button>
        </div>
        <div class="workflow-source-banner">
          <div><span class="eyebrow">PROCESO SELECCIONADO</span><strong>{{workflowName}}</strong>
            <small v-if="isOriginalFirstFlow">Documento original de 2 páginas · Roles y campos pendientes de confirmar</small>
            <small v-else>Borrador local · La vista muestra exactamente la definición seleccionada</small>
            <small v-if="editingLinkedDraft" class="linked-draft-caption">Asociado a {{editingLinkedDraft.partyName}} · Borrador editable</small></div>
          <div class="workflow-source-actions">
            <button type="button" class="ghost-button" @click="loadOriginalContractFlowDraft">Abrir flujo original</button>
            <button v-if="archivedPilotDraft" type="button" class="ghost-button" @click="openArchivedPilotDraft">Ver ejercicio anterior</button>
          </div>
        </div>
        <section v-if="studioTab==='pantallas'" class="workflow-front-preview">
          <div class="workflow-front-heading">
            <div><span class="eyebrow">Una definición · dos interfaces</span>
              <h3>Así se verá el proceso en la plataforma</h3>
              <p>La vista se actualiza con las actividades, campos y responsables del diseñador. No requiere expediente ni publicación.</p>
            </div>
            <div class="workflow-side-toggle" role="group" aria-label="Ver interfaz por participante">
              <button type="button" :class="{selected:previewSide==='CONTRATANTE'}" @click="previewSide='CONTRATANTE'">Contratante</button>
              <button type="button" :class="{selected:previewSide==='CONTRATISTA'}" @click="previewSide='CONTRATISTA'">Prestador</button>
            </div>
          </div>
          <WorkflowPresentation :workflow="definition()" :side="previewSide" />
          <section class="workflow-sharing">
            <div><h4>Compartir esta vista con un prestador</h4>
              <p>Selecciona un contacto registrado para mostrarle estas mismas pantallas en su portal. Se comparte una copia de solo lectura, no una contratación.</p>
            </div>
            <div class="workflow-sharing-actions">
              <select v-model="previewPartyId" aria-label="Prestador destinatario de la vista previa">
                <option value="">Seleccionar prestador autorizado</option>
                <option v-for="party in partyRecords.filter(p=>p.email)" :key="party.id" :value="party.id">{{party.name}} · {{party.email}}</option>
              </select>
              <button type="button" class="primary-button" :disabled="previewShareBusy||!previewPartyId" @click="shareWorkflowPreview">Compartir vista previa</button>
            </div>
            <p v-if="previewShareError" class="pilot-error" role="alert">{{previewShareError}}</p>
            <p v-if="previewShareMessage" class="pilot-success" role="status">{{previewShareMessage}}</p>
            <p v-if="!partyRecords.some(p=>p.email)" class="workflow-sharing-note">Para compartir la visualización, primero registra el contacto autorizado en Personas y empresas.</p>
          </section>
          <p class="workflow-preview-review">Este diseño tiene {{definition().nodes.length}} nodos. Sus responsabilidades y condiciones siguen sujetas a revisión mientras no estén validadas en el diseñador.</p>
        </section>


        <div v-if="mairaImportOpen" class="maira-import-surface" role="region" aria-label="Crear flujo a partir de documento con MAIRA">
          <div class="maira-import-head">
            <div><span class="eyebrow">Maira · Documento a proceso</span><h3>Crear proceso con Maira</h3><p v-if="mairaTargetParty">Vista previa para <strong>{{mairaTargetParty.name}}</strong> · {{mairaTargetParty.kind==='JURIDICA'?'Persona jurídica':'Persona natural'}}</p><p>Carga el diagrama. Maira propondrá tareas, responsabilidades y dependencias para revisión; no se activa un contrato automáticamente.</p></div>
            <button type="button" class="ghost-button" @click="mairaImportOpen=false" aria-label="Cerrar creación con MAIRA">Cerrar ×</button>
          </div>
          <div class="maira-import-grid">
            <div class="maira-import-card">
              <strong>1. Identificación y documento</strong>
              <p v-if="!mairaImportStatus" class="maira-import-warning">No se pudo verificar la disponibilidad de MAIRA.</p>
              <div v-else-if="!mairaImportStatus.ready" class="maira-import-warning" role="status">
                La prueba está preparada, pero aún requiere configurar
                <strong>{{!mairaImportStatus.google_enabled?'Google Sign-In':''}}{{!mairaImportStatus.google_enabled&&!mairaImportStatus.gemini_enabled?' y ':''}}{{!mairaImportStatus.gemini_enabled?'Gemini':''}}</strong>
                en Smart Contract. No se permite enviar archivos sin autorización.
              </div>
              <p class="maira-import-fine">Cuenta verificada: <strong>{{loginEmail}}</strong>. El análisis del documento usa esta sesión autorizada.</p>
              <label class="maira-file-label">Seleccionar diagrama de flujo
                <input type="file" :disabled="mairaImportBusy" accept=".pdf,.png,.jpg,.jpeg,.txt,application/pdf,image/png,image/jpeg,text/plain" @change="chooseMairaSource"/>
              </label>
              <div v-if="mairaSourceFile" class="maira-import-selected">{{mairaSourceFile.name}} · {{(mairaSourceFile.size/1024).toFixed(0)}} KB</div>
              <p class="maira-import-fine">PDF, imagen o TXT · Máximo 6 MB. Únicamente documentos sintéticos o autorizados. «Analizar con Maira» envía el archivo a Gemini; «Extraer pasos sin Gemini» lo procesa en Smart Contract. El archivo no se conserva.</p>
              <div class="pilot-actions">
                <button type="button" class="primary-button" :disabled="!mairaImportStatus?.ready||!mairaGoogleToken||!mairaSourceFile||mairaImportBusy" @click="analyzeMairaDocument">
                  {{mairaImportBusy?'Maira está analizando…':'Analizar documento con Maira'}}
                </button>
                <button type="button" class="ghost-button" :disabled="!mairaImportStatus?.ready||!mairaGoogleToken||mairaConnectionBusy||mairaImportBusy" @click="checkMairaConnection">
                  {{mairaConnectionBusy?'Diagnosticando…':'Diagnosticar modelos Gemini'}}
                </button>
                <button type="button" class="ghost-button" :disabled="!mairaImportStatus?.ready||!mairaGoogleToken||!mairaSourceFile||!(/\.pdf$/i.test(mairaSourceFile.name))||mairaImportBusy||mairaConnectionBusy"
                        @click="extractMairaPdfWithoutGemini">Extraer pasos sin Gemini</button>
              </div>
              <p v-if="mairaConnectionResult" class="maira-import-notice" role="status">{{mairaConnectionResult}}</p>
              <p class="maira-import-fine">La extracción sin Gemini recupera texto numerado, no interpreta flechas ni comprueba reglas. Requiere revisión humana.</p>
            </div>
            <div class="maira-import-card">
              <strong>2. Propuesta y vista previa</strong>
              <section v-if="mairaLiveHistory.length" class="maira-live" role="status" aria-live="polite">
                <div class="maira-live-head"><strong>Avance del análisis</strong><span>{{mairaClockDisplay(mairaSeconds)}} transcurridos</span></div>
                <div class="maira-live-main">
                  <div class="maira-progress-circle" :class="{'finished':mairaLivePhase==='TERMINADO','failed':mairaLivePhase==='ERROR'}"
                       role="progressbar" :aria-valuenow="mairaConfirmed" aria-valuemin="0" aria-valuemax="4" aria-label="Hitos confirmados del análisis">
                    <svg viewBox="0 0 120 120" aria-hidden="true">
                      <circle class="maira-circle-track" cx="60" cy="60" r="49"/>
                      <circle class="maira-circle-fill" cx="60" cy="60" r="49" :stroke-dasharray="mairaRingLength" :stroke-dashoffset="mairaRingOffset"/>
                      <circle v-if="mairaImportBusy" class="maira-circle-activity" cx="60" cy="60" r="49"/>
                    </svg>
                    <div class="maira-circle-number"><strong>{{mairaConfirmed}}/4</strong><span>hitos</span></div>
                  </div>
                  <div class="maira-live-description"><strong>{{mairaLiveLabel}}</strong>
                    <small>{{mairaImportBusy?'Procesando con seguimiento en vivo':'Último estado confirmado'}}</small>
                    <small v-if="mairaImportBusy">Solo avanza al terminar una etapa. Gemini no informa porcentajes internos.</small>
                  </div>
                </div>
                <div class="maira-live-milestones">
                  <div v-for="(stage,i) in mairaStages" :key="i" :class="{'complete':i<mairaConfirmed,'current':i===mairaConfirmed&&mairaImportBusy}">
                    <span>{{i<mairaConfirmed?'✓':i+1}}</span><strong>{{stage}}</strong>
                    <small>{{i<mairaConfirmed?'Confirmado':i===mairaConfirmed&&mairaImportBusy?'En curso':'Pendiente'}}</small>
                  </div>
                </div>
                <p v-if="mairaLiveHistory.some(x=>x.phase==='RECUPERACION'||x.phase==='REINTENTO')" class="maira-live-recovery">
                  {{mairaLiveHistory.filter(x=>x.phase==='RECUPERACION'||x.phase==='REINTENTO').slice(-1)[0]?.label}}
                </p>
              </section>
              <div v-if="mairaImportError" class="maira-import-error" role="alert">{{mairaImportError}}</div>
              <div v-if="mairaImportInfo" class="maira-import-notice" role="status">{{mairaImportInfo}}</div>
              <template v-if="mairaProposal">
                <section class="maira-dialogue" aria-label="Preguntas de MAIRA">
                  <div class="maira-dialogue-top"><div><span class="eyebrow">MAIRA · Definición guiada</span><strong>{{mairaQuestionsDone?'Respuestas registradas':'Necesito una respuesta antes de continuar'}}</strong></div>
                    <small>{{mairaAnsweredQuestions}} de {{mairaTotalQuestions}} respondidas</small>
                  </div>
                  <template v-if="mairaQuestionCursor<mairaTotalQuestions">
                    <p class="maira-dialogue-prompt">{{mairaCurrentQuestion}}</p>
                    <div v-if="mairaQuestionCursor===0" class="maira-dialogue-choices">
                      <button type="button" :class="{chosen:mairaIntent==='KEEP_ORIGINAL'}" @click="mairaIntent='KEEP_ORIGINAL';mairaQuestionError=''">Conservar el proceso original</button>
                      <button type="button" :class="{chosen:mairaIntent==='ADAPT_TO_ENTITY'}" @click="mairaIntent='ADAPT_TO_ENTITY';mairaQuestionError=''">Adaptarlo a la entidad</button>
                    </div>
                    <textarea v-else v-model="mairaAnswerText" rows="3" maxlength="650" class="maira-dialogue-input"
                      placeholder="Responde o indica qué información falta por definir." :aria-label="'Respuesta a pregunta '+(mairaQuestionCursor+1)"/>
                    <p v-if="mairaQuestionError" class="maira-dialogue-error" role="alert">{{mairaQuestionError}}</p>
                    <div class="maira-dialogue-actions">
                      <button v-if="mairaQuestionCursor>0" type="button" class="ghost-button" @click="mairaBack">Anterior</button>
                      <button type="button" class="primary-button" @click="mairaAnswer">{{mairaQuestionCursor===mairaTotalQuestions-1?'Registrar respuesta':'Responder y continuar'}}</button>
                    </div>
                  </template>
                  <div v-else class="maira-dialogue-done">
                    <strong>Decisiones vinculadas al borrador</strong>
                    <p>{{mairaIntent==='ADAPT_TO_ENTITY'?'Se utilizará el documento como referencia para adaptar el proceso.':'Se conservará el alcance original del documento.'}} No se han cambiado automáticamente las actividades ni las asignaciones.</p>
                    <button type="button" class="ghost-button" @click="mairaQuestionCursor=0;mairaAnswerText='';mairaQuestionError=''">Revisar respuestas</button>
                  </div>
                </section>
                <div class="maira-import-metrics"><span><b>{{mairaProposal.node_count}}</b> nodos</span><span><b>{{mairaProposal.mapped_steps}}</b> pasos identificados</span><span><b>{{mairaTotalQuestions}}</b> preguntas de MAIRA</span></div>
                <div class="maira-preview-card">
                  <strong>{{sourceOnlyPreview?'Actividades recuperadas del documento original':'Así se distribuirían las actividades '+(mairaTargetParty?'para '+mairaTargetParty.name:'')}}</strong>
                  <p v-if="sourceOnlyPreview" class="maira-preview-alert">Extracción textual sin Gemini. Los responsables provienen del PDF, no son asignaciones aprobadas para {{mairaTargetParty?.name||'la institución'}}. Las conexiones son provisionales.</p>
                  <p class="maira-import-fine">Las responsabilidades son una propuesta. No se inventan campos o documentos que no figuren en el diagrama.</p>
                  <div v-if="!sourceOnlyPreview" class="maira-preview-summary">
                    <span><b>{{mairaPreviewStages.filter(s=>s.side==='CONTRATISTA').length}}</b> Del contratista</span>
                    <span><b>{{mairaPreviewStages.filter(s=>s.side==='CONTRATANTE').length}}</b> Del contratante</span>
                    <span><b>{{mairaPreviewStages.filter(s=>s.side==='REVISAR').length}}</b> Por definir</span>
                  </div>
                  <div v-else class="maira-preview-summary"><span><b>{{mairaPreviewStages.length}}</b> actividades del documento</span><span>Roles por revisar</span><span>Dependencias provisionales</span></div>
                  <div class="maira-preview-tasks">
                    <div v-for="stage in mairaPreviewStages" :key="stage.id" class="maira-preview-task">
                      <span class="maira-preview-number">{{stage.step}}</span>
                      <div><strong>{{stage.label}}</strong><small v-if="sourceOnlyPreview">Responsable original: {{stage.role}} · Asignación institucional no verificada</small><small v-else>{{stage.role}} · {{stage.side==='CONTRATISTA'?'Contratista (propuesto)':stage.side==='CONTRATANTE'?'Contratante (propuesto)':'Por definir · no asignado'}}</small>
                        <small>Origen: {{stage.source}}{{stage.page?' · Página '+stage.page:''}}</small>
                        <small v-if="sourceOnlyPreview">Conexión provisional por numeración: {{stage.dependencies.join(', ')||'Inicio'}} · Validar flechas</small>
                        <small v-else>Depende de: {{stage.dependencies.join(', ')||'Inicio'}}</small></div>
                    </div>
                  </div>
                  <p v-if="mairaTargetParty?.kind==='JURIDICA'&&mairaPreviewStages.some(s=>s.role==='ASPIRANTE')" class="maira-preview-alert">El documento identifica actividades de un aspirante. Antes de asignarlas a una empresa, valida si aplican al hospital o a un representante autorizado.</p>
                </div>
                <div v-if="mairaProposal.observations.length"><strong>Observaciones</strong><p v-for="(item,i) in mairaProposal.observations" :key="i">• {{item}}</p></div>
                <div class="pilot-actions">
                  <button v-if="mairaTargetParty" type="button" class="primary-button" :disabled="mairaPreviewSaving" @click="saveMairaPreview">{{mairaPreviewSaving?'Guardando…':sourceOnlyPreview?'Guardar borrador sin aprobar en '+mairaTargetParty.name:'Guardar vista previa en '+mairaTargetParty.name}}</button>
                  <button type="button" class="ghost-button" :disabled="!mairaQuestionsDone" @click="applyMairaProposal">Editar workflow de {{mairaProposal.mapped_steps}} actividades</button>
                </div>
                <p class="maira-import-fine">El diagrama muestra el proceso generado, no la plantilla del piloto. Al abrirlo en el diseñador sustituye el borrador local; puedes exportar el borrador actual antes de hacerlo.</p>
              </template>
              <p v-else class="maira-import-fine">MAIRA mostrará aquí el mapeo de pasos originales a etapas, dependencias, dudas y observaciones. Nada se aplica sin tu revisión.</p>
            </div>
          </div>
        </div>

          <section v-if="mairaProposal" class="maira-workflow-visual" aria-label="Workflow generado por MAIRA">
            <div class="maira-workflow-visual-head">
              <div>
                <span class="eyebrow">Workflow propuesto · Borrador no publicado</span>
                <h3>Diagrama generado a partir del documento</h3>
                <p>{{mairaProposal.mapped_steps}} actividades · {{mairaProposal.node_count}} nodos · {{mairaProposal.workflow.edges.length}} conexiones propuestas</p>
              </div>
              <button type="button" class="primary-button" :disabled="!mairaQuestionsDone" @click="applyMairaProposal">Abrir workflow en diseñador</button>
            </div>
            <div class="maira-workflow-visual-canvas">
              <div v-if="mairaGraphReviewQuestions.length" class="maira-flow-questions" aria-label="Preguntas señaladas en el diagrama">
                <div class="maira-flow-questions-title">
                  <strong>Preguntas pendientes en este proceso ({{mairaGraphReviewQuestions.length}})</strong>
                  <span>No son decisiones de ejecución hasta validar sus condiciones y ramas.</span>
                </div>
                <div class="maira-flow-questions-items">
                  <div v-for="(item,i) in mairaGraphReviewQuestions" :key="'graph-question-'+i" class="maira-flow-question">
                    <span class="maira-flow-question-icon">?</span>
                    <div><strong>{{item.text}}</strong>
                      <small v-if="item.context" class="maira-flow-question-context">Hallazgo de MAIRA: {{item.context}}</small>
                      <small v-if="item.steps.length">Relacionada con términos originales de los pasos {{item.steps.join(', ')}}. Esta coincidencia no valida las conexiones.</small>
                      <small v-else>Consulta general del proceso · sin referencia textual inequívoca a un paso</small>
                    </div>
                  </div>
                </div>
              </div>
              <div class="maira-workflow-map-body">
                <VueFlow :key="'maira-map-'+mairaDiagramVersion" id="maira-generated-diagram"
                         :nodes="mairaDiagram.nodes" :edges="mairaDiagram.edges" :fit-view-on-init="true"
                         :nodes-draggable="false" :nodes-connectable="false" :edges-updatable="false"
                         :min-zoom="0.22" :max-zoom="1.7" :elements-selectable="true"/>
              </div>
            </div>
            <p v-if="mairaGraphReviewQuestions.length" class="maira-review-graphic-disclaimer">
              MAIRA identificó {{mairaGraphReviewQuestions.length}} pregunta(s) de revisión y
              {{mairaVerifiedBranchCount}} decisión(es) con más de una salida en el workflow propuesto.
              Una pregunta pendiente no crea por sí sola una bifurcación.
            </p>
            <p class="maira-workflow-visual-note">Las conexiones representan el workflow propuesto por MAIRA. Debes confirmar las flechas, responsables y condiciones con el documento original antes de publicar.</p>
          </section>
        <input ref="fileInput" type="file" accept="application/json,.json" class="hidden-input" @change="importDraft" />
        <div v-show="studioTab==='editor'" class="workflow-meta">
          <label>Nombre del proceso<input v-model="workflowName" maxlength="200" aria-label="Nombre del proceso" /></label>
          <label>Identificador<input v-model="workflowKey" maxlength="120" aria-label="Identificador del proceso" /></label>
          <label>Modalidad <span class="field-hint">opcional</span><input v-model="modalityKey" placeholder="Definida por la entidad" maxlength="120" aria-label="Modalidad configurable" /></label>
        </div>
        <div v-show="studioTab==='editor'" class="studio-layout">
          <div class="studio-catalog">
            <div class="panel-title"><strong>Componentes</strong><button class="tiny-link" @click="loadOriginalContractFlowDraft">Restaurar flujo original</button></div>
            <p class="panel-caption">Selecciona una etapa y agrega bloques a su recorrido.</p>
            <div v-if="showCatalog" class="catalog-scroll">
              <div v-for="category in categories" :key="category" class="catalog-group"><span class="group-label">{{category}}</span>
                <button v-for="block in blocks.filter(b=>b.category===category)" :key="block.kind" class="block-button" @click="addBlock(block.kind)"><span class="block-glyph">{{block.glyph}}</span><span>{{block.title}}</span><span class="plus">+</span></button>
              </div>
            </div>
          </div>
          <div class="diagram-panel">
            <div class="panel-title studio-visual-header">
              <div><strong>Diagrama del proceso</strong><small>{{guidedActivities.length}} actividades · {{edges.length}} conexiones</small></div>
              <div class="studio-view-switch" role="group" aria-label="Modo de edición del diagrama">
                <button type="button" :class="{selected:studioCanvasMode==='guided'}" @click="studioCanvasMode='guided'">Recorrido</button>
                <button type="button" :class="{selected:studioCanvasMode==='canvas'}" @click="studioCanvasMode='canvas'">Lienzo</button>
              </div>
            </div>
            <div v-if="studioCanvasMode==='guided'" class="guided-flow" role="region" aria-label="Recorrido editable">
              <div class="guided-flow-helper">
                <div><strong>Recorrido del proceso</strong><p>Selecciona una actividad para editarla en el panel de propiedades. El recorrido conserva las conexiones del workflow.</p></div>
                <span>Página {{guidedCurrentPage+1}} de {{guidedPages}}</span>
              </div>
              <div v-if="!guidedVisible.length" class="guided-flow-empty">No hay actividades. Agrégalas desde el catálogo.</div>
              <div v-for="(step,i) in guidedVisible" :key="step.id" class="guided-flow-row">
                <button type="button" :class="['guided-flow-card',{active:selectedId===step.id}]"
                  :aria-pressed="selectedId===step.id" @click="selectGuidedStage(step.id)">
                  <span class="guided-flow-index">{{guidedCurrentPage*guidedPageSize+i+1}}</span>
                  <span class="guided-flow-card-copy">
                    <strong>{{(step.data as WorkNode).label}}</strong>
                    <small>{{guidedStageLabel(step)}} · {{(step.data as WorkNode).role||'Responsable no definido'}}</small>
                  </span>
                  <span class="guided-flow-owner">{{guidedSide(step)}}</span>
                  <span class="guided-flow-edit">Editar</span>
                </button>
                <div v-if="i<guidedVisible.length-1" class="guided-flow-connector"
                  :class="{uncertain:!guidedHasDirectEdge(step.id,guidedVisible[i+1].id)}" aria-hidden="true">
                  <span>{{guidedHasDirectEdge(step.id,guidedVisible[i+1].id)?'↓':'⋯'}}</span>
                </div>
              </div>
              <div class="guided-flow-foot">
                <span>Inicio <template v-if="guidedCurrentPage>0">· Continúa de la página anterior</template></span>
                <span>Fin del proceso al completar todas las etapas</span>
              </div>
            </div>
            <div v-else class="canvas-area studio-canvas-readable">
              <div class="studio-map-tools studio-map-switch">
                <strong>{{freeformMode?'Editor técnico':'Workflow editable'}} · {{guidedOrderedNodes.length}} nodos</strong>
                <span>{{freeformMode?'Editor alternativo de enlaces y posiciones.':'Puedes mover las etapas y el lienzo directamente.'}}</span>
                <button type="button" @click="freeformMode=!freeformMode">{{freeformMode?'Volver al workflow':'Editor técnico'}}</button>
              </div>
              <CompactWorkflowDiagram v-if="!freeformMode"
                :ordered-nodes="guidedOrderedNodes" :edges="edges"
                :manual-positions="compactSavedPositions"
                :selected-node-id="selectedId" :selected-edge-id="selectedEdgeId"
                @select-node="selectGuidedStage" @select-edge="selectCompactEdge"
                @move-node="onCompactMove" @organize="organizeCompactLayout"
                @connect="connectCompactNodes"/>
              <VueFlow v-else :key="'studio-'+studioDiagramVersion" v-model:nodes="nodes"
                v-model:edges="edges" :fit-view-on-init="false"
                :default-viewport="{x:90,y:35,zoom:0.9}"
                :nodes-connectable="true" :nodes-draggable="true" :elements-selectable="true"
                :pan-on-scroll="true" :zoom-on-scroll="false" :zoom-on-pinch="true"
                :min-zoom="0.55" :max-zoom="1.6" @connect="onConnect"
                @node-click="({node}) => {selectedId=node.id;selectedEdgeId=null}"
                @edge-click="({edge}) => {selectedEdgeId=edge.id;selectedId=null}"
                @node-drag-stop="onNodeDragStop"
                @pane-click="() => {selectedId=null;selectedEdgeId=null}" />
            </div>
            <div class="canvas-footer">
              <span v-if="studioCanvasMode==='guided'">Selecciona cada etapa y edita su nombre, responsable, campos y condiciones a la derecha.</span>
              <span v-else>Mueve etapas y fondo directamente · Guarda cambios para conservar el diseño</span>
              <div class="canvas-buttons" v-if="studioCanvasMode==='guided'">
                <button type="button" :disabled="guidedCurrentPage===0" @click="changeGuidedPage(guidedCurrentPage-1)">Anterior</button>
                <button type="button" :disabled="guidedCurrentPage>=guidedPages-1" @click="changeGuidedPage(guidedCurrentPage+1)">Siguiente</button>
              </div>
              <div class="canvas-buttons" v-else>
                <button @click="validateDraft">Verificar</button><button @click="simulateDraft">Simular</button>
              </div>
            </div>
          </div>
          <div class="inspector-panel">
            <div class="panel-title"><strong>Propiedades</strong><span class="inspector-icon">⚙</span></div>
            <template v-if="selectedData">
              <p class="panel-caption">{{stageLabel}}</p>
              <div v-if="selectedData.config?.source_step" class="maira-source-evidence">
                <strong>Origen del documento · Paso {{selectedData.config.source_step}}</strong>
                <p>{{selectedData.config.source_excerpt||'Sin cita disponible'}}</p>
                <span>Fuente MAIRA{{selectedData.config.source_page?' · Página '+selectedData.config.source_page:''}}{{selectedData.config.source_confidence?' · Confianza '+selectedData.config.source_confidence:''}} · Revisión humana requerida</span>
                <span v-if="selectedData.config.party_scope_pending" class="maira-evidence-warning">Este responsable del PDF no equivale a Hospital Smart. Asigna el ejecutor antes de publicar.</span>
              </div>
              <label class="inspector-field">Nombre de la etapa<input :value="selectedData.label" maxlength="200" @input="editNode('label',($event.target as HTMLInputElement).value)" /></label>
              <label class="inspector-field">Tipo de componente<input :value="blocks.find(b=>b.kind===selectedData?.kind)?.title||selectedData.kind" disabled /></label>
              <label class="inspector-field">Responsable<input list="roles-contrato" :value="selectedData.role||''" placeholder="Selecciona o escribe otro rol" maxlength="120" @input="editNode('role',($event.target as HTMLInputElement).value)"/><datalist id="roles-contrato"><option v-for="role in roles" :key="role" :value="role" /></datalist></label>
              <label v-if="selectedData.kind!=='START'&&selectedData.kind!=='END'" class="inspector-field">Ejecuta la actividad<select :value="selectedData.config?.actor_side||'REVISAR'" @change="editNode('actorSide',($event.target as HTMLSelectElement).value)"><option value="REVISAR">Por definir · no asignado</option><option value="CONTRATANTE">Entidad contratante</option><option value="CONTRATISTA">Contratista / prestador</option></select></label>
              <label class="inspector-field">Clasificación<select :value="selectedData.policy" @change="editNode('policy',($event.target as HTMLSelectElement).value)"><option v-for="p in policies" :key="p.value" :value="p.value">{{p.label}}</option></select></label>
              <label class="inspector-field">Campo de condición <span class="field-hint">opcional</span><input :value="selectedData.when?.field||''" placeholder="Ej. contract.requires_policy" @input="editNode('conditionField',($event.target as HTMLInputElement).value)" /></label>
              <label v-if="selectedData.when?.field" class="inspector-field">Operador<select :value="selectedData.when?.op||'eq'" @change="editNode('conditionOperator',($event.target as HTMLSelectElement).value)"><option v-for="op in conditionOperators" :key="op.value" :value="op.value">{{op.label}}</option></select></label>
               <label v-if="selectedData.when?.field&&selectedData.when?.op!=='exists'" class="inspector-field">Valor esperado<input :value="conditionValueText(selectedData.when?.value)" placeholder="true, 150000000 o [1,2]" @input="editNode('conditionValue',($event.target as HTMLInputElement).value)" /></label>
              <label class="inspector-field">Modo de ejecución<select :value="selectedData.config?.execution_mode||'MANUAL'" @change="editNode('executionMode',($event.target as HTMLSelectElement).value)"><option v-for="mode in executionModes" :key="mode.value" :value="mode.value">{{mode.label}}</option></select></label>
               <label class="inspector-field">Instrucciones<textarea :value="selectedData.config?.instructions||''" rows="3" placeholder="Describe qué debe verificarse o solicitarse" @input="editNode('instructions',($event.target as HTMLTextAreaElement).value)"></textarea></label>
               <div class="field-editor"><div class="field-title"><strong>Campos configurables</strong><button @click="addField">+ Agregar</button></div><p class="panel-caption">Define los datos que recopilará esta etapa.</p>
                 <div v-for="(field,i) in selectedData.config?.fields||[]" :key="i" class="field-card">
                   <div class="field-card-head"><strong>Campo {{i+1}}</strong><button @click="removeField(i)" aria-label="Eliminar campo">Eliminar</button></div>
                   <label>Nombre<input :value="field.label" maxlength="120" @input="editField(i,'label',($event.target as HTMLInputElement).value)" /></label>
                   <label>Identificador<input :value="field.key" maxlength="120" @input="editField(i,'key',($event.target as HTMLInputElement).value)" /></label>
                   <label>Tipo<select :value="field.type" @change="editField(i,'type',($event.target as HTMLSelectElement).value)"><option v-for="type in fieldTypes" :key="type" :value="type">{{type}}</option></select></label>
                   <label class="field-required"><input type="checkbox" :checked="field.required" @change="editField(i,'required',($event.target as HTMLInputElement).checked)"/> Obligatorio</label>
                 </div>
               </div>
               <div class="field-editor"><div class="field-title"><strong>Conexiones</strong></div>
                 <div v-for="edge in incidentEdges" :key="edge.id" class="edge-row"><span>{{labelFor(edge.source)}} → {{labelFor(edge.target)}}</span><button @click="removeEdge(edge.id)" aria-label="Quitar conexión">×</button></div>
               </div>
              <div class="switch-row"><div><strong>Etapa activa</strong><small>Solo opcionales o condicionales</small></div><input type="checkbox" :checked="selectedData.enabled" :disabled="['LEGAL_LOCKED','ORG_REQUIRED'].includes(selectedData.policy)" @change="editNode('enabled',($event.target as HTMLInputElement).checked)" /></div>
              <button v-if="!['START','END'].includes(selectedData.kind) && !['LEGAL_LOCKED','ORG_REQUIRED'].includes(selectedData.policy)" class="delete-button" @click="removeNode">Eliminar etapa</button>
            </template>
            <template v-else-if="selectedEdge">
               <p class="panel-caption">Conexión entre etapas</p>
               <div class="edge-label">{{labelFor(selectedEdge.source)}} → {{labelFor(selectedEdge.target)}}</div>
               <label class="inspector-field">Condición de ruta (campo)<input :value="selectedEdgeCondition?.field||''" placeholder="Ej. acuerdo.requires_approval" @input="editEdge('field',($event.target as HTMLInputElement).value)" /></label>
               <label v-if="selectedEdgeCondition?.field" class="inspector-field">Operador<select :value="selectedEdgeCondition?.op||'eq'" @change="editEdge('operator',($event.target as HTMLSelectElement).value)"><option v-for="op in conditionOperators" :key="op.value" :value="op.value">{{op.label}}</option></select></label>
               <label v-if="selectedEdgeCondition?.field&&selectedEdgeCondition?.op!=='exists'" class="inspector-field">Valor<input :value="conditionValueText(selectedEdgeCondition?.value)" @input="editEdge('value',($event.target as HTMLInputElement).value)" /></label>
               <button class="delete-button" @click="removeEdge(selectedEdge.id)">Quitar conexión</button>
             </template>
             <div v-else class="select-message"><div>◇</div><p>Selecciona una etapa o conexión para configurar sus datos y reglas.</p></div>
          </div>
        </div>
        <details v-if="studioTab==='editor'&&sourceReviewRequired" class="maira-review-gate studio-review-details">
          <summary><span>Revisión del documento · {{studioReviewQuestions.length}} aclaraciones pendientes</span><small>Expandir preguntas y confirmar responsables</small></summary>
          <div class="studio-review-detail-body">
          <strong>Revisión documental obligatoria</strong>
          <p>El proceso conserva los datos del documento, pero no verifica automáticamente los responsables ni las flechas. Comprueba cada etapa en el diseñador antes de confirmar.</p>
          <div v-if="isOriginalFirstFlow" class="original-review-form">
            <div class="original-review-heading"><strong>Definiciones pendientes · Primer flujo</strong><span>Fuente: Ciclo de contratación v2 · PDF</span></div>
            <p>MAIRA necesita estas definiciones para completar la configuración del primer proceso. Las respuestas quedan en el borrador; no activan contrataciones.</p>
            <label>¿Qué alcance tendrá el procedimiento?
              <select v-model="originalScopeChoice">
                <option value="">Seleccionar</option>
                <option value="KEEP_ORIGINAL">Conservar el procedimiento fuente</option>
                <option value="ADAPT_TO_ENTITY">Adaptarlo para una configuración específica</option>
              </select>
            </label>
            <label v-for="(question,index) in studioReviewQuestions" :key="index">
              <span>{{index+1}}. {{question}}</span>
              <textarea :value="originalClarificationAnswers[question]||''" rows="2" maxlength="650"
                 placeholder="Respuesta o información por confirmar"
                 @input="originalClarificationAnswers={...originalClarificationAnswers,[question]:($event.target as HTMLTextAreaElement).value}"></textarea>
            </label>
            <button class="ghost-button" type="button" @click="saveOriginalFlowClarifications">
              Registrar aclaraciones del caso
            </button>
            <span v-if="studioMairaDialogue?.completed" class="original-review-complete">Aclaraciones registradas para este borrador. Debes verificar las tareas y los roles antes de cualquier publicación.</span>
          </div>
          <p v-if="studioMairaDialogue?.completed" class="maira-dialogue-record">MAIRA registró {{studioMairaDialogue.questions_total}} decisiones. Alcance: {{studioMairaDialogue.scope_decision==='ADAPT_TO_ENTITY'?'Adaptar a la entidad':'Conservar el proceso original'}}. Las respuestas no modifican automáticamente el workflow.</p>
          <label><input type="checkbox" v-model="reviewRolesConfirmed" /> Revisé responsables, contratante/contratista y pertinencia para esta persona o empresa.</label>
          <label><input type="checkbox" v-model="reviewRoutesConfirmed" /> Revisé las dependencias, secuencia y condiciones contra el diagrama original.</label>
          <div class="pilot-actions">
            <button type="button" class="ghost-button" :disabled="!reviewRolesConfirmed||!reviewRoutesConfirmed" @click="confirmSourceReview">Confirmar revisión del borrador</button>
            <span v-if="sourceReviewConfirmed" class="maira-review-ok">Revisión registrada para esta versión. Si editas el flujo, habrá que confirmar de nuevo.</span>
            <span v-else class="maira-review-pending">Publicación bloqueada hasta completar la revisión.</span>
          </div>
          </div>
        </details>
        <div v-if="studioTab==='editor'&&simulationVisible" class="simulation-panel"><div class="panel-title"><strong>Simulación de recorrido</strong><button class="tiny-link" @click="simulationVisible=false">Cerrar</button></div><p class="panel-caption">Datos de ejemplo en JSON; indica etapas completadas separadas por coma. Esta prueba es local y no ejecuta tareas.</p>
          <div class="simulation-fields"><label>Datos del expediente (JSON)<textarea v-model="simulationFacts" rows="3" spellcheck="false"/></label><label>Identificadores completados<input v-model="simulationCompleted" placeholder="inicio, documentos"/></label><button class="primary-button" @click="simulateDraft">Ejecutar simulación</button></div>
          <p v-if="simulationError" class="validation-list">{{simulationError}}</p>
          <div class="simulation-results"><div v-for="(status,id) in simulationStatuses" :key="id" class="simulation-item"><span>{{labelFor(String(id))}}</span><strong>{{status}}</strong></div></div>
        </div>
        <div v-if="flowMessage" class="status-message" role="status">{{flowMessage}}</div>
        <div v-if="errors.length" class="validation-list"><strong>Observaciones del flujo</strong><p v-for="(err,i) in errors" :key="i">{{err}}</p></div>
        <div v-show="studioTab==='editor'" class="summary-strip"><span>{{nodeCount}} etapas · {{edges.length}} conexiones · {{policyCount}} protegidas</span><span>Borrador guardado en este navegador{{lastSavedAt?' · '+lastSavedAt:''}}. Para compartirlo, usa Exportar. La publicación institucional requiere inicio de sesión.</span></div>
      </section>
      <section v-else-if="current==='resumen'" class="overview">
        <div class="summary-hero">
          <div class="hero-copy">
            <span class="eyebrow">PLATAFORMA DE INTELIGENCIA CONTRACTUAL</span>
            <h2>El futuro de la contratación se diseña aquí.</h2>
            <p>Construye procesos adaptativos, controla sus dependencias y prepara un ciclo contractual inteligente con MAIRA. Una arquitectura para múltiples instituciones.</p>
            <div class="hero-actions">
              <button class="primary-button" @click="current='flujos'">Abrir Workflow Studio <span aria-hidden="true">↗</span></button>
              <button class="ghost-button" @click="current='maira'">Conocer MAIRA</button>
            </div>
          </div>
          <div class="hero-visual" aria-hidden="true">
            <div class="hero-orbit"></div><div class="hero-orbit orbit-two"></div>
            <div class="hero-core"><strong class="hero-core-name">MAIRA</strong><span class="hero-core-caption">AI AGENT</span></div>
            <span class="hero-chip chip-top">◇ Workflows adaptativos</span>
            <span class="hero-chip chip-bottom">✧ Inteligencia contractual</span>
          </div>
        </div>
        <div class="overview-heading">
          <div><h3>Centro de control</h3><p>Indicadores del borrador que estás diseñando en este navegador.</p></div>
          <span class="section-tag">Borrador local · Sin contratos reales</span>
        </div>
        <div class="stat-grid">
          <div class="metric-card"><div class="metric-label"><span>ETAPAS DEL FLUJO</span><span class="metric-dot">◇</span></div><strong>{{nodeCount}}</strong><span class="metric-foot">Componentes del diseño actual</span></div>
          <div class="metric-card violet"><div class="metric-label"><span>ETAPAS ACTIVAS</span><span class="metric-dot">✓</span></div><strong>{{activeCount}}</strong><span class="metric-foot">Configuradas para participar</span></div>
          <div class="metric-card aqua"><div class="metric-label"><span>DEPENDENCIAS</span><span class="metric-dot">⇄</span></div><strong>{{activeDependencyCount}}</strong><span class="metric-foot">Conexiones entre etapas</span></div>
          <div class="metric-card green"><div class="metric-label"><span>CONTROLES PROTEGIDOS</span><span class="metric-dot">▣</span></div><strong>{{policyCount}}</strong><span class="metric-foot">Restricciones del borrador</span></div>
        </div>
        <div class="dashboard-lower">
          <div class="dashboard-panel">
            <div class="dashboard-panel-head"><div><h3>Proceso en diseño</h3><p class="panel-lead">Continúa desde la estructura que tienes abierta.</p></div><span class="status-pill">NO PUBLICADO</span></div>
            <div class="draft-summary"><div class="draft-symbol">◇</div><div><strong>{{workflowName}}</strong><small>{{workflowKey}} · Diseño editable en el navegador</small></div></div>
            <div class="mini-kpi-row"><span><b>{{nodeCount}}</b> etapas</span><span><b>{{activeCount}}</b> activas</span><span><b>{{edges.length}}</b> conexiones</span><span><b>{{catalogCount}}</b> componentes disponibles</span></div>
            <button class="dashboard-link" @click="current='flujos'">Continuar configurando <span aria-hidden="true">↗</span></button>
          </div>
          <div class="dashboard-panel">
            <div class="dashboard-panel-head"><div><h3>Maira Intelligence</h3><p class="panel-lead">Asistente de inteligencia contractual.</p></div><span class="status-pill">{{mairaImportStatus?.ready?'GEMINI CONFIGURADO':mairaImportStatus?'CONFIGURACIÓN PENDIENTE':'VERIFICANDO'}}</span></div>
            <div class="intelligence-status"><div class="intelligence-glyph">✧</div><div><strong>MAIRA · Contract Intelligence Agent</strong><small>Multi-tenant AI for Intelligent Review &amp; Agreements</small></div></div>
            <p class="status-line">{{mairaImportStatus?.ready?'Gemini está configurado en Smart Contract. Falta comprobar la primera interpretación real de un documento.':'La interpretación de documentos requiere configurar Gemini en la API. Puedes continuar diseñando flujos manualmente.'}}</p>
            <button class="dashboard-link" @click="current=mairaImportStatus?.ready?'personas':'maira'">{{mairaImportStatus?.ready?'Crear proceso con Maira desde Personas y empresas':'Revisar Maira'}} <span aria-hidden="true">↗</span></button>
          </div>
        </div>
      </section>
      <section v-else-if="current==='maira'" class="overview">
        <div class="maira-hero maira-identity-layout">
          <div class="maira-identity-card" aria-label="MAIRA, agente de inteligencia contractual">
            <div class="maira-identity-rings">
              <div class="maira-identity-circle">
                <strong>MAIRA</strong>
                <span>AI AGENT</span>
              </div>
            </div>
            <p class="maira-identity-tagline">Contract Intelligence</p>
          </div>
          <div class="maira-identity-copy">
            <span class="eyebrow">SMART CONTRACT · AGENTE DE INTELIGENCIA CONTRACTUAL</span>
            <h2>MAIRA</h2>
            <p class="maira-full-name">Multi-tenant AI for Intelligent Review &amp; Agreements</p>
            <p class="maira-es-meaning">Inteligencia artificial multiempresa para revisión inteligente y acuerdos contractuales.</p>
            <p class="maira-introduction">{{mairaImportStatus?.ready?'Maira puede recibir documentos para generar propuestas de workflows. La primera solicitud a Gemini sigue pendiente de verificación.':'Maira prepara propuestas de workflows a partir de documentos. Para analizarlos, primero debe habilitarse Gemini en la API.'}}</p>
            <span class="status-pill">{{mairaImportStatus?.ready?'GEMINI CONFIGURADO · PENDIENTE PRUEBA':mairaImportStatus?'GEMINI NO CONFIGURADO':'COMPROBANDO CONFIGURACIÓN'}}</span>
          </div>
        </div>
        <div class="overview-heading"><div><h3>Capacidades de Maira</h3><p>El análisis documental propone flujos para revisión humana; no ejecuta contratos ni firmas.</p></div></div>
        <div class="capability-grid">
          <div v-for="(cap,i) in [{name:'Comprender',desc:'Interpretar manuales, necesidades y documentos.'},{name:'Configurar',desc:'Proponer bloques, campos y reglas de procesos.'},{name:'Analizar',desc:'Identificar inconsistencias y controles pendientes.'},{name:'Acompañar',desc:'Guiar la ejecución contractual paso a paso.'}]" :key="cap.name" class="capability-card">
            <span class="number">0{{i+1}}</span><h3>{{cap.name}}</h3><p>{{cap.desc}}</p>
          </div>
        </div>
        <div class="status-panel"><div><strong>{{mairaImportStatus?.ready?'Preparado para analizar el primer documento':'Workflow Studio disponible'}}</strong><p>{{mairaImportStatus?.ready?'Selecciona Hospital Smart en Personas y empresas y pulsa Crear proceso con Maira. El resultado requerirá validación antes de publicar.':'Puedes diseñar flujos manualmente mientras se configura Gemini.'}}</p></div><div class="pilot-actions"><button class="ghost-button" @click="loadMairaImportStatus">Actualizar estado</button><button class="ghost-button" @click="current=mairaImportStatus?.ready?'personas':'flujos'">{{mairaImportStatus?.ready?'Ir a Personas y empresas':'Abrir Studio'}} ↗</button></div></div>
      </section>

      <section v-else-if="current==='personas'&&hasInstitution" class="contract-space">
        <div class="contract-hero"><div><span class="eyebrow">SMART CONTRACT · DIRECTORIO</span><h2>Personas y empresas</h2><p>Consulta los procesos y expedientes asociados a cada persona o empresa.</p></div><div class="pilot-actions"><button class="ghost-button" @click="refreshPortal">Actualizar</button><button class="primary-button" @click="showNewPartyForm=!showNewPartyForm">{{showNewPartyForm?'Cerrar registro':'＋ Nuevo registro'}}</button></div></div>
        <div class="pilot-notice">Los flujos guardados y los expedientes son elementos distintos. Abre una ficha para consultar lo existente; crear algo nuevo es opcional.</div>
        <div v-if="portalError" class="pilot-error" role="alert">{{portalError}}</div><div v-if="portalMessage" class="pilot-success" role="status">{{portalMessage}}</div>

        <div class="pilot-panel party-directory-panel">
          <div class="pilot-directory-header"><div><h3>Personas y empresas <span class="pilot-count">{{partyRecords.length}}</span></h3>
            <p class="pilot-muted">Abre un registro para consultar sus flujos, vistas previas y expedientes.</p></div>
            <input v-if="partyRecords.length" v-model="partySearch" type="search" placeholder="Buscar persona o empresa" aria-label="Buscar persona o empresa"/>
          </div>
          <div v-if="!filteredParties.length" class="pilot-empty">{{partyRecords.length?'No hay registros para esta búsqueda.':'Todavía no hay personas o empresas registradas.'}}</div>
          <div v-for="party in filteredParties" :key="party.id" class="party-directory-card">
            <div class="party-directory-summary">
              <div class="party-directory-identity">
                <strong>{{party.name}}</strong>
                <small>{{party.kind==='JURIDICA'?'Persona jurídica':'Persona natural'}} · {{party.email||'Sin correo de contacto'}}</small>
                <div class="party-directory-stats">
                  <span>{{party.process_count||0}} {{party.process_count===1?'flujo registrado':'flujos registrados'}}</span>
                  <span>{{party.case_count}} {{party.case_count===1?'expediente':'expedientes'}}</span>
                </div>
                <p v-if="party.latest_process" class="party-directory-latest"><b>Último flujo:</b> {{party.latest_process.name}} · {{processTypeLabel(party.latest_process)}}</p>
                <p v-else class="party-directory-latest">Aún no hay procesos guardados en este registro.</p>
              </div>
              <button type="button" class="primary-button" :aria-expanded="expandedPartyId===party.id"
                :disabled="partyPortfolioBusy&&expandedPartyId===party.id" @click="togglePartyRecord(party)">
                {{expandedPartyId===party.id?'Cerrar ficha':'Abrir ficha'}}
              </button>
            </div>
            <div v-if="expandedPartyId===party.id" class="party-record-detail">
              <p v-if="partyPortfolioBusy" class="pilot-muted">Cargando procesos y expedientes de {{party.name}}…</p>
              <template v-else-if="partyPortfolio?.party.id===party.id">
                <div class="party-record-section">
                  <h4>Flujos y vistas previas <span>{{partyPortfolio.processes.length}}</span></h4>
                  <div v-if="!partyPortfolio.processes.length" class="party-record-empty">No hay procesos guardados para este registro. Un borrador local de Workflow Studio no se asocia automáticamente a una empresa.</div>
                  <div v-for="process in partyPortfolio.processes" :key="process.id" class="party-record-asset">
                    <div><strong>{{process.name}}</strong>
                      <small>{{processTypeLabel(process)}} · {{process.activity_count}} actividades · {{process.status==='PREVIEW_SHARED'?'Compartida en modo lectura':'No publicado'}}</small>
                    </div>
                    <button type="button" class="ghost-button" @click="openPartyExistingProcess(party,process)">{{process.kind==='DESIGN'?'Editar diagrama':process.kind==='PROPOSAL'?'Revisar propuesta':'Ver proceso'}}</button>
                  </div>
                </div>
                <div class="party-record-section">
                  <h4>Expedientes <span>{{partyPortfolio.cases.length}}</span></h4>
                  <div v-if="!partyPortfolio.cases.length" class="party-record-empty">Este registro todavía no tiene expedientes contractuales.</div>
                  <div v-for="record in partyPortfolio.cases" :key="record.id" class="party-record-asset">
                    <div><strong>{{record.title}}</strong>
                      <small>{{caseStateLabel(record.state)}} · {{record.workflow_version_id?'Con workflow vinculado':'Sin workflow vinculado'}} · {{record.completed}} / {{record.total}} actividades completadas</small>
                    </div>
                    <button type="button" class="ghost-button" @click="openPartyExistingCase(record.id)">Abrir expediente</button>
                  </div>
                </div>
                <div class="party-record-secondary">
                  <strong>Otras acciones</strong>
                  <p>Flujo actualmente seleccionado en el diseñador: <b>{{workflowName}}</b>. No se vincula a {{party.name}} hasta que lo guardes aquí.</p>
                  <div class="pilot-actions">
                    <button type="button" class="ghost-button" :disabled="portalPartySaving" @click="saveCurrentWorkflowForParty(party)">Guardar flujo actual en este registro</button>
                    <button type="button" class="ghost-button" @click="openMairaDocumentImport(party.id)">Crear con MAIRA</button>
                    <button type="button" class="ghost-button" @click="selectPartyForContract(party)">Nuevo expediente</button>
                    <button type="button" class="ghost-button" @click="editingPartyId=party.id;editingPartyEmail=party.email||''">Editar contacto</button>
                  </div>
                </div>
                <div v-if="editingPartyId===party.id" class="pilot-edit-contact">
                  <label>Correo de contacto <input v-model="editingPartyEmail" type="email" maxlength="255" placeholder="persona@ejemplo.com"/></label>
                  <button class="primary-button" :disabled="portalPartySaving" @click="savePartyEmail(party.id)">Guardar contacto</button>
                  <button class="ghost-button" @click="editingPartyId=''">Cancelar</button>
                </div>
              </template>

              <div v-if="partyPreview&&partyPreviewTarget?.id===party.id" class="party-record-presentation">
                <div class="pilot-detail-top">
                  <div><span class="eyebrow">PROPUESTA DE MAIRA · NO PUBLICADA</span>
                    <h4>{{partyPreview.workflow.name}}</h4>
                    <p class="pilot-muted">{{partyPreview.source_map.length}} actividades documentales · Requiere revisión</p>
                  </div>
                  <button type="button" class="ghost-button" @click="partyPreview=null;partyPreviewTarget=null">Cerrar vista</button>
                </div>
                <div class="workflow-side-toggle" role="group" aria-label="Ver propuesta por participante">
                  <button type="button" :class="{selected:partyPreviewSide==='CONTRATANTE'}" @click="partyPreviewSide='CONTRATANTE'">Contratante</button>
                  <button type="button" :class="{selected:partyPreviewSide==='CONTRATISTA'}" @click="partyPreviewSide='CONTRATISTA'">Contratista</button>
                </div>
                <WorkflowPresentation :workflow="workflowWithEvidence(partyPreview,party.kind)" :side="partyPreviewSide"/>
                <div v-if="partyPreview.questions.length||partyPreview.observations.length" class="party-record-questions">
                  <strong>Observaciones pendientes</strong>
                  <p v-for="(question,index) in [...partyPreview.questions,...partyPreview.observations]" :key="index">{{question}}</p>
                </div>
                <div class="pilot-actions"><button type="button" class="primary-button" @click="openReviewInDesigner">Continuar en Workflow Studio</button></div>
              </div>
              <div v-if="partyPresentationPreview" class="party-record-presentation">
                <div class="pilot-detail-top"><div><span class="eyebrow">VISTA PREVIA GUARDADA</span><h4>{{partyPresentationPreview.name}}</h4></div>
                  <button class="ghost-button" @click="partyPresentationPreview=null">Cerrar vista</button></div>
                <div class="workflow-side-toggle" role="group" aria-label="Ver proceso por participante">
                  <button :class="{selected:partyPreviewSide==='CONTRATANTE'}" @click="partyPreviewSide='CONTRATANTE'">Contratante</button>
                  <button :class="{selected:partyPreviewSide==='CONTRATISTA'}" @click="partyPreviewSide='CONTRATISTA'">Contratista</button>
                </div>
                <WorkflowPresentation :workflow="partyPresentationPreview.workflow" :side="partyPreviewSide"/>
              </div>
            </div>
          </div>
        </div>
        <div v-if="showNewPartyForm" class="pilot-panel">
          <h3>Nuevo registro</h3><p>Registrar una persona o empresa no crea expedientes ni envía invitaciones.</p>
          <div class="pilot-form-grid">
            <label>Nombre o razón social<input v-model="partyName" maxlength="250" placeholder="Nombre de la persona o empresa"/></label>
            <label>Tipo de persona<select v-model="partyKind"><option value="JURIDICA">Persona jurídica</option><option value="NATURAL">Persona natural</option></select></label>
            <label>Correo de contacto <span class="pilot-optional">opcional</span><input v-model="partyEmail" type="email" maxlength="255" placeholder="contacto@ejemplo.com"/></label>
          </div>
          <div class="pilot-actions"><button class="primary-button" :disabled="portalPartySaving||partyName.trim().length<2" @click="registerParty">Guardar registro</button>
            <button class="ghost-button" @click="showNewPartyForm=false">Cancelar</button></div>
        </div>
      </section>
      <section v-else-if="current==='contrataciones'&&(hasInstitution||portalSession?.can_setup)" class="contract-space">
        <div class="contract-hero"><div><span class="eyebrow">SMART CONTRACT · CONTRATANTE</span><h2>Gestión Contractual</h2><p>Gestiona expedientes, define responsables y revisa el avance de tus contratistas.</p></div><div class="pilot-actions"><button class="ghost-button" @click="openProviderPortal">Ver portal de IPS</button><button class="ghost-button" @click="refreshPortal">Actualizar</button></div></div>
        <div class="pilot-notice">Ambiente de evaluación con datos sintéticos. No admite documentos confidenciales, firma válida ni contratación productiva.</div>
                <div v-if="portalError" class="pilot-error" role="alert">{{portalError}}</div>
        <div v-if="portalMessage" class="pilot-success" role="status">{{portalMessage}}</div>
        <div v-if="portalSession?.can_setup" class="pilot-panel">
          <h3>Crear institución de prueba</h3><p>Solo se crearán datos ficticios. El acceso queda vinculado a tu cuenta Google.</p>
          <label>Nombre del espacio<input v-model="pilotName" maxlength="150"/></label>
          <button class="primary-button" :disabled="portalBusy" @click="setupPilot">Crear espacio de prueba</button>
        </div>
        <template v-else>
          <div class="pilot-panel">
            <h3>Nueva contratación</h3><p>Selecciona una persona o empresa registrada. Puedes abrir un expediente y asociar la plantilla cuando esté lista.</p>
            <div v-if="!partyRecords.length" class="pilot-empty">Primero registra una persona natural o jurídica. <button class="primary-button" @click="current='personas'">Registrar persona o empresa</button></div>
            <div class="pilot-form-grid">
              <label>Persona o empresa registrada<select v-model="selectedPartyId"><option value="">Selecciona un registro</option><option v-for="p in partyRecords" :key="p.id" :value="p.id">{{p.name}} · {{p.kind==='JURIDICA'?'Jurídica':'Natural'}}</option></select></label>
              <label>Nombre del expediente<input v-model="newCaseTitle" maxlength="250" placeholder="Ej. Contratación de servicios"/></label>
              <label>Plantilla <span class="pilot-optional">opcional</span><select v-model="selectedWorkflowId"><option value="">Sin plantilla: asociar más adelante</option><option v-for="tpl in templates" :key="tpl.id" :value="tpl.id">{{tpl.name}} · versión {{tpl.version}}</option></select></label>
            </div>
            <p v-if="selectedParty" class="pilot-muted">{{selectedParty.name}} · {{selectedParty.email||'Sin correo de contacto'}}. {{selectedWorkflowId?'El proceso se activa con esta plantilla y necesita correo de contacto.':'El expediente permanecerá en borrador hasta asociar una plantilla.'}}</p>
            <div class="pilot-actions">
              <button class="primary-button" :disabled="portalBusy||!selectedPartyId||newCaseTitle.trim().length<3||(!!selectedWorkflowId&&!selectedParty?.email)" @click="createPilotCase">{{selectedWorkflowId?'Crear expediente e iniciar proceso':'Crear expediente sin plantilla'}}</button>
              <button class="ghost-button" @click="current='personas'">Personas y empresas</button><button class="ghost-button" @click="current='flujos'">Diseñar plantilla</button>
            </div>
            <p v-if="!templates.length" class="pilot-muted">No hay plantillas publicadas. Esto no impide registrar personas ni abrir expedientes en borrador.</p>
          </div>
          <div class="pilot-panel">
            <h3>Expedientes de la institución <span class="pilot-count">{{internalCases.length}}</span></h3>
            <div v-if="!internalCases.length" class="pilot-empty">Aún no existen expedientes. Crea uno con información ficticia.</div>
            <button v-for="caseItem in internalCases" :key="caseItem.id" class="pilot-case-row" @click="openCase(caseItem.id)">
              <span><strong>{{caseItem.title}}</strong><small>{{caseItem.party_name}} · {{caseItem.party_email}}</small></span>
              <span>{{caseItem.workflow_version_id?caseItem.completed+'/'+caseItem.total:'Sin plantilla'}} · {{caseItem.state==='DRAFT'?'Borrador':caseItem.state==='COMPLETED'?'Finalizado':'En trámite'}}</span>
            </button>
          </div>
        </template>
      </section>
      <section v-else class="overview">
        <div class="placeholder-panel">
          <div class="placeholder-icon">{{menu.find(m=>m.key===current)?.glyph}}</div>
          <span class="eyebrow">SMART CONTRACT / PRÓXIMO HITO</span>
          <h2>{{screenTitle}}</h2>
          <p>Este espacio se conectará con expedientes y roles institucionales cuando se complete la autenticación multiempresa. No presentamos datos de prueba como información real.</p>
          <div class="placeholder-features"><span>◇ Multiempresa</span><span>▣ Control de acceso</span><span>✧ Asistencia MAIRA</span></div>
          <button class="primary-button" @click="current='flujos'">Abrir Workflow Studio ↗</button>
        </div>
      </section>
      <section v-if="activeCase&&current==='contrataciones'" class="contract-case-detail">
        <div class="pilot-detail-top"><div><span class="eyebrow">EXPEDIENTE DE PRUEBA · {{activeCase.side}}</span><h3>{{activeCase.case.title}}</h3><p>{{activeCase.case.party_name}} · {{activeCase.case.completed}} de {{activeCase.case.total}} actividades completadas</p></div><button class="ghost-button" @click="activeCase=null">Cerrar detalle</button></div>
        <div class="pilot-progress"><div :style="{width:activeCase.case.total?Math.round(100*activeCase.case.completed/activeCase.case.total)+'%':'0%'}"></div></div>
        <div v-if="activeCase.side==='CONTRATANTE'&&!activeCase.case.workflow_version_id" class="pilot-draft-attach">
          <strong>Expediente en borrador · Sin plantilla</strong>
          <p>La persona o empresa ya está registrada, pero todavía no hay tareas ni acceso al expediente. Asocia un proceso cuando lo tengas listo.</p>
          <div class="pilot-form-grid"><label>Plantilla publicada<select v-model="draftWorkflowId"><option value="">Selecciona una plantilla</option><option v-for="tpl in templates" :key="tpl.id" :value="tpl.id">{{tpl.name}} · versión {{tpl.version}}</option></select></label></div>
          <div class="pilot-actions">
            <button class="primary-button" :disabled="portalBusy||!draftWorkflowId||!activeCase.case.party_email" @click="attachWorkflowToCase">Asociar plantilla e iniciar proceso</button>
            <button class="ghost-button" @click="current='flujos'">Crear nueva plantilla</button>
            <button v-if="!activeCase.case.party_email" class="ghost-button" @click="current='personas'">Completar correo</button>
          </div>
          <p v-if="!templates.length" class="pilot-muted">Publica una nueva plantilla desde Flujos y vuelve aquí para asociarla.</p>
        </div>
        <button v-if="activeCase.side==='CONTRATANTE'&&activeCase.case.invited" class="ghost-button" @click="inviteLink">Copiar enlace para el contratista</button>
        <div class="pilot-task-list">
          <div v-for="task in activeCase.tasks" :key="task.id" class="pilot-task">
            <div class="pilot-task-head"><strong>{{task.label}}</strong><span class="pilot-task-status">{{task.state==='COMPLETED'?'Completada':task.state==='PENDING'?'Pendiente':task.state==='RETURNED'?'Devuelta':'En espera'}}</span></div>
            <p class="pilot-muted">{{task.side==='CONTRATANTE'?'Entidad contratante':'Contratista'}} · {{task.kind}}</p>
            <p v-if="task.note" class="pilot-task-note">{{task.note}}</p>
            <template v-if="(task.state==='PENDING'||task.state==='RETURNED')&&activeCase.side===task.side&&task.kind!=='START'&&task.kind!=='END'">
              <div v-for="field in task.fields" :key="field.key" class="pilot-field">
                <label>{{field.label}}{{field.required?' *':''}}
                  <select v-if="field.type==='boolean'" :value="answers[field.key]??''" @change="answers[field.key]=($event.target as HTMLSelectElement).value">
                    <option value="">Seleccionar</option><option value="true">Sí</option><option value="false">No</option>
                  </select>
                  <input v-else :value="answers[field.key]||''" :type="field.type==='number'||field.type==='currency'?'number':field.type==='date'?'date':'text'" @input="answers[field.key]=($event.target as HTMLInputElement).value" />
                </label>
              </div>
              <label class="pilot-field">Observación de la actividad<textarea v-model="taskNote" rows="2" maxlength="2000" placeholder="Observación opcional, solo información ficticia"></textarea></label>
              <button class="primary-button" :disabled="portalBusy" @click="completePortalTask(task)">Completar actividad de prueba</button>
            </template>
            <div v-if="activeCase.side==='CONTRATANTE'&&task.side==='CONTRATISTA'&&task.state==='COMPLETED'" class="pilot-return">
              <input v-model="returnReason" placeholder="Motivo de devolución (mínimo cinco caracteres)" maxlength="2000" />
              <button class="ghost-button" :disabled="portalBusy||returnReason.trim().length<5" @click="returnPortalTask(task)">Solicitar corrección</button>
            </div>
          </div>
        </div>
      </section>
    </main>
    <aside v-if="mairaOpen" id="maira-panel" class="maira-dock" aria-label="Asistencia contextual de MAIRA">
      <div class="maira-dock-head">
        <div class="maira-dock-avatar" aria-hidden="true">✦</div>
        <div class="maira-dock-heading"><strong>MAIRA</strong><small>Contract Intelligence Agent</small></div>
        <button type="button" class="maira-dock-close" aria-label="Cerrar panel MAIRA" @click="mairaOpen=false">×</button>
      </div>
      <div class="maira-dock-body">
        <div class="maira-dock-meaning"><strong>Multi-tenant AI for Intelligent Review &amp; Agreements</strong><span>IA multiempresa para revisión inteligente y acuerdos contractuales</span></div>
        <span class="maira-dock-eyebrow">CONTEXTO ACTUAL · {{screenTitle}}</span>
        <h2>{{mairaContext.title}}</h2>
        <p>{{mairaContext.detail}}</p>
        <div v-if="current==='flujos'" class="maira-dock-stats" aria-label="Estado del workflow">
          <div><strong>{{nodeCount}}</strong><span>Etapas</span></div>
          <div><strong>{{edges.length}}</strong><span>Conexiones</span></div>
          <div><strong>{{activeCount}}</strong><span>Activas</span></div>
        </div>
        <div class="maira-dock-divider"></div>
        <span class="maira-dock-eyebrow">ACCIONES DISPONIBLES</span>
        <div class="maira-dock-shortcuts">
          <button v-for="shortcut in mairaShortcuts" :key="shortcut.key" type="button" @click="mairaShortcut(shortcut.key)">
            <span class="maira-shortcut-icon" aria-hidden="true">{{shortcut.icon}}</span>
            <span>{{shortcut.label}}</span><span class="maira-shortcut-arrow" aria-hidden="true">↗</span>
          </button>
        </div>
        <div v-if="mairaLastAction" class="maira-dock-feedback" role="status">{{mairaLastAction}}</div>
        <div v-if="current==='flujos' && errors.length" class="maira-dock-issues">
          <strong>{{errors.length}} observación(es) del borrador</strong>
          <p v-for="(issue,i) in errors.slice(0,3)" :key="i">{{issue}}</p>
        </div>
      </div>
      <div class="maira-dock-foot">
        <span class="maira-dock-indicator"></span>
        <div><strong>Asistencia contextual disponible</strong><small>Gemini aún no está conectado. No se envían documentos ni se ejecutan decisiones contractuales.</small></div>
      </div>
    </aside>
    <button class="maira-launcher" type="button" aria-controls="maira-panel" :aria-expanded="mairaOpen" :aria-label="mairaOpen?'Cerrar Maira':'Abrir Maira'" @click="mairaOpen=!mairaOpen">
      <span class="maira-launcher-icon" aria-hidden="true"><span class="maira-launcher-spark">✦</span></span>
      <span class="maira-launcher-label">Maira</span>
    </button>
  </div>
</template>
