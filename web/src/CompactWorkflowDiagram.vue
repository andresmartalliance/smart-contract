<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import type { Node, Edge } from '@vue-flow/core'
import { buildEditableLayout } from './compactFlowLayout'

type Position={x:number;y:number}
type StageInfo={label?:string;kind?:string;role?:string|null;config?:{source_step?:string;actor_side?:string}}
type DragState={id:string;pointerId:number;startX:number;startY:number;origin:Position;moved:boolean}
type PanState={pointerId:number;startX:number;startY:number;scrollX:number;scrollY:number}
const props=defineProps<{
 orderedNodes:Node[]
 edges:Edge[]
 manualPositions?:Record<string,Position>|null
 selectedNodeId:string|null
 selectedEdgeId:string|null
}>()
const emit=defineEmits<{
 (event:'selectNode',id:string):void
 (event:'selectEdge',id:string):void
 (event:'moveNode',id:string,position:Position):void
 (event:'organize'):void
 (event:'connect',source:string,target:string):void
}>()
const viewport=ref<HTMLElement|null>(null)
const hoveredEdge=ref<string|null>(null)
const zoom=ref(.9)
const previewPosition=ref<{id:string;position:Position}|null>(null)
const drag=ref<DragState|null>(null)
const pan=ref<PanState|null>(null)
const suppressClick=ref<string|null>(null)
const connectMode=ref(false)
const connectionSource=ref<string|null>(null)
const combinedPositions=computed<Record<string,Position>>(()=>{
 const combined={...(props.manualPositions||{})}
 if(previewPosition.value)combined[previewPosition.value.id]=previewPosition.value.position
 return combined
})
const diagram=computed(()=>buildEditableLayout(
 props.orderedNodes.map(n=>n.id),
 props.edges.map(e=>({id:e.id,source:e.source,target:e.target})),
 combinedPositions.value
))
const cards=computed(()=>diagram.value.points.map(point=>{
 const node=props.orderedNodes[point.index]
 const data=(node.data||{}) as StageInfo
 return {...point,label:data.label||node.id,kind:data.kind||'FORM',
  step:data.config?.source_step||(data.kind==='START'?'INICIO':'FIN'),
  role:data.role||'Por definir',side:data.config?.actor_side}
}))
const pendingText=computed(()=>{
 if(!connectMode.value)return 'Arrastra las etapas para moverlas. Arrastra el fondo para desplazarte. Selecciona una flecha para editar su condición.'
 return connectionSource.value?'Selecciona la etapa de destino para completar la conexión.':'Selecciona la etapa de origen.'
})
function sideLabel(side?:string){
 return side==='CONTRATISTA'?'Prestador':side==='CONTRATANTE'?'Contratante':'Por confirmar'
}
function edgeLabel(edgeId:string){
 const edge=props.edges.find(e=>e.id===edgeId)
 const first=cards.value.find(p=>p.id===edge?.source)
 const second=cards.value.find(p=>p.id===edge?.target)
 return 'Editar conexión: '+(first?.label||'Origen')+' → '+(second?.label||'Destino')
}
function activateCard(id:string){
 if(suppressClick.value===id){suppressClick.value=null;return}
 if(!connectMode.value){emit('selectNode',id);return}
 if(!connectionSource.value){connectionSource.value=id;return}
 if(connectionSource.value!==id)emit('connect',connectionSource.value,id)
 connectionSource.value=null
 connectMode.value=false
}
function toggleConnect(){
 connectMode.value=!connectMode.value
 connectionSource.value=null
}
function startCardDrag(event:PointerEvent,card:{id:string;x:number;y:number}){
 if(event.button!==0||connectMode.value)return
 drag.value={id:card.id,pointerId:event.pointerId,startX:event.clientX,startY:event.clientY,
   origin:{x:card.x,y:card.y},moved:false}
 ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
}
function moveCard(event:PointerEvent){
 const d=drag.value
 if(!d||event.pointerId!==d.pointerId)return
 const dx=(event.clientX-d.startX)/zoom.value
 const dy=(event.clientY-d.startY)/zoom.value
 if(!d.moved&&Math.hypot(dx,dy)<4)return
 d.moved=true
 previewPosition.value={id:d.id,position:{x:Math.max(0,Math.round(d.origin.x+dx)),
   y:Math.max(0,Math.round(d.origin.y+dy))}}
}
function finishCard(event:PointerEvent,commit:boolean){
 const d=drag.value
 if(!d||d.pointerId!==event.pointerId)return
 if(d.moved&&previewPosition.value){
  suppressClick.value=d.id
  if(commit){
   const target=previewPosition.value.position
   emit('moveNode',d.id,target)
   emit('selectNode',d.id)
  }
 }
 drag.value=null
 previewPosition.value=null
}
function moveByKeyboard(event:KeyboardEvent,card:{id:string;x:number;y:number}){
 const directions:Record<string,Position>={
  ArrowLeft:{x:-12,y:0},ArrowRight:{x:12,y:0},
  ArrowUp:{x:0,y:-12},ArrowDown:{x:0,y:12}
 }
 const change=directions[event.key]
 if(!change||connectMode.value)return
 event.preventDefault()
 emit('moveNode',card.id,{x:Math.max(0,card.x+change.x),y:Math.max(0,card.y+change.y)})
 emit('selectNode',card.id)
}
function startPan(event:PointerEvent){
 if(event.button!==0||drag.value)return
 const el=event.target
 if(el instanceof Element&&el.closest('button,[role="button"]'))return
 const area=viewport.value
 if(!area)return
 pan.value={pointerId:event.pointerId,startX:event.clientX,startY:event.clientY,
  scrollX:area.scrollLeft,scrollY:area.scrollTop}
 area.setPointerCapture(event.pointerId)
}
function movePan(event:PointerEvent){
 const p=pan.value,area=viewport.value
 if(!p||!area||p.pointerId!==event.pointerId)return
 area.scrollLeft=p.scrollX-(event.clientX-p.startX)
 area.scrollTop=p.scrollY-(event.clientY-p.startY)
}
function stopPan(event:PointerEvent){
 if(pan.value?.pointerId===event.pointerId)pan.value=null
}
async function setZoom(scale:number){
 const next=Math.max(.55,Math.min(1.65,Math.round(scale*100)/100))
 const area=viewport.value
 const prev=zoom.value
 if(!area||next===prev)return
 const centerX=(area.scrollLeft+area.clientWidth/2)/prev
 const centerY=(area.scrollTop+area.clientHeight/2)/prev
 zoom.value=next
 await nextTick()
 area.scrollLeft=centerX*next-area.clientWidth/2
 area.scrollTop=centerY*next-area.clientHeight/2
}
async function fitDiagram(){
 const area=viewport.value
 if(!area)return
 zoom.value=Math.max(.55,Math.min(1.15,(area.clientWidth-18)/diagram.value.width))
 await nextTick()
 area.scrollLeft=0
 area.scrollTop=0
}
</script>

<template>
 <section class="compact-flow-editor">
  <div class="compact-flow-toolbar">
   <span class="compact-flow-helper">{{pendingText}}</span>
   <div class="compact-flow-tools">
    <button type="button" :class="{selected:connectMode}" :aria-pressed="connectMode"
      @click="toggleConnect">{{connectMode?'Cancelar conexión':'Conectar etapas'}}</button>
    <button type="button" @click="emit('organize')">Organizar</button>
    <button type="button" aria-label="Reducir zoom" @click="setZoom(zoom-.15)">−</button>
    <span class="compact-flow-zoom">{{Math.round(zoom*100)}}%</span>
    <button type="button" aria-label="Aumentar zoom" @click="setZoom(zoom+.15)">+</button>
    <button type="button" @click="fitDiagram">Ajustar</button>
   </div>
  </div>
  <div ref="viewport" class="compact-flow-scroll"
    :class="{panning:pan!==null}"
    role="region" aria-label="Lienzo editable del workflow" tabindex="0"
    @pointerdown="startPan" @pointermove="movePan" @pointerup="stopPan" @pointercancel="stopPan">
   <div class="compact-flow-scaled" :style="{
      width:diagram.width*zoom+'px',height:diagram.height*zoom+'px'}">
    <div class="compact-flow-board" :style="{
      width:diagram.width+'px',height:diagram.height+'px',
      transform:'scale('+zoom+')'}">
     <svg class="compact-flow-arrows" :width="diagram.width" :height="diagram.height"
        :viewBox="'0 0 '+diagram.width+' '+diagram.height" aria-label="Conexiones">
       <defs>
        <marker id="smart-flow-arrow" viewBox="0 0 12 12" markerWidth="10" markerHeight="10"
          refX="11" refY="6" orient="auto" markerUnits="userSpaceOnUse">
          <path d="M 2 2 L 11 6 L 2 10" fill="none" stroke="#568bbd" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </marker>
        <marker id="smart-flow-arrow-active" viewBox="0 0 12 12" markerWidth="10" markerHeight="10"
          refX="11" refY="6" orient="auto" markerUnits="userSpaceOnUse">
          <path d="M 2 2 L 11 6 L 2 10" fill="none" stroke="#116bd3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </marker>
       </defs>
       <g v-for="edge in diagram.segments" :key="edge.id" class="compact-flow-segment">
        <path :d="edge.path" class="compact-flow-route"
          :class="{active:selectedEdgeId===edge.id||hoveredEdge===edge.id}"
          :marker-end="selectedEdgeId===edge.id||hoveredEdge===edge.id?'url(#smart-flow-arrow-active)':'url(#smart-flow-arrow)'"/>
        <path :d="edge.path" class="compact-flow-route-hit" fill="none" stroke="transparent"
          stroke-width="19" tabindex="0" role="button" :aria-label="edgeLabel(edge.id)"
          @mouseenter="hoveredEdge=edge.id" @mouseleave="hoveredEdge=null"
          @focus="hoveredEdge=edge.id" @blur="hoveredEdge=null"
          @click="emit('selectEdge',edge.id)" @keydown.enter.prevent="emit('selectEdge',edge.id)"
          @keydown.space.prevent="emit('selectEdge',edge.id)">
          <title>{{edgeLabel(edge.id)}}</title>
        </path>
       </g>
     </svg>
     <button v-for="card in cards" :key="card.id" type="button"
      class="compact-flow-card" :class="{
       selected:selectedNodeId===card.id,
       source:connectMode&&connectionSource===card.id,
       dragging:drag?.id===card.id,
       start:card.kind==='START',end:card.kind==='END'}"
      :style="{left:card.x+'px',top:card.y+'px'}"
      :aria-pressed="selectedNodeId===card.id"
      :aria-label="'Mover o editar '+card.label"
      @pointerdown="startCardDrag($event,card)" @pointermove="moveCard"
      @pointerup="finishCard($event,true)" @pointercancel="finishCard($event,false)"
      @keydown="moveByKeyboard($event,card)" @click="activateCard(card.id)">
       <span class="compact-flow-step">{{card.step}}</span>
       <span class="compact-flow-card-body">
         <strong>{{card.label}}</strong>
         <small v-if="card.kind!=='START'&&card.kind!=='END'">{{card.role}} · {{sideLabel(card.side)}}</small>
       </span>
     </button>
    </div>
   </div>
  </div>
  <div v-if="connectMode" class="compact-flow-connecting" role="status">
    {{connectionSource?'Origen seleccionado. Haz clic en el destino.':'Selecciona la primera etapa para crear una relación.'}}
  </div>
 </section>
</template>

<style scoped>
.compact-flow-editor{flex:1;min-width:0;min-height:0;display:flex;flex-direction:column}
.compact-flow-toolbar{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap;
 padding:10px 12px;background:#fff;border-bottom:1px solid #e2edf7;flex:none}
.compact-flow-helper{font-size:10px;line-height:1.5;color:#67829c;flex:1;min-width:200px}
.compact-flow-tools{display:flex;align-items:center;gap:5px;flex-wrap:wrap}
.compact-flow-tools button{border:1px solid #d4e5f5;background:#fff;border-radius:8px;padding:7px 9px;
 font-size:11px;font-weight:700;color:#356e9f;cursor:pointer;white-space:nowrap}
.compact-flow-tools button:hover,.compact-flow-tools button.selected{background:#e9f4ff;border-color:#9fc4eb}
.compact-flow-zoom{color:#7289a1;font-size:10px;min-width:34px;text-align:center;font-variant-numeric:tabular-nums}
.compact-flow-scroll{flex:1;min-height:0;width:100%;overflow:auto;background:#f8fbff;
 background-image:radial-gradient(#dce7f3 .7px,transparent .7px);background-size:22px 22px;
 scrollbar-color:#bdcee3 transparent;scrollbar-width:thin;cursor:grab}
.compact-flow-scroll.panning{cursor:grabbing}
.compact-flow-scaled{position:relative;margin:0 auto}
.compact-flow-board{position:relative;min-width:0;transform-origin:0 0}
.compact-flow-arrows{position:absolute;inset:0;overflow:visible;pointer-events:none}
.compact-flow-route{fill:none;stroke:#80a8cd;stroke-width:2.4;stroke-linejoin:round;stroke-linecap:round;transition:stroke .12s}
.compact-flow-route.active{stroke:#176ccf;stroke-width:3.1}
.compact-flow-route-hit{pointer-events:stroke;cursor:pointer}
.compact-flow-card{position:absolute;z-index:2;width:205px;height:94px;display:flex;align-items:center;gap:9px;
 padding:10px 10px 10px 9px;border:1px solid #ccdeef;border-left:4px solid #4687d4;border-radius:12px;
 background:white;box-shadow:0 3px 13px rgba(29,71,113,.055);text-align:left;cursor:grab;box-sizing:border-box;
 overflow:hidden;touch-action:none;user-select:none;-webkit-user-select:none;color:#254d71}
.compact-flow-card.dragging{cursor:grabbing;z-index:5;box-shadow:0 8px 25px rgba(25,91,159,.19);border-color:#337bd2}
.compact-flow-card:hover,.compact-flow-card.selected,.compact-flow-card:focus-visible{
 border-color:#3c82d0;background:#edf6ff;box-shadow:0 0 0 3px rgba(49,113,190,.12);outline:0}
.compact-flow-card.source{outline:3px solid #359d84;outline-offset:2px}
.compact-flow-card.start{background:#eaf3ff;border-left-color:#377bd5}
.compact-flow-card.end{background:#ecfaf4;border-left-color:#26a98d}
.compact-flow-step{width:34px;height:31px;flex:none;display:grid;place-items:center;border-radius:8px;
 padding:0 2px;box-sizing:border-box;background:#e8f2fc;color:#3273b7;font-weight:800;font-size:10px}
.compact-flow-card.end .compact-flow-step{background:#dbf4eb;color:#148a6c}
.compact-flow-card-body{min-width:0;display:grid;gap:6px}
.compact-flow-card-body strong{font-size:11.5px;line-height:1.36;font-weight:750;color:#244a6d;
 display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;overflow-wrap:anywhere}
.compact-flow-card-body small{font-size:9.8px;line-height:1.35;color:#7891a7;
 display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.compact-flow-connecting{background:#edf9f4;color:#397b69;padding:8px 12px;font-size:11px;border-top:1px solid #ceeadf}
@media(max-width:700px){.compact-flow-tools{gap:3px}.compact-flow-tools button{padding:6px}
.compact-flow-helper{min-width:0}.compact-flow-toolbar{align-items:flex-start}}
</style>
