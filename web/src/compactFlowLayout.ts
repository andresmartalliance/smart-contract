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


/** Editable view of the SAME graph. Optional positions are persisted per node.
 * Unlike the read-only snake helper, branching/non-sequential edges are supported.
 */
export function buildEditableLayout(
 ids:string[],edges:CompactEdge[],
 positions:Record<string,{x:number;y:number}>={},
 columns=COMPACT_COLS
):CompactLayout {
 if(columns<2||!Number.isInteger(columns))throw Error('Número de columnas inválido')
 const rows=Math.max(1,Math.ceil(ids.length/columns))
 const defaultWidth=COMPACT_PAD_X*2+columns*COMPACT_CARD_WIDTH+(columns-1)*COMPACT_GAP_X
 const defaultHeight=COMPACT_PAD_Y*2+rows*COMPACT_CARD_HEIGHT+(rows-1)*COMPACT_GAP_Y
 const points=ids.map((id,index)=>{
  const row=Math.floor(index/columns)
  const col=row%2===0?index%columns:columns-1-index%columns
  const saved=positions[id]
  return {id,index,row,col,
   x:saved&&Number.isFinite(saved.x)?Math.max(0,saved.x):COMPACT_PAD_X+col*(COMPACT_CARD_WIDTH+COMPACT_GAP_X),
   y:saved&&Number.isFinite(saved.y)?Math.max(0,saved.y):COMPACT_PAD_Y+row*(COMPACT_CARD_HEIGHT+COMPACT_GAP_Y)}
 })
 const lookup=new Map(points.map(p=>[p.id,p]))
 const segments=edges.map(edge=>{
  const a=lookup.get(edge.source),b=lookup.get(edge.target)
  if(!a||!b)throw Error('Conexión con nodo inexistente')
  const acx=a.x+COMPACT_CARD_WIDTH/2,acy=a.y+COMPACT_CARD_HEIGHT/2
  const bcx=b.x+COMPACT_CARD_WIDTH/2,bcy=b.y+COMPACT_CARD_HEIGHT/2
  const dx=bcx-acx,dy=bcy-acy
  const horizontal=Math.abs(dx)>Math.abs(dy)*.9
  let from:{x:number;y:number},to:{x:number;y:number},path:string
  if(horizontal){
   const direction=dx>=0?1:-1
   from={x:acx+direction*COMPACT_CARD_WIDTH/2,y:acy}
   to={x:bcx-direction*COMPACT_CARD_WIDTH/2,y:bcy}
   if(Math.abs(from.y-to.y)<.5)path='M '+from.x+' '+from.y+' L '+to.x+' '+to.y
   else{
    const mid=(from.x+to.x)/2
    path='M '+from.x+' '+from.y+' L '+mid+' '+from.y+' L '+mid+' '+to.y+' L '+to.x+' '+to.y
   }
  }else{
   const direction=dy>=0?1:-1
   from={x:acx,y:acy+direction*COMPACT_CARD_HEIGHT/2}
   to={x:bcx,y:bcy-direction*COMPACT_CARD_HEIGHT/2}
   if(Math.abs(from.x-to.x)<.5)path='M '+from.x+' '+from.y+' L '+to.x+' '+to.y
   else{
    const mid=(from.y+to.y)/2
    path='M '+from.x+' '+from.y+' L '+from.x+' '+mid+' L '+to.x+' '+mid+' L '+to.x+' '+to.y
   }
  }
  return {id:edge.id,source:edge.source,target:edge.target,
   orientation:horizontal?'horizontal' as const:'vertical' as const,path,from,to}
 })
 return {width:Math.max(defaultWidth,...points.map(p=>p.x+COMPACT_CARD_WIDTH+COMPACT_PAD_X)),
  height:Math.max(defaultHeight,...points.map(p=>p.y+COMPACT_CARD_HEIGHT+COMPACT_PAD_Y)),
  points,segments}
}
