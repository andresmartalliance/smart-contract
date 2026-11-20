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
