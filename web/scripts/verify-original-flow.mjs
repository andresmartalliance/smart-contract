/**
 * Design contract: first exercise comes from the original two-page PDF.
 * No accidental return to the two-node demo or unrelated Famisanar seed.
 * Uses the TypeScript compiler already present in the web dependencies.
 */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'

const path=new URL('../src/originalContractFlow.ts',import.meta.url)
const source=fs.readFileSync(path,'utf8')
const {outputText}=ts.transpileModule(source,{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
})
const cjs={exports:{}}
vm.runInNewContext(outputText,{exports:cjs.exports,module:cjs},{timeout:5000})
const {buildOriginalContractFlow}=cjs.exports
assert.equal(typeof buildOriginalContractFlow,'function')
const flow=buildOriginalContractFlow()
assert.equal(flow.key,'SMART_CICLO_CONTRATACION_V2')
assert.equal(flow.metadata.source,'smart-contract-original-pdf')
assert.equal(flow.nodes.length,25,'23 original activities + start + end')
assert.equal(flow.edges.length,24,'24 arrows in original two-page diagram')
const steps=flow.nodes.filter(n=>n.config.source_step)
assert.equal(steps.length,23)
assert.equal(steps[0].config.source_step,'1')
assert.equal(steps.at(-1).config.source_step,'13')
assert.equal(steps.filter(n=>n.config.source_page===1).length,11)
assert.equal(steps.filter(n=>n.config.source_page===2).length,12)
assert.equal(new Set(steps.map(n=>n.config.source_step)).size,23)
assert.deepEqual([...steps.filter(n=>n.role==='ASPIRANTE').map(n=>n.config.source_step)],['2','8'])
assert.equal(steps.filter(n=>n.config.actor_side==='CONTRATISTA').length,2)
assert.equal(steps.filter(n=>n.config.actor_side==='CONTRATANTE').length,21)
assert.ok(steps.every(n=>n.config.fields.length===0),'do not invent form fields absent from the PDF')
assert.ok(steps.every(n=>n.config.source_excerpt&&n.config.source_confidence==='alta'))
assert.equal(flow.metadata.maira_dialogue.completed,false)
for(let i=0;i<flow.edges.length;i++){
  assert.equal(flow.edges[i].source,flow.nodes[i].id,'continuous original source arrow')
  assert.equal(flow.edges[i].target,flow.nodes[i+1].id,'continuous original target arrow')
}
const app=fs.readFileSync(new URL('../src/App.vue',import.meta.url),'utf8')
assert.ok(app.includes('loadOriginalContractFlowDraft()'))
assert.ok(!app.includes('loadFamisanarCaseDraft'), 'the unrelated case must not override the first exercise')
assert.ok(!app.includes('Caso Famisanar · Prefactibilidad'),'no unrelated navigation')
assert.ok(app.includes('archivedPilotDraft'),'preserve the retired two-node demo')
console.log('Original PDF verified: 23 numbered tasks, 25 nodes, 24 edges, 21/2 actor sides; no invented form fields.')

// Connected diagram regression: its links are generated from actual workflow edges.
assert.ok(app.includes('const directedChain=computed('))
assert.ok(app.includes('edges.value.length!==ordered.length-1'))
assert.ok(app.includes('const compactSavedPositions=computed<'))
assert.ok(app.includes('<CompactWorkflowDiagram v-if="!freeformMode"'))
assert.ok(app.includes('@select-edge="selectCompactEdge"'))
assert.ok(!app.includes('Editar conexión</span>'),'remove repeated edge editing pills')


// Geometry regression: compact snake positions; every route touches two actual nodes.
const compactSource=fs.readFileSync(new URL('../src/compactFlowLayout.ts',import.meta.url),'utf8')
const compactJS=ts.transpileModule(compactSource,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText
const compactExports={exports:{}}
vm.runInNewContext(compactJS,{exports:compactExports.exports,module:compactExports},{timeout:5000})
const {buildCompactLayout,buildEditableLayout,COMPACT_CARD_WIDTH,COMPACT_CARD_HEIGHT,COMPACT_GAP_X,COMPACT_GAP_Y}=compactExports.exports
const ids=flow.nodes.map(n=>n.id)
const edges=flow.edges.map((e,i)=>({id:'edge_'+i,source:e.source,target:e.target}))
const diagram=buildCompactLayout(ids,edges)
assert.equal(diagram.points.length,25)
assert.equal(diagram.segments.length,24)
assert.equal(diagram.width,971)
assert.ok(diagram.height<1200,'compact view must fit within ~7 rows')
assert.equal(diagram.points[0].row,0)
assert.equal(diagram.points[3].col,3)
assert.equal(diagram.points[4].col,3,'snake must turn vertically at row boundary')
assert.equal(diagram.points[7].col,0)
for(const [i,edge] of diagram.segments.entries()){
 const first=diagram.points[i],next=diagram.points[i+1]
 assert.equal(edge.source,first.id)
 assert.equal(edge.target,next.id)
 assert.equal(edge.id,'edge_'+i)
 assert.equal(edge.orientation,first.row===next.row?'horizontal':'vertical')
 if(first.row===next.row){
   assert.equal(Math.abs(edge.to.x-edge.from.x),COMPACT_GAP_X)
   assert.equal(edge.from.y,first.y+COMPACT_CARD_HEIGHT/2)
   assert.equal(edge.to.y,next.y+COMPACT_CARD_HEIGHT/2)
 }else{
   assert.equal(edge.from.y,first.y+COMPACT_CARD_HEIGHT)
   assert.equal(edge.to.y,next.y)
   assert.equal(edge.to.y-edge.from.y,COMPACT_GAP_Y)
   assert.equal(first.col,next.col)
 }
}
assert.ok(fs.readFileSync(new URL('../src/CompactWorkflowDiagram.vue',import.meta.url),'utf8').includes('compact-flow-arrows'))
console.log('Compact flow verified: 25 readable cards, 24 actual continuous routes, 7 rows, no intersections.')


// Genuine editable canvas regression: movement, panning, linking, persisted coordinates.
const editable=buildEditableLayout(ids,edges)
assert.equal(editable.points.length,25)
assert.equal(editable.segments.length,24)
assert.equal(editable.points[0].x,diagram.points[0].x)
const moved=buildEditableLayout(ids,edges,{[ids[1]]:{x:1250,y:190}})
assert.equal(moved.points[1].x,1250)
assert.equal(moved.points[1].y,190)
assert.ok(moved.width>=1475,'board expands when a node is dragged right')
assert.notEqual(moved.segments[0].path,editable.segments[0].path,'edges follow moved stages')
assert.notEqual(moved.segments[1].path,editable.segments[1].path,'all incident routes follow movement')
const extra=buildEditableLayout(ids,[...edges,{id:'new_branch',source:ids[1],target:ids[4]}])
assert.equal(extra.segments.length,25)
assert.equal(extra.segments.at(-1).target,ids[4])
const comp=fs.readFileSync(new URL('../src/CompactWorkflowDiagram.vue',import.meta.url),'utf8')
assert.ok(comp.includes("@pointerdown=\"startCardDrag($event,card)\""))
assert.ok(comp.includes("@pointermove=\"moveCard\""))
assert.ok(comp.includes("@pointerdown=\"startPan\""))
assert.ok(comp.includes("@click=\"setZoom(zoom+.15)\""))
assert.ok(comp.includes("emit('connect',connectionSource.value,id)"))
assert.ok(app.includes("@move-node=\"onCompactMove\""))
assert.ok(app.includes("canvas_layout:'manual'"))
assert.ok(app.includes("config:{...d.config,position:{x:n.position.x,y:n.position.y}}"))
assert.ok(app.includes("'PATCH',{workflow:definition()}"))
console.log('Editable workflow verified: drag updates routed geometry, free panning, zoom, branching and persisted positions.')

// Smart Contract 3 V6.6.10: deterministic institutional canvas continuation.
assert.ok(app.includes("const studioTab=ref<'pantallas'|'editor'>('editor')"))
assert.ok(app.includes("const studioCanvasMode=ref<'guided'|'canvas'>('canvas')"))
assert.ok(app.includes("async function openInitialFirstWorkflow()"))
assert.ok(app.includes("await openInitialFirstWorkflow()"))
assert.ok(app.includes("const linkedHasChanges=computed("))
assert.ok(app.includes("linkedSavedSnapshot.value=JSON.stringify(definition())"))
assert.ok(app.includes("party.latest_process?.kind==='DESIGN'"))
assert.ok(app.includes("studioCanvasMode.value='canvas'"))
console.log('Institutional draft continuation verified: saved graph, canvas-first editing, unsaved status.')
