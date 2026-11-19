<script setup lang="ts">
import { computed, ref } from 'vue'
import { VueFlow, type Node, type Edge } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

type Screen = 'resumen' | 'contrataciones' | 'flujos' | 'prestadores' | 'maira' | 'configuracion'
const current = ref<Screen>('flujos')
const menu: {key: Screen; title: string; glyph: string}[] = [
  { key: 'resumen', title: 'Resumen', glyph: '▦' },
  { key: 'contrataciones', title: 'Contrataciones', glyph: '▤' },
  { key: 'prestadores', title: 'Prestadores', glyph: '⌂' },
  { key: 'flujos', title: 'Flujos', glyph: '◇' },
  { key: 'maira', title: 'MAIRA', glyph: '✳' },
  { key: 'configuracion', title: 'Configuración', glyph: '⚙' }
]
const selected = computed(() => menu.find(m => m.key === current.value)?.title || '')
// Reference layout only; persisted tenant-scoped workflow editing is not yet integrated.
const nodes = ref<Node[]>([
  { id: 'start', type: 'input', position: { x: 225, y: 20 }, data: { label: 'Inicio de proceso' } },
  { id: 'document', position: { x: 225, y: 115 }, data: { label: 'Revisión documental' } },
  { id: 'legal', position: { x: 65, y: 220 }, data: { label: 'Jurídica' } },
  { id: 'finance', position: { x: 385, y: 220 }, data: { label: 'Financiera' } },
  { id: 'contract', position: { x: 225, y: 325 }, data: { label: 'Contrato' } },
  { id: 'end', type: 'output', position: { x: 225, y: 425 }, data: { label: 'Formalización' } }
])
const edges = ref<Edge[]>([
  { id:'e1',source:'start',target:'document' },
  { id:'e2',source:'document',target:'legal' },
  { id:'e3',source:'document',target:'finance' },
  { id:'e4',source:'legal',target:'contract' },
  { id:'e5',source:'finance',target:'contract' },
  { id:'e6',source:'contract',target:'end' }
])
</script>
<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark">S</div><div><strong>Smart Contract</strong><small>Workflow platform</small></div></div>
      <nav><button v-for="entry in menu" :key="entry.key" :class="{active:current===entry.key}" @click="current=entry.key">
        <span>{{ entry.glyph }}</span>{{ entry.title }}</button></nav>
      <div class="sidebar-foot">MAIRA · Smart Alliance</div>
    </aside>
    <main class="main">
      <header><div><small>Smart Contract / {{ selected }}</small><h1>{{ selected }}</h1></div><div class="context-pill">Arquitectura inicial</div></header>
      <section v-if="current==='flujos'" class="stack">
        <div class="heading"><div><h2>Diseñador de workflows</h2><p>Motor de etapas, reglas y dependencias configurable por institución.</p></div></div>
        <div class="workspace"><div class="workspace-heading"><strong>Vista de referencia</strong><span>Sin datos contractuales de clientes</span></div>
        <VueFlow v-model:nodes="nodes" v-model:edges="edges" :fit-view-on-init="true" :nodes-draggable="true" :nodes-connectable="false" :elements-selectable="true" :min-zoom="0.4" :max-zoom="1.5" /></div>
        <p class="notice">La edición persistente, publicación y simulación desde la interfaz se conectarán al backend en el siguiente paquete.</p>
      </section>
      <section v-else class="empty"><div class="empty-icon">{{ menu.find(m=>m.key===current)?.glyph }}</div><h2>{{ selected }}</h2>
        <p>Sección prevista en la arquitectura multiempresa. Todavía no hay datos operativos ni funcionalidades activadas.</p></section>
    </main>
  </div>
</template>
