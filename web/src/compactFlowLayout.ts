/** Compact connected view of a directed linear workflow.
 * Geometry is independent of CSS transforms and Vue Flow handles.
 * Every route is derived from a real (source,target) edge.
 */
export const COMPACT_COLS=4
export const COMPACT_CARD_WIDTH=205
export const COMPACT_CARD_HEIGHT=94
export const COMPACT_GAP_X=37
export const COMPACT_GAP_Y=52
export const COMPACT_PAD_X=20
export const COMPACT_PAD_Y=24

export type CompactPoint={id:string;index:number;row:number;col:number;x:number;y:number}
export type CompactSegment={
 id:string;source:string;target:string;orientation:'horizontal'|'vertical';
 path:string;from:{x:number;y:number};to:{x:number;y:number}
}
export type CompactLayout={width:number;height:number;points:CompactPoint[];segments:CompactSegment[]}
export type CompactEdge={id:string;source:string;target:string}

export function buildCompactLayout(ids:string[],edges:CompactEdge[],columns=COMPACT_COLS):CompactLayout{
 if(columns<2||!Number.isInteger(columns))throw Error('La cantidad de columnas debe ser un entero mayor a uno')
 const rows=Math.max(1,Math.ceil(ids.length/columns))
 const width=COMPACT_PAD_X*2+columns*COMPACT_CARD_WIDTH+(columns-1)*COMPACT_GAP_X
 const height=COMPACT_PAD_Y*2+rows*COMPACT_CARD_HEIGHT+(rows-1)*COMPACT_GAP_Y
 const points=ids.map((id,index)=>{
  const row=Math.floor(index/columns), position=index%columns
  const col=row%2===0?position:columns-1-position
  return {id,index,row,col,
   x:COMPACT_PAD_X+col*(COMPACT_CARD_WIDTH+COMPACT_GAP_X),
   y:COMPACT_PAD_Y+row*(COMPACT_CARD_HEIGHT+COMPACT_GAP_Y)}
 })
 const segments=points.slice(0,-1).map((source,i)=>{
  const target=points[i+1]
  const edge=edges.find(e=>e.source===source.id&&e.target===target.id)
  if(!edge)throw Error('No existe conexión entre '+source.id+' y '+target.id)
  const horizontal=source.row===target.row
  const from=horizontal?
   {x:source.col<target.col?source.x+COMPACT_CARD_WIDTH:source.x,y:source.y+COMPACT_CARD_HEIGHT/2}:
   {x:source.x+COMPACT_CARD_WIDTH/2,y:source.y+COMPACT_CARD_HEIGHT}
  const to=horizontal?
   {x:source.col<target.col?target.x:target.x+COMPACT_CARD_WIDTH,y:target.y+COMPACT_CARD_HEIGHT/2}:
   {x:target.x+COMPACT_CARD_WIDTH/2,y:target.y}
  if(horizontal&&Math.abs(to.x-from.x)!==COMPACT_GAP_X)throw Error('Conexión horizontal inconsistente')
  if(!horizontal&&(source.col!==target.col||to.y-from.y!==COMPACT_GAP_Y))throw Error('Conexión vertical inconsistente')
  return {id:edge.id,source:edge.source,target:edge.target,
   orientation:horizontal?'horizontal' as const:'vertical' as const,
   path:'M '+from.x+' '+from.y+' L '+to.x+' '+to.y,from,to}
 })
 return {width,height,points,segments}
}
