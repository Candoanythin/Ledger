# -*- coding: utf-8 -*-
import io

path = 'index.html'
with io.open(path, 'r', encoding='utf-8') as f:
    content = f.read()

changed = 0

def apply(old, new):
    global content, changed
    if old not in content:
        print('NOT FOUND:', repr(old[:90]))
        return False
    content = content.replace(old, new, 1)
    changed += 1
    return True

# 1. File input accept: add .pdf
apply(
    'accept=".xls,.xlsx,.csv,.html,.htm,text/csv"',
    'accept=".pdf,.xls,.xlsx,.csv,.html,.htm,text/csv"'
)

# 2. Update info text in import dialog
apply(
    'HTML 형식 XLS 및 CSV/텍스트 형식 XLS는 자동 분석합니다. 구형 Excel 바이너리 XLS는 개인정보 보호를 위해 외부 라이브러리를 쓰지 않으므로, Excel에서 <b>다른 이름으로 저장 → CSV UTF-8</b> 후 가져오면 됩니다.',
    'PDF·HTML·CSV·텍스트 형식은 자동 분석합니다. Excel 바이너리 XLS는 개인정보 보호를 위해 외부 라이브러리를 쓰지 않으므로, Excel에서 <b>다른 이름으로 저장 → CSV UTF-8</b> 후 가져오면 됩니다. (스캔된 이미지 PDF는 텍스트가 없어 분석되지 않습니다.)'
)

# 3. Add pdfText and pdfRows functions before decodeBuffer
apply(
    'function decodeBuffer(buf)',
    '''async function pdfText(buf){
 const bytes=new Uint8Array(buf),latin=new TextDecoder('latin1').decode(bytes);
 const chunks=[];let pos=0;
 while(true){
  const s=latin.indexOf('stream',pos);if(s<0)break;
  let start=s+6;
  while(start<latin.length&&(latin[start]==='\\r'||latin[start]==='\\n'))start++;
  const e=latin.indexOf('endstream',start);if(e<0)break;
  const raw=latin.slice(start,e);
  const rawBytes=Uint8Array.from(raw,c=>c.charCodeAt(0)&0xFF);
  let decoded='';
  try{decoded=await new Response(new Blob([rawBytes]).stream().pipeThrough(new DecompressionStream('deflate'))).text()}
  catch{try{decoded=await new Response(new Blob([rawBytes]).stream().pipeThrough(new DecompressionStream('deflate-raw'))).text()}catch{decoded=raw}}
  if(/[Tj]|TJ|(?:^|[^A-Za-z])(?:Td|TD|Tm|T\\*)|(?:^|[^A-Za-z])BT/.test(decoded))chunks.push(decoded);
  pos=e+9;
 }
 const content=chunks.join('\\n');
 const parts=[];
 const segments=content.split(/(?:^|[^A-Za-z])(?:BT|ET|Td|TD|Tm|T\\*)(?:[^A-Za-z]|$)/);
 for(const seg of segments){
  const texts=seg.match(/\\((?:\\.|[^\\()])*\\)/g)||[];
  if(texts.length){
   const decoded=texts.map(s=>s.slice(1,-1).replace(/\\([nrtbf()\\\\])/g,(_,c)=>({n:'\\n',r:'\\r',t:'\\t',b:'\\b',f:'\\f','(':'(',')':')','\\\\':'\\\\'}[c]||c)));
   parts.push(decoded.join(' '));
  }
 }
 const out=parts.join('\\n');
 return out||clean(content).replace(/\\s+/g,' ');
}
function pdfRows(text){
 return text.split(/\\n/).map(l=>l.split(/\\s{2,}/).map(x=>clean(x))).filter(r=>r.some(Boolean));
}
function decodeBuffer(buf)'''
)

# 4. analyzeStatements: detect PDF (using single quotes as in actual file)
apply(
    r"""const buf=await file.arrayBuffer(),sig=Array.from(new Uint8Array(buf).slice(0,8)).map(x=>x.toString(16).padStart(2,'0')).join(''),isExcel=sig.startsWith('d0cf11e0')||sig.startsWith('504b0304');const text=isExcel?'':decodeBuffer(buf),rows=isExcel?spreadsheetRows(buf):/<(?:html|table|tr)[\s>]/i.test(text)?tableRows(text):textRows(text),meta=metaFromText(isExcel?rows.flat().join(' '):text,file.name),fileId=await digestFile(file);""",
    r"""const buf=await file.arrayBuffer(),sig=Array.from(new Uint8Array(buf).slice(0,8)).map(x=>x.toString(16).padStart(2,'0')).join(''),isPdf=sig.startsWith('25504446'),isExcel=sig.startsWith('d0cf11e0')||sig.startsWith('504b0304');const text=isExcel?'':isPdf?await pdfText(buf):decodeBuffer(buf),rows=isExcel?spreadsheetRows(buf):isPdf?pdfRows(text):/<(?:html|table|tr)[\s>]/i.test(text)?tableRows(text):textRows(text),meta=metaFromText(isExcel?rows.flat().join(' '):text,file.name),fileId=await digestFile(file);"""
)

with io.open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('CHANGED:', changed)