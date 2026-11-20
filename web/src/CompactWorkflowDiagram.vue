<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Node, Edge } from '@vue-flow/core'
import { buildCompactLayout } from './compactFlowLayout'

type StageInfo={label?:string;kind?:string;role?:string|null;config?:{source_step?:string;actor_side?:string}}
const props=defineProps<{
 orderedNodes:Node[]
 edges:Edge[]
 selectedNodeId:string|null
 selectedEdgeId:string|null
}>()
const emit=defineEmits<{
 (event:'selectNode',id:string):void
 (event:'selectEdge',id:string):void
}>()
const hoveredEdge=ref<string|null>(null)
const diagram=computed(()=>buildCompactLayout(
 props.orderedNodes.map(n=>n.id),
 props.edges.map(e=>({id:e.id,source:e.source,target:e.target}))
))
const cards=computed(()=>diagram.value.points.map(point=>{
 const node=props.orderedNodes[point.index]
 const data=(node.data||{}) as StageInfo
 return {...point,label:data.label||node.id,kind:data.kind||'FORM',
   step:data.config?.source_step||(data.kind==='START'?'INICIO':'FIN'),
   role:data.role||'Por definir',side:data.config?.actor_side}
}))
function sideLabel(side?:string){
 return side==='CONTRATISTA'?'Prestador':side==='CONTRATANTE'?'Contratante':'Por confirmar'
}
function edgeLabel(edgeId:string){
 const edge=props.edges.find(e=>e.id===edgeId)
 const first=cards.value.find(p=>p.id===edge?.source)
 const second=cards.value.find(p=>p.id===edge?.target)
 return 'Editar conexión: '+(first?.label||'Origen')+' → '+(second?.label||'Destino')
}
</script>

<template>
 <div class="compact-flow-scroll" role="region" aria-label="Diagrama completo del proceso en varias columnas" tabindex="0">
  <div class="compact-flow-board" :style="{width:diagram.width+'px',height:diagram.height+'px'}">
   <svg class="compact-flow-arrows" :width="diagram.width" :height="diagram.height"
      :viewBox="'0 0 '+diagram.width+' '+diagram.height" aria-label="Conexiones del proceso">
      <defs>
       <marker id="smart-flow-arrow" viewBox="0 0 12 12" markerWidth="11" markerHeight="11"
         refX="11" refY="6" orient="auto" markerUnits="userSpaceOnUse">
         <path d="M 2 2 L 11 6 L 2 10" fill="none" stroke="#5a8dbd" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
       </marker>
       <marker id="smart-flow-arrow-active" viewBox="0 0 12 12" markerWidth="11" markerHeight="11"
         refX="11" refY="6" orient="auto" markerUnits="userSpaceOnUse">
         <path d="M 2 2 L 11 6 L 2 10" fill="none" stroke="#146ad0" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/>
       </marker>
      </defs>
      <g v-for="edge in diagram.segments" :key="edge.id" class="compact-flow-segment">
        <path :d="edge.path" class="compact-flow-route"
          :class="{active:selectedEdgeId===edge.id||hoveredEdge===edge.id}"
          :marker-end="selectedEdgeId===edge.id||hoveredEdge===edge.id?'url(#smart-flow-arrow-active)':'url(#smart-flow-arrow)'"/>
        <path :d="edge.path" class="compact-flow-route-hit" fill="none" stroke="transparent"
          stroke-width="20" tabindex="0" role="button" :aria-label="edgeLabel(edge.id)"
          @mouseenter="hoveredEdge=edge.id" @mouseleave="hoveredEdge=null"
          @focus="hoveredEdge=edge.id" @blur="hoveredEdge=null"
          @click="emit('selectEdge',edge.id)"
          @keydown.enter.prevent="emit('selectEdge',edge.id)"
          @keydown.space.prevent="emit('selectEdge',edge.id)">
          <title>{{edgeLabel(edge.id)}}</title>
        </path>
      </g>
   </svg>
   <button v-for="card in cards" :key="card.id" type="button"
      class="compact-flow-card"
      :class="{selected:selectedNodeId===card.id,
        start:card.kind==='START',end:card.kind==='END'}"
      :style="{left:card.x+'px',top:card.y+'px'}"
      :aria-pressed="selectedNodeId===card.id"
      @click="emit('selectNode',card.id)">
       <span class="compact-flow-step">{{card.step}}</span>
       <span class="compact-flow-card-body">
         <strong>{{card.label}}</strong>
         <small v-if="card.kind!=='START'&&card.kind!=='END'">{{card.role}} · {{sideLabel(card.side)}}</small>
       </span>
   </button>
  </div>
 </div>
</template>

<style scoped>
.compact-flow-scroll{flex:1;min-height:0;width:100%;overflow:auto;background:#f8fbff;
 background-image:radial-gradient(#dce7f3 .7px,transparent .7px);background-size:22px 22px;
 scrollbar-color:#bccfe5 transparent;scrollbar-width:thin}
.compact-flow-board{position:relative;min-width:0;margin:0 auto}
.compact-flow-arrows{position:absolute;inset:0;overflow:visible;pointer-events:none}
.compact-flow-route{fill:none;stroke:#80a8cd;stroke-width:2.4;stroke-linejoin:round;stroke-linecap:round;transition:stroke .12s}
.compact-flow-route.active{stroke:#176ccf;stroke-width:3.1}
.compact-flow-route-hit{pointer-events:stroke;cursor:pointer}
.compact-flow-card{position:absolute;z-index:2;width:205px;height:94px;display:flex;align-items:center;gap:9px;
 padding:10px 10px 10px 9px;border:1px solid #ccdeef;border-left:4px solid #4687d4;border-radius:12px;
 background:white;box-shadow:0 3px 13px rgba(29,71,113,.055);text-align:left;cursor:pointer;
 color:#254d71;box-sizing:border-box;overflow:hidden}
.compact-flow-card:hover,.compact-flow-card.selected,.compact-flow-card:focus-visible{
 border-color:#3c82d0;background:#edf6ff;box-shadow:0 0 0 3px rgba(49,113,190,.12);outline:0}
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
</style>
