<script setup lang="ts">
import { computed, ref } from 'vue'

type Field = { key:string;label:string;type:string;required:boolean }
type ProviderTask = {id:string;node_id:string;label:string;kind:string;side:string;state:string;fields:Field[];note?:string}
type ProviderCase = {id:string;title:string;party_name:string|null;state:string;workflow_version_id:string|null;total:number;completed:number}
type ProviderCaseDetail = {case:ProviderCase;side:'CONTRATANTE'|'CONTRATISTA';tasks:ProviderTask[]}
const props=defineProps<{
 email:string
 cases:ProviderCase[]
 detail:ProviderCaseDetail|null
 busy:boolean
 error:string
 message:string
 canReturnToAdmin:boolean
}>()
const emit=defineEmits<{
 (e:'openCase',id:string):void
 (e:'refresh'):void
 (e:'closeCase'):void
 (e:'complete',payload:{taskId:string;data:Record<string,unknown>;note:string}):void
 (e:'logout'):void
 (e:'backOffice'):void
}>()
const caseSearch=ref('')
const draftValues=ref<Record<string,Record<string,string>>>({})
const draftNotes=ref<Record<string,string>>({})
const formError=ref('')
const list=computed(()=>props.cases.filter(item=>
 (item.title+' '+(item.party_name||'')).toLocaleLowerCase('es-CO').includes(caseSearch.value.toLocaleLowerCase('es-CO'))))
const pendingCount=computed(()=>props.detail?.tasks.filter(t=>t.state==='PENDING'||t.state==='RETURNED').length||0)
const completion=computed(()=>{
 const detail=props.detail?.case
 return detail?.total?Math.round(100*detail.completed/detail.total):0
})
const readyTasks=computed(()=>props.detail?.tasks.filter(t=>t.state==='PENDING'||t.state==='RETURNED')||[])
const otherTasks=computed(()=>props.detail?.tasks.filter(t=>t.state!=='PENDING'&&t.state!=='RETURNED')||[])
function stateLabel(value:string){
 return ({DRAFT:'Borrador',COMPLETED:'Finalizado',ACTIVE:'En curso',PENDING:'Pendiente',
  RETURNED:'Requiere corrección',BLOCKED:'Próximamente'} as Record<string,string>)[value]||'En trámite'
}
function update(taskId:string,key:string,value:string){
 draftValues.value={...draftValues.value,[taskId]:{...(draftValues.value[taskId]||{}),[key]:value}}
}
function submit(task:ProviderTask){
 formError.value=''
 const values=draftValues.value[task.id]||{}
 const data:Record<string,unknown>={}
 for(const field of task.fields||[]){
  const value=values[field.key]||''
  if(field.required&&!value){formError.value='Completa el campo «'+field.label+'» antes de registrar la actividad.';return}
  if(!value)continue
  if(field.type==='boolean')data[field.key]=value==='true'
  else if(field.type==='number'||field.type==='currency'){
   const numeric=Number(value)
   if(!Number.isFinite(numeric)){formError.value='El campo «'+field.label+'» debe ser numérico.';return}
   data[field.key]=numeric
  }else data[field.key]=value
 }
 emit('complete',{taskId:task.id,data,note:(draftNotes.value[task.id]||'').trim()})
}
</script>

<template>
 <div class="provider-layout">
  <aside class="provider-nav">
   <div class="provider-brand"><img src="/smart-wordmark.png" alt="Smart"/><div><strong>Smart Contract</strong><small>Portal de prestadores</small></div></div>
   <div class="provider-nav-link active"><span aria-hidden="true">▦</span> Mis procesos</div>
   <p class="provider-nav-note">Solo podrás ver expedientes y tareas vinculados a tu correo autorizado.</p>
   <div class="provider-nav-bottom">
    <div class="provider-identity"><span class="provider-avatar">{{email.slice(0,1).toUpperCase()}}</span><div><strong>Cuenta verificada</strong><small>{{email}}</small></div></div>
    <button v-if="canReturnToAdmin" type="button" class="provider-side-button" @click="emit('backOffice')">Volver al escritorio</button>
    <button type="button" class="provider-side-button" @click="emit('logout')">Cerrar sesión</button>
   </div>
  </aside>
  <main class="provider-main">
   <header class="provider-page-top"><div><span>PORTAL DE CONTRATISTAS</span><h1>Mi contratación</h1><p>Consulta tus procesos, responde solicitudes y sigue el avance de cada actividad.</p></div>
    <button type="button" class="provider-outline" :disabled="busy" @click="emit('refresh')">Actualizar</button>
   </header>
   <div class="provider-evaluation-note">Versión de evaluación. No admite carga documental ni firma legal; no envíes información confidencial a través de este portal.</div>
   <div v-if="error" class="provider-alert error" role="alert">{{error}}</div>
   <div v-if="message" class="provider-alert" role="status">{{message}}</div>
   <template v-if="!detail">
    <div class="provider-panel">
     <div class="provider-panel-top"><div><h2>Expedientes asignados</h2><p>{{cases.length}} proceso(s) relacionados con esta cuenta</p></div>
      <input v-model="caseSearch" type="search" class="provider-search" placeholder="Buscar proceso" aria-label="Buscar procesos"/>
     </div>
     <div v-if="!list.length" class="provider-empty"><div class="provider-empty-icon">▣</div><h3>{{cases.length?'No hay resultados':'Todavía no hay procesos asignados'}}</h3>
      <p>{{cases.length?'Prueba con otro término.':'La entidad contratante debe registrar tu correo y asignarte un expediente. No necesitas configurar ningún flujo.'}}</p>
     </div>
     <button v-for="item in list" :key="item.id" type="button" class="provider-case" @click="emit('openCase',item.id)">
      <div><strong>{{item.title}}</strong><span>{{item.party_name||'Entidad contratista'}}</span></div>
      <div class="provider-case-state"><span>{{stateLabel(item.state)}}</span><small>{{item.workflow_version_id?item.completed+' / '+item.total+' actividades':'Sin actividades asignadas'}}</small></div>
      <span class="provider-chevron" aria-hidden="true">›</span>
     </button>
    </div>
   </template>
   <template v-else-if="detail.side==='CONTRATISTA'">
    <button type="button" class="provider-back" @click="emit('closeCase')">‹ Volver a mis procesos</button>
    <section class="provider-panel">
      <div class="provider-case-head"><span>EXPEDIENTE</span><h2>{{detail.case.title}}</h2><p>{{detail.case.party_name}}</p></div>
      <div class="provider-facts"><div><strong>{{completion}}%</strong><small>Avance general</small></div>
       <div><strong>{{pendingCount}}</strong><small>Actividades para ti</small></div>
       <div><strong>{{detail.case.completed}} / {{detail.case.total}}</strong><small>Actividades completadas del expediente</small></div></div>
      <div class="provider-progress"><span :style="{width:completion+'%'}"></span></div>
    </section>
    <section class="provider-panel">
     <div class="provider-panel-top"><div><h2>Actividades por atender</h2><p>Solo se muestran las tareas que te corresponden y que están disponibles.</p></div></div>
     <div v-if="!readyTasks.length" class="provider-empty compact"><h3>Sin actividades pendientes</h3><p>Podrás continuar cuando la entidad habilite las siguientes etapas.</p></div>
     <article v-for="task in readyTasks" :key="task.id" class="provider-task">
      <div class="provider-task-top"><div><span class="provider-task-icon">✓</span><strong>{{task.label}}</strong></div>
       <span class="provider-task-state" :class="{returned:task.state==='RETURNED'}">{{stateLabel(task.state)}}</span></div>
      <p v-if="task.note" class="provider-task-context">Observación: {{task.note}}</p>
      <p class="provider-task-context">{{task.kind==='DOCUMENT_REQUEST'?'Solicitud de información':'Actividad asignada a tu entidad'}}</p>
      <div v-for="field in task.fields" :key="field.key" class="provider-field"><label>{{field.label}}{{field.required?' *':''}}
       <select v-if="field.type==='boolean'" :value="draftValues[task.id]?.[field.key]||''" @change="update(task.id,field.key,($event.target as HTMLSelectElement).value)">
        <option value="">Selecciona</option><option value="true">Sí</option><option value="false">No</option>
       </select>
       <input v-else :type="field.type==='number'||field.type==='currency'?'number':field.type==='date'?'date':'text'"
        :value="draftValues[task.id]?.[field.key]||''" :placeholder="'Ingresa '+field.label.toLocaleLowerCase('es-CO')"
        @input="update(task.id,field.key,($event.target as HTMLInputElement).value)" />
      </label></div>
      <div class="provider-field"><label>Observación (opcional)<textarea :value="draftNotes[task.id]||''" maxlength="2000" rows="2" placeholder="Información relacionada con esta actividad" @input="draftNotes={...draftNotes,[task.id]:($event.target as HTMLTextAreaElement).value}"></textarea></label></div>
      <p v-if="formError" class="provider-alert error" role="alert">{{formError}}</p>
      <button class="provider-primary" type="button" :disabled="busy" @click="submit(task)">{{busy?'Registrando…':'Registrar actividad'}}</button>
     </article>
    </section>
    <section v-if="otherTasks.length" class="provider-panel">
     <div class="provider-panel-top"><div><h2>Historial y próximas etapas</h2><p>Las etapas bloqueadas se abrirán cuando el proceso lo permita.</p></div></div>
     <div v-for="task in otherTasks" :key="task.id" class="provider-history">
      <span>{{task.label}}</span><small>{{stateLabel(task.state)}}</small>
     </div>
    </section>
   </template>
   <div v-else class="provider-alert error">Este expediente pertenece al escritorio interno. Accede con un usuario invitado como contratista para consultar sus tareas.</div>
  </main>
 </div>
</template>

<style scoped>
.provider-layout{min-height:100vh;display:grid;grid-template-columns:244px minmax(0,1fr);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#233e5b;background:#f5f8fc}
.provider-nav{background:#fff;border-right:1px solid #e2ebf4;display:flex;flex-direction:column;padding:28px 20px;gap:20px}
.provider-brand{display:flex;align-items:center;gap:11px}.provider-brand img{width:76px;max-width:38%;height:auto}.provider-brand div{display:grid;gap:5px}.provider-brand strong{font-size:14px;white-space:nowrap}.provider-brand small{font-size:10px;color:#7791aa}
.provider-nav-link{padding:12px;background:#edf4ff;border:1px solid #d7e6fa;border-radius:11px;color:#2666b7;font-size:13px;font-weight:700;display:flex;gap:13px}
.provider-nav-note{line-height:1.6;color:#8496a9;font-size:11px;margin:0}
.provider-nav-bottom{margin-top:auto;display:grid;gap:10px}
.provider-identity{padding:12px;background:#f5f8fc;border:1px solid #edf1f6;border-radius:12px;display:flex;align-items:center;gap:9px;min-width:0}
.provider-identity>div{min-width:0;display:grid;gap:4px}.provider-identity strong{font-size:11px}.provider-identity small{font-size:10px;overflow-wrap:anywhere;color:#7b8fa5}
.provider-avatar{width:30px;height:30px;flex:none;display:grid;place-items:center;border-radius:9px;background:#e1ebfd;color:#2464af;font-size:12px;font-weight:800}
.provider-side-button{padding:11px;border:1px solid #dce7f2;background:white;color:#486680;border-radius:10px;text-align:left;font-weight:650;cursor:pointer}
.provider-main{padding:38px max(24px,6vw) 70px;max-width:1290px;width:100%;box-sizing:border-box;margin:0 auto}
.provider-page-top{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:25px}
.provider-page-top span,.provider-case-head>span{font-size:10px;letter-spacing:.13em;font-weight:800;color:#3978c7}
.provider-page-top h1{font-size:clamp(28px,3vw,39px);margin:7px 0 8px;color:#1b3e65;font-weight:780;letter-spacing:-.04em}
.provider-page-top p,.provider-panel-top p{font-size:12px;color:#7890a7;line-height:1.65;margin:0}
.provider-outline,.provider-back{background:white;border:1px solid #d6e5f5;color:#39638b;border-radius:11px;padding:10px 15px;cursor:pointer;font-weight:680}
.provider-evaluation-note{padding:12px 16px;background:#fbfcff;border:1px solid #dfe7ef;border-radius:12px;color:#73879d;font-size:11px;line-height:1.6;margin-bottom:17px}
.provider-panel{background:white;border:1px solid #e0eaf4;border-radius:18px;padding:23px;margin:0 0 17px;box-shadow:0 4px 24px rgba(22,56,92,.025)}
.provider-panel-top{display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap;margin-bottom:15px}
.provider-panel h2{font-size:17px;color:#1a406a;margin:0 0 6px;letter-spacing:-.015em}
.provider-search{padding:10px 13px;border:1px solid #d9e4ef;border-radius:11px;min-width:230px;background:#fafcff}
.provider-case{display:grid;grid-template-columns:1fr auto 16px;gap:16px;align-items:center;text-align:left;background:white;border:0;border-top:1px solid #edf2f8;padding:20px 3px;width:100%;cursor:pointer;color:inherit}
.provider-case:hover{background:#f9fcff}.provider-case>div:first-child{display:grid;gap:6px}.provider-case strong{font-size:13px}.provider-case span{color:#7290ad;font-size:11px}
.provider-case-state{text-align:right;display:grid;gap:5px}.provider-case-state span{font-size:11px;font-weight:700;color:#467c91}
.provider-case-state small{font-size:10px;color:#8097ad}.provider-chevron{font-size:24px!important;color:#79a2d2!important}
.provider-empty{padding:48px 25px;text-align:center}.provider-empty.compact{padding:28px}.provider-empty-icon{font-size:26px;color:#8eb2dc}.provider-empty h3{font-size:15px;margin:8px 0;color:#345574}.provider-empty p{font-size:12px;color:#8397ab;max-width:450px;margin:auto;line-height:1.65}
.provider-alert{padding:12px 16px;background:#eaf7f3;border:1px solid #bfe6d9;border-radius:10px;font-size:12px;color:#276d5a;margin-bottom:15px}.provider-alert.error{color:#a03f48;background:#fff3f3;border-color:#f3cccc}
.provider-back{margin-bottom:16px}.provider-case-head h2{font-size:24px;margin:7px 0}.provider-case-head p{color:#7690a9;font-size:12px;margin:0}
.provider-facts{display:flex;gap:12px;flex-wrap:wrap;margin-top:18px}.provider-facts>div{min-width:145px;display:grid;gap:5px;padding:15px;background:#f7faff;border-radius:12px}.provider-facts strong{font-size:19px;color:#254b72}.provider-facts small{font-size:10px;color:#8193aa}
.provider-progress{height:8px;background:#eaf1f8;border-radius:10px;overflow:hidden;margin-top:18px}.provider-progress span{display:block;height:100%;background:#4a98bb;border-radius:10px;transition:width .4s}
.provider-task{border-top:1px solid #edf1f5;padding:20px 0}.provider-task-top{display:flex;justify-content:space-between;gap:14px;align-items:center}
.provider-task-top>div{display:flex;gap:9px;align-items:center}.provider-task-top strong{font-size:13px;color:#294968}.provider-task-icon{display:grid;place-items:center;background:#e4f2ed;color:#278b73;width:28px;height:28px;border-radius:10px}
.provider-task-state{font-size:10px;color:#397a63;border-radius:20px;background:#e8f6ed;padding:6px 9px}.provider-task-state.returned{color:#99652b;background:#fff4e3}
.provider-task-context{color:#8497a8;font-size:11px;line-height:1.55}
.provider-field{margin-top:15px}.provider-field label{display:grid;gap:7px;font-size:12px;font-weight:650;color:#446481}
.provider-field input,.provider-field select,.provider-field textarea{font:inherit;font-size:12px;padding:11px;border:1px solid #d5e3f1;border-radius:10px;box-sizing:border-box;width:100%;color:#234665}
.provider-primary{background:#2c7dd7;color:white;padding:12px 20px;border:0;border-radius:11px;cursor:pointer;font-size:12px;font-weight:720;margin-top:15px}
.provider-primary:disabled{opacity:.55;cursor:not-allowed}.provider-history{display:flex;justify-content:space-between;gap:15px;padding:12px 0;border-bottom:1px solid #edf2f8;color:#436384;font-size:12px}
.provider-history small{font-size:11px;color:#8da0b3}
@media(max-width:850px){.provider-layout{display:block}.provider-nav{padding:12px 18px;gap:11px;border-right:0;border-bottom:1px solid #e6eef6}.provider-brand img{width:63px}.provider-nav-bottom{display:flex;flex-wrap:wrap;align-items:center}.provider-nav-note,.provider-nav-link{display:none}.provider-main{padding:23px 16px 60px}.provider-panel{padding:16px}.provider-page-top{align-items:flex-start}.provider-page-top h1{font-size:26px}}
@media(max-width:480px){.provider-case{grid-template-columns:1fr 16px}.provider-case-state{grid-column:1;text-align:left}.provider-chevron{grid-column:2;grid-row:1}.provider-facts>div{min-width:0;flex:1}.provider-page-top{flex-wrap:wrap}.provider-search{width:100%;min-width:0}}
</style>
