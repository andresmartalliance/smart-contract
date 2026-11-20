<script setup lang="ts">
import { computed, ref, watch } from 'vue'
export type PreviewSide='CONTRATANTE'|'CONTRATISTA'
export type PreviewField={key:string;label:string;type:string;required:boolean;options?:unknown[]}
export type PreviewNode={id:string;label:string;kind:string;enabled?:boolean;role?:string|null;
 config?:{actor_side?:string;fields?:PreviewField[];instructions?:string;source_step?:string;[key:string]:unknown}}
export type PreviewEdge={source:string;target:string;when?:{field:string;op:string;value?:unknown}|null}
export type PreviewWorkflow={key:string;name:string;nodes:PreviewNode[];edges:PreviewEdge[];metadata?:Record<string,unknown>}
const props=defineProps<{workflow:PreviewWorkflow;side:PreviewSide}>()
const selectedId=ref('')
const draftValues=ref<Record<string,string>>({})
const stages=computed(()=>props.workflow.nodes.filter(n=>n.kind!=='START'&&n.kind!=='END'&&n.enabled!==false))
const active=computed(()=>stages.value.find(n=>n.id===selectedId.value)||
 stages.value.find(n=>sideOf(n)===props.side)||stages.value[0]||null)
const index=computed(()=>stages.value.findIndex(n=>n.id===active.value?.id))
watch(()=>props.workflow.key,()=>{selectedId.value='';draftValues.value={}})
watch(()=>props.side,()=>{selectedId.value='';draftValues.value={}})
function sideOf(n:PreviewNode){
 const side=n.config?.actor_side
 return side==='CONTRATANTE'||side==='CONTRATISTA'?side:'REVISAR'
}
function sideName(n:PreviewNode){return sideOf(n)==='CONTRATANTE'?'Contratante':sideOf(n)==='CONTRATISTA'?'Prestador':'Por definir'}
const myStages=computed(()=>stages.value.filter(n=>sideOf(n)===props.side))
const unassigned=computed(()=>stages.value.filter(n=>sideOf(n)==='REVISAR'))
const mine=computed(()=>Boolean(active.value&&sideOf(active.value)===props.side))
const fields=computed(()=>active.value&&mine.value&&Array.isArray(active.value.config?.fields)?active.value.config.fields:[])
const before=computed(()=>props.workflow.edges.filter(e=>e.target===active.value?.id)
 .map(e=>props.workflow.nodes.find(n=>n.id===e.source)?.label||e.source))
const after=computed(()=>props.workflow.edges.filter(e=>e.source===active.value?.id).map(e=>{
  const name=props.workflow.nodes.find(n=>n.id===e.target)?.label||e.target
  return e.when?(e.when.field+' '+e.when.op+' '+String(e.when.value)+' → '+name):name
}))
function kindName(kind:string){
 const label:Record<string,string>={FORM:'Formulario',VALIDATION:'Validación',DOCUMENT_REQUEST:'Solicitud documental',
 DOCUMENT_REVIEW:'Revisión documental',HUMAN_DECISION:'Decisión',APPROVAL:'Aprobación',
 NEGOTIATION:'Negociación',NOTIFICATION:'Notificación',SIGNATURE:'Firma',
 DOCUMENT_GENERATION:'Generación documental',CALCULATION:'Cálculo',TIMER:'Espera',INTEGRATION:'Integración'}
 return label[kind]||'Actividad'
}
function select(id:string){selectedId.value=id;draftValues.value={}}
function value(key:string,next:string){draftValues.value={...draftValues.value,[key]:next}}
function optionValue(opt:unknown):string{
 if(typeof opt==='string'||typeof opt==='number')return String(opt)
 if(opt&&typeof opt==='object'&&'value' in opt)return String((opt as {value:unknown}).value??'')
 return ''
}
function optionLabel(opt:unknown):string{
 if(typeof opt==='string'||typeof opt==='number')return String(opt)
 if(opt&&typeof opt==='object'&&'label' in opt)return String((opt as {label:unknown}).label??'')
 return ''
}
</script>
<template>
 <section class="presentation">
  <header class="presentation-head">
    <div><span class="presentation-eyebrow">PANTALLAS GENERADAS DESDE EL WORKFLOW</span>
      <h3>{{workflow.name}}</h3>
      <p>Recorrido visto desde {{side==='CONTRATISTA'?'el portal del prestador':'el escritorio del contratante'}}.</p>
    </div>
    <span class="presentation-tag">Solo visualización</span>
  </header>
  <div class="presentation-metrics">
    <div><strong>{{stages.length}}</strong><span>Actividades</span></div>
    <div><strong>{{myStages.length}}</strong><span>De esta parte</span></div>
    <div><strong>{{unassigned.length}}</strong><span>Pendientes de responsable</span></div>
  </div>
  <div class="presentation-body">
    <nav class="presentation-nav" aria-label="Etapas del proceso">
      <p>RECORRIDO CONTRACTUAL</p>
      <button v-for="(step,i) in stages" :key="step.id" type="button"
        :class="['presentation-step',{active:active?.id===step.id,owner:sideOf(step)===side}]"
        :aria-current="active?.id===step.id?'step':undefined" @click="select(step.id)">
        <span class="presentation-number">{{i+1}}</span>
        <span class="presentation-step-copy"><strong>{{step.label}}</strong><small>{{sideName(step)}} · {{kindName(step.kind)}}</small></span>
      </button>
    </nav>
    <article v-if="active" class="presentation-detail">
      <div class="presentation-top"><span>ACTIVIDAD {{index+1}} DE {{stages.length}}</span>
        <span class="presentation-role">{{sideName(active)}}</span>
      </div>
      <h4>{{active.label}}</h4><p class="presentation-kind">{{kindName(active.kind)}}</p>
      <p v-if="sideOf(active)==='REVISAR'" class="presentation-notice warning">El responsable de esta actividad está por definir. Aún no se asigna al contratante ni al prestador.</p>
      <p v-else-if="!mine" class="presentation-notice neutral">Esta actividad corresponde a la otra parte. Forma parte del recorrido, pero no podrás diligenciarla.</p>
      <p v-else class="presentation-notice okay">Aquí aparecerá la actividad que corresponde a {{side==='CONTRATISTA'?'la IPS':'la entidad contratante'}}.</p>
      <div v-if="fields.length" class="presentation-fields">
        <strong>Información solicitada</strong>
        <label v-for="field in fields" :key="field.key"><span>{{field.label}} <small v-if="field.required">Obligatorio</small></span>
          <select v-if="field.type==='boolean'" :value="draftValues[field.key]||''" @change="value(field.key,($event.target as HTMLSelectElement).value)">
            <option value="">Seleccionar</option><option value="true">Sí</option><option value="false">No</option>
          </select>
          <select v-else-if="field.type==='select'" :value="draftValues[field.key]||''" @change="value(field.key,($event.target as HTMLSelectElement).value)">
            <option value="">Seleccionar</option>
            <option v-for="(opt,i) in field.options||[]" :key="i" :value="optionValue(opt)">{{optionLabel(opt)}}</option>
          </select>
          <input v-else :type="field.type==='date'?'date':field.type==='number'||field.type==='currency'?'number':'text'"
            :value="draftValues[field.key]||''" placeholder="Campo en vista previa"
            @input="value(field.key,($event.target as HTMLInputElement).value)"/>
        </label>
        <p>Los valores ingresados aquí no se guardan ni se envían.</p>
      </div>
      <div v-else-if="mine" class="presentation-empty-fields">
        <strong>Esta etapa todavía no tiene campos configurados.</strong>
        <p>El diseñador debe definirlos antes de utilizarla. MAIRA no inventará campos, documentos ni aprobaciones.</p>
      </div>
      <section v-if="before.length" class="presentation-relations"><strong>Etapas anteriores</strong><p v-for="(n,i) in before" :key="i">{{n}}</p></section>
      <section v-if="after.length" class="presentation-relations"><strong>Rutas siguientes propuestas</strong><p v-for="(n,i) in after" :key="i">{{n}}</p>
        <small>Las condiciones son referencias del diseño; no se ejecutan desde esta vista.</small>
      </section>
      <div class="presentation-actions">
        <button type="button" :disabled="index<=0" @click="select(stages[index-1].id)">Anterior</button>
        <span>No operativo</span>
        <button type="button" :disabled="index>=stages.length-1" @click="select(stages[index+1].id)">Siguiente etapa</button>
      </div>
    </article>
  </div>
  <footer>La previsualización no crea expedientes, no habilita tareas, no publica plantillas y no firma contratos.</footer>
 </section>
</template>
<style scoped>
.presentation{background:#fff;border:1px solid #d9e6f3;border-radius:20px;overflow:hidden;color:#294965}
.presentation-head{padding:25px 28px 20px;display:flex;justify-content:space-between;gap:15px;align-items:flex-start;background:#fbfdff}
.presentation-eyebrow,.presentation-top{font-size:10px;font-weight:800;letter-spacing:.11em;color:#347ac4}
.presentation-head h3{font-size:23px;line-height:1.3;color:#1a416b;margin:7px 0}
.presentation-head p{font-size:12px;color:#8297aa;margin:0}
.presentation-tag{border:1px solid #d4e3f6;background:#eff6ff;color:#4075a9;padding:7px 12px;border-radius:20px;font-size:11px;white-space:nowrap}
.presentation-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:#e8f0f7;border-top:1px solid #e8f0f7;border-bottom:1px solid #e8f0f7}
.presentation-metrics div{background:white;padding:16px 27px;display:grid;gap:5px}
.presentation-metrics strong{font-size:21px;color:#255a8c}.presentation-metrics span{font-size:11px;color:#839bad}
.presentation-body{display:grid;grid-template-columns:minmax(240px,34%) minmax(0,1fr);min-height:540px}
.presentation-nav{padding:18px 13px;background:#f8fafc;border-right:1px solid #e4edf6;display:flex;flex-direction:column;gap:6px;max-height:720px;overflow-y:auto}
.presentation-nav p{font-size:10px;letter-spacing:.12em;font-weight:800;color:#8ba0b5;padding:0 12px;margin:0 0 9px}
.presentation-step{text-align:left;display:flex;gap:9px;padding:11px 10px;background:transparent;border:1px solid transparent;border-radius:11px;cursor:pointer}
.presentation-step.active{background:#eaf4ff;border-color:#c2dcfa}.presentation-step.owner .presentation-number{background:#d8f0e9;color:#317d6d}
.presentation-number{flex:none;background:#e9f0f8;color:#50789c;border-radius:8px;width:27px;height:27px;display:grid;place-items:center;font-size:11px;font-weight:800}
.presentation-step-copy{display:grid;gap:5px}.presentation-step-copy strong{font-size:12px;color:#335a78;line-height:1.45}.presentation-step-copy small{font-size:10px;color:#889caf;line-height:1.5}
.presentation-detail{padding:29px 32px;min-width:0}.presentation-top{display:flex;justify-content:space-between;gap:10px}
.presentation-role{font-size:11px;color:#5681a0;letter-spacing:normal;background:#f2f8fc;border-radius:30px;padding:7px 10px}
.presentation-detail h4{font-size:20px;color:#22466c;line-height:1.4;margin:18px 0 5px}
.presentation-kind{color:#93a5b6;font-size:12px;margin:0 0 22px}
.presentation-notice{padding:13px 16px;font-size:12px;line-height:1.6;border-radius:11px}
.presentation-notice.warning{background:#fff8eb;border:1px solid #ecdcbb;color:#8b6434}
.presentation-notice.neutral{background:#f7f9fc;border:1px solid #e1e9f2;color:#71889c}
.presentation-notice.okay{background:#eef8f5;border:1px solid #d0e8df;color:#377b6a}
.presentation-fields{display:grid;gap:15px;margin:22px 0}.presentation-fields>strong{font-size:13px;color:#315b80}
.presentation-fields label{display:grid;gap:8px;font-size:12px;color:#3e617f}
.presentation-fields label span small{color:#a4824e;font-size:10px;margin-left:6px}
.presentation-fields input,.presentation-fields select{border:1px solid #d5e3f0;border-radius:10px;background:white;padding:12px;font:inherit;font-size:12px;color:#325675;box-sizing:border-box;width:100%}
.presentation-fields>p{font-size:11px;color:#8298ac;margin:0}
.presentation-empty-fields{padding:20px;border:1px dashed #d4e3f0;border-radius:12px;margin:20px 0}
.presentation-empty-fields strong{font-size:12px;color:#6e879d}.presentation-empty-fields p{font-size:11px;color:#8ba0b0;line-height:1.6;margin:7px 0 0}
.presentation-relations{border-top:1px solid #e8edf3;margin:19px 0 0;padding-top:14px;display:grid;gap:7px}
.presentation-relations strong{font-size:11px;color:#345f83}.presentation-relations p{font-size:11px;color:#71889c;margin:0}
.presentation-relations small{font-size:10px;color:#99a8b6}
.presentation-actions{display:flex;justify-content:space-between;align-items:center;gap:9px;margin-top:30px}
.presentation-actions button{background:white;border:1px solid #cedfec;color:#376993;border-radius:10px;padding:11px 14px;font-size:11px;font-weight:700;cursor:pointer}
.presentation-actions button:disabled{opacity:.35;cursor:not-allowed}.presentation-actions span{font-size:10px;color:#a2b2c1}
.presentation footer{border-top:1px solid #e8eef5;padding:13px 27px;background:#fcfdff;font-size:11px;color:#869bac;line-height:1.55}
@media(max-width:760px){.presentation-head{flex-wrap:wrap;padding:18px}.presentation-body{grid-template-columns:1fr}.presentation-nav{max-height:270px;border-right:0;border-bottom:1px solid #e4edf6}.presentation-detail{padding:22px}.presentation-metrics div{padding:12px}.presentation footer{padding:12px}}
</style>
