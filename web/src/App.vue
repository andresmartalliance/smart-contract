<script setup lang="ts">
import { computed, ref, shallowRef, watch } from 'vue'
import { VueFlow, type Node, type Edge, type Connection } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

type Screen = 'resumen' | 'contrataciones' | 'prestadores' | 'flujos' | 'maira' | 'configuracion'
type Kind = 'START'|'FORM'|'DOCUMENT_REQUEST'|'DOCUMENT_REVIEW'|'VALIDATION'|'APPROVAL'|'NEGOTIATION'|'CALCULATION'|'DOCUMENT_GENERATION'|'SIGNATURE'|'NOTIFICATION'|'INTEGRATION'|'TIMER'|'JOIN'|'HUMAN_DECISION'|'END'
type Policy = 'LEGAL_LOCKED' | 'ORG_REQUIRED' | 'CONDITIONAL' | 'OPTIONAL'
type Condition = {field:string;op:'eq'|'neq'|'gt'|'gte'|'lt'|'lte'|'in'|'exists';value?: unknown}
type FieldType = 'text'|'number'|'date'|'currency'|'boolean'|'select'
type WorkField = {key:string;label:string;type:FieldType;required:boolean}
type ExecutionMode = 'MANUAL'|'AI_ASSISTED'|'API'|'RPA'
type WorkNode = {id:string;label:string;kind:Kind;policy:Policy;enabled:boolean;role:string|null;when?:Condition|null;config:{position?:{x:number;y:number};instructions?:string;execution_mode?:ExecutionMode;fields?:WorkField[]}}
type WorkEdge = {source:string;target:string;when?:Condition|null}
type Workflow = {key: string; name: string; modality_key: string | null; nodes: WorkNode[]; edges: WorkEdge[]; metadata: Record<string, unknown>}

const current = ref<Screen>('flujos')
const menu: { key: Screen; title: string; glyph: string }[] = [
  { key:'resumen',title:'Resumen',glyph:'▦' },
  { key:'contrataciones',title:'Contrataciones',glyph:'▤' },
  { key:'prestadores',title:'Prestadores',glyph:'⌂' },
  { key:'flujos',title:'Flujos',glyph:'◇' },
  { key:'maira',title:'MAIRA',glyph:'✳' },
  { key:'configuracion',title:'Configuración',glyph:'⚙' }
]
const screenTitle = computed(() => menu.find(m => m.key === current.value)?.title ?? '')
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
const modalityKey = ref('')
const flowMessage = ref('')
const errors = ref<string[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const showCatalog = ref(true)
const nodes = shallowRef<Node[]>([])
const edges = shallowRef<Edge[]>([])

function nodeInfo(id:string, kind:Kind, label:string, x:number,y:number,role:string|null=null,policy:Policy='OPTIONAL'):Node {
  return {id,type:kind==='START'?'input':kind==='END'?'output':'default',position:{x,y},data:{label,kind,role,policy,enabled:true,config:{execution_mode:'MANUAL',fields:[]}},class:kind==='START'?'node-start':kind==='END'?'node-end':''}
}
function loadExample(){
  workflowName.value='Contratación de red prestadora';workflowKey.value='RED_PRESTADORA_BASE';modalityKey.value=''
  nodes.value=[
    nodeInfo('inicio','START','Solicitud de contratación',260,24,null,'ORG_REQUIRED'),
    nodeInfo('documentos','DOCUMENT_REVIEW','Revisión documental',260,155,'RED'),
    nodeInfo('juridica','APPROVAL','Concepto jurídico',70,300,'JURIDICO'),
    nodeInfo('financiera','APPROVAL','Revisión financiera',455,300,'FINANCIERO'),
    nodeInfo('acuerdo','DOCUMENT_GENERATION','Acuerdo de voluntades',260,440,'RED'),
    nodeInfo('fin','END','Formalización',260,570,null,'ORG_REQUIRED')
  ]
  edges.value=[{id:'e1',source:'inicio',target:'documentos'},{id:'e2',source:'documentos',target:'juridica'},{id:'e3',source:'documentos',target:'financiera'},{id:'e4',source:'juridica',target:'acuerdo'},{id:'e5',source:'financiera',target:'acuerdo'},{id:'e6',source:'acuerdo',target:'fin'}]
  selectedId.value='documentos';selectedEdgeId.value=null;nodeCounter.value=1;errors.value=[];simulationVisible.value=false;flowMessage.value='Plantilla base cargada para edición.'
}
function newWorkflow(){
  workflowName.value='Nuevo proceso de contratación';workflowKey.value='NUEVO_PROCESO';modalityKey.value=''
  nodes.value=[nodeInfo('inicio','START','Inicio',230,60,null,'ORG_REQUIRED'),nodeInfo('fin','END','Finalización',230,270,null,'ORG_REQUIRED')]
  edges.value=[{id:'e-inicio-fin',source:'inicio',target:'fin'}]
  selectedId.value=null;selectedEdgeId.value=null;nodeCounter.value=1;errors.value=[];simulationVisible.value=false;flowMessage.value='Proceso en blanco. Agrega bloques desde el catálogo.'
}
loadExample()
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

function editNode(field:'label'|'role'|'enabled'|'policy'|'instructions'|'conditionField'|'conditionValue'|'conditionOperator'|'executionMode', val:string|boolean){
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
   else if(field==='policy') {
     if(['LEGAL_LOCKED','ORG_REQUIRED'].includes(target.policy)&&!['LEGAL_LOCKED','ORG_REQUIRED'].includes(String(val))){flowMessage.value='No puedes rebajar la protección de una etapa obligatoria desde el editor.';return}
     next.policy=val; if(['ORG_REQUIRED','LEGAL_LOCKED'].includes(String(val)))next.enabled=true
   }
  else if(field==='role')next.role=val===''?null:val
  else next[field]=val
  nodes.value=nodes.value.map(n=>n.id===selectedId.value?{...n,data:next,class:next.enabled===false?'node-disabled':n.type==='input'?'node-start':n.type==='output'?'node-end':''}:n)
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
    edges:edges.value.map(e=>({source:e.source,target:e.target,when:(e.data as {when?:Condition}|undefined)?.when||null})),metadata:{source:'smart-contract-workflow-studio',draft:true}}
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
 const imported:Node[]=parsed.nodes.map((raw,i)=>{
   if(typeof raw.id!=='string'||!raw.id.trim()||raw.id.length>120||typeof raw.label!=='string'||!raw.label.trim()||!validKinds.has(raw.kind)||!validPolicies.has(raw.policy)||typeof raw.enabled!=='boolean')throw new Error('La etapa '+(i+1)+' tiene valores inválidos.')
   if(!raw.enabled&&['LEGAL_LOCKED','ORG_REQUIRED'].includes(raw.policy))throw new Error('El archivo intenta desactivar un requisito protegido.')
   const fields=(raw.config?.fields||[]).map(f=>{
     if(typeof f.key!=='string'||typeof f.label!=='string'||!validFields.has(f.type)||typeof f.required!=='boolean')throw new Error('Campo inválido en '+raw.label)
     return {key:f.key,label:f.label,type:f.type,required:f.required}
   })
   const position=raw.config?.position
   const x=typeof position?.x==='number'&&Number.isFinite(position.x)?position.x:260
   const y=typeof position?.y==='number'&&Number.isFinite(position.y)?position.y:i*130
   const n=nodeInfo(raw.id,raw.kind,raw.label,x,y,raw.role||null,raw.policy)
   const mode=raw.config?.execution_mode
   n.data={label:raw.label,kind:raw.kind,role:raw.role||null,policy:raw.policy,enabled:raw.enabled,when:safeCondition(raw.when),config:{position:{x,y},instructions:String(raw.config?.instructions||'').slice(0,5000),execution_mode:executionModes.some(x=>x.value===mode)?mode:'MANUAL',fields}}
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
 nodes.value=imported;edges.value=parsedEdges;selectedId.value=null;selectedEdgeId.value=null;simulationVisible.value=false
 nodeCounter.value=imported.length+1;errors.value=[]
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
function restoreLocalDraft(){
 try{
   const raw=localStorage.getItem(LOCAL_DRAFT_KEY)
   if(!raw)return
   loadDefinition(JSON.parse(raw) as Partial<Workflow>)
   flowMessage.value='Se recuperó el último borrador de este navegador.'
 }catch{flowMessage.value='No se pudo recuperar el borrador local. Se cargó el ejemplo base.'}
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
  <div class="shell">
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark">S</div><div><strong>Smart Contract</strong><small>MAIRA · Plataforma contractual</small></div></div>
      <nav><button v-for="entry in menu" :key="entry.key" :class="{active:current===entry.key}" @click="current=entry.key">
        <span class="menu-glyph">{{entry.glyph}}</span><span class="menu-title">{{entry.title}}</span></button></nav>
      <div class="sidebar-foot">Smart Alliance<br>Plataforma multiempresa</div>
    </aside>
    <main class="main">
      <header class="top-header"><div><small>Smart Contract / {{ screenTitle }}</small><h1>{{screenTitle}}</h1></div><span class="context-pill">Development</span></header>
      <section v-if="current==='flujos'" class="stack">
        <div class="heading"><div><h2>Workflow Studio</h2><p>Construye procesos utilizando etapas, condiciones y responsables configurables.</p></div><div class="header-actions"><button class="ghost-button" @click="newWorkflow">Nuevo flujo</button><button class="ghost-button" @click="fileInput?.click()">Importar</button><button class="primary-button" @click="exportDraft">Exportar borrador</button></div></div>
        <input ref="fileInput" type="file" accept="application/json,.json" class="hidden-input" @change="importDraft" />
        <div class="workflow-meta">
          <label>Nombre del proceso<input v-model="workflowName" maxlength="200" aria-label="Nombre del proceso" /></label>
          <label>Identificador<input v-model="workflowKey" maxlength="120" aria-label="Identificador del proceso" /></label>
          <label>Modalidad <span class="field-hint">opcional</span><input v-model="modalityKey" placeholder="Definida por la entidad" maxlength="120" aria-label="Modalidad configurable" /></label>
        </div>
        <div class="studio-layout">
          <div class="studio-catalog">
            <div class="panel-title"><strong>Componentes</strong><button class="tiny-link" @click="loadExample">Restaurar ejemplo</button></div>
            <p class="panel-caption">Selecciona una etapa y agrega bloques a su recorrido.</p>
            <div v-if="showCatalog" class="catalog-scroll">
              <div v-for="category in categories" :key="category" class="catalog-group"><span class="group-label">{{category}}</span>
                <button v-for="block in blocks.filter(b=>b.category===category)" :key="block.kind" class="block-button" @click="addBlock(block.kind)"><span class="block-glyph">{{block.glyph}}</span><span>{{block.title}}</span><span class="plus">+</span></button>
              </div>
            </div>
          </div>
          <div class="diagram-panel">
            <div class="panel-title"><strong>Diagrama del proceso</strong><span class="flow-count">{{activeCount}} etapas activas</span></div>
            <div class="canvas-area">
              <VueFlow v-model:nodes="nodes" v-model:edges="edges" :fit-view-on-init="true" :nodes-connectable="true" :nodes-draggable="true" :elements-selectable="true" :min-zoom="0.2" :max-zoom="2" @connect="onConnect" @node-click="({node}) => {selectedId=node.id;selectedEdgeId=null}" @edge-click="({edge}) => {selectedEdgeId=edge.id;selectedId=null}" @node-drag-stop="onNodeDragStop" @pane-click="() => {selectedId=null;selectedEdgeId=null}" />
            </div>
            <div class="canvas-footer"><span>Arrastra las etapas · Conecta los puntos · Selecciona para editar</span><div class="canvas-buttons"><button @click="validateDraft">Verificar</button><button @click="simulateDraft">Simular</button></div></div>
          </div>
          <div class="inspector-panel">
            <div class="panel-title"><strong>Propiedades</strong><span class="inspector-icon">⚙</span></div>
            <template v-if="selectedData">
              <p class="panel-caption">{{stageLabel}}</p>
              <label class="inspector-field">Nombre de la etapa<input :value="selectedData.label" maxlength="200" @input="editNode('label',($event.target as HTMLInputElement).value)" /></label>
              <label class="inspector-field">Tipo de componente<input :value="blocks.find(b=>b.kind===selectedData?.kind)?.title||selectedData.kind" disabled /></label>
              <label class="inspector-field">Responsable<input list="roles-contrato" :value="selectedData.role||''" placeholder="Selecciona o escribe otro rol" maxlength="120" @input="editNode('role',($event.target as HTMLInputElement).value)"/><datalist id="roles-contrato"><option v-for="role in roles" :key="role" :value="role" /></datalist></label>
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
        <div v-if="simulationVisible" class="simulation-panel"><div class="panel-title"><strong>Simulación de recorrido</strong><button class="tiny-link" @click="simulationVisible=false">Cerrar</button></div><p class="panel-caption">Datos de ejemplo en JSON; indica etapas completadas separadas por coma. Esta prueba es local y no ejecuta tareas.</p>
          <div class="simulation-fields"><label>Datos del expediente (JSON)<textarea v-model="simulationFacts" rows="3" spellcheck="false"/></label><label>Identificadores completados<input v-model="simulationCompleted" placeholder="inicio, documentos"/></label><button class="primary-button" @click="simulateDraft">Ejecutar simulación</button></div>
          <p v-if="simulationError" class="validation-list">{{simulationError}}</p>
          <div class="simulation-results"><div v-for="(status,id) in simulationStatuses" :key="id" class="simulation-item"><span>{{labelFor(String(id))}}</span><strong>{{status}}</strong></div></div>
        </div>
        <div v-if="flowMessage" class="status-message" role="status">{{flowMessage}}</div>
        <div v-if="errors.length" class="validation-list"><strong>Observaciones del flujo</strong><p v-for="(err,i) in errors" :key="i">{{err}}</p></div>
        <div class="summary-strip"><span>{{nodeCount}} etapas · {{edges.length}} conexiones · {{policyCount}} protegidas</span><span>Borrador guardado en este navegador{{lastSavedAt?' · '+lastSavedAt:''}}. Para compartirlo, usa Exportar. La publicación institucional requiere inicio de sesión.</span></div>
      </section>
      <section v-else-if="current==='resumen'" class="overview"><h2>Visión de la plataforma</h2><p>La información contractual se mostrará aquí cuando las entidades y expedientes tengan acceso autenticado.</p><div class="stat-grid"><div><strong>{{nodeCount}}</strong><span>Etapas del borrador actual</span></div><div><strong>{{activeCount}}</strong><span>Etapas habilitadas</span></div><div><strong>{{edges.length}}</strong><span>Dependencias definidas</span></div></div><button class="primary-button" @click="current='flujos'">Abrir diseñador</button></section>
      <section v-else-if="current==='maira'" class="overview"><h2>MAIRA</h2><p>MAIRA ayudará a interpretar documentos, recomendar plantillas y proponer modificaciones a los flujos. Todavía no se ha conectado Gemini ni se han habilitado acciones de IA.</p><button class="primary-button" @click="current='flujos'">Ir a Workflow Studio</button></section>
      <section v-else class="overview"><h2>{{screenTitle}}</h2><p>Esta sección utilizará los datos y permisos de cada institución cuando se complete la autenticación multiempresa. No se muestran datos ficticios como si fueran contratos reales.</p><button class="ghost-button" @click="current='flujos'">Volver a Flujos</button></section>
    </main>
  </div>
</template>
