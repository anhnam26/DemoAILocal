// Deliberately small Markdown subset: text is always escaped, no model-supplied HTML.
function renderAnswer(text){
  const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const inline=s=>safe(s).replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\[([A-Z0-9-]+)\]/g,'<span class="inline-citation">[$1]</span>');
  const lines=String(text).replace(/\r/g,'').split('\n');const out=[];let i=0;
  const list=s=>s.match(/^\s*(?:(\d+)[.)]|([-*•]))\s+(.+)$/);
  const special=s=>!s.trim()||/^\s*(?:#{1,4}\s|\||```)/.test(s)||list(s)||/^\*\*[^*]+\*\*:?\s*$/.test(s.trim());
  while(i<lines.length){
    let line=lines[i].trim();if(!line){i++;continue}
    if(line.startsWith('```')){const block=[];i++;while(i<lines.length&&!lines[i].trim().startsWith('```'))block.push(lines[i++]);if(i<lines.length)i++;out.push('<pre class="answer-code"><code>'+safe(block.join('\n'))+'</code></pre>');continue}
    if(line.startsWith('|')){
      const rows=[];while(i<lines.length&&lines[i].trim().startsWith('|')){const cells=lines[i++].trim().replace(/^\||\|$/g,'').split('|').map(x=>x.trim());if(!cells.every(c=>/^:?-{3,}:?$/.test(c)))rows.push(cells)}
      if(rows.length)out.push('<div class="table-scroll" tabindex="0" role="region" aria-label="Bảng so sánh, có thể cuộn ngang"><table class="answer-table"><thead><tr>'+rows[0].map(x=>'<th scope="col">'+inline(x)+'</th>').join('')+'</tr></thead><tbody>'+rows.slice(1).map(r=>'<tr>'+r.map(x=>'<td>'+inline(x)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>');continue
    }
    if(/^#{1,4}\s/.test(line)||/^\*\*[^*]+\*\*:?\s*$/.test(line)){out.push('<h3 class="answer-heading">'+inline(line.replace(/^#{1,4}\s+/,''))+'</h3>');i++;continue}
    let match=list(line);if(match){const ordered=!!match[1],tag=ordered?'ol':'ul';let items=[];const start=ordered?Number(match[1]):1;
      while(i<lines.length&&(match=list(lines[i]))&&!!match[1]===ordered){items.push('<li>'+inline(match[3])+'</li>');i++}
      out.push('<'+tag+' class="answer-list"'+(ordered?' start="'+start+'"':'')+'>'+items.join('')+'</'+tag+'>');continue
    }
    const block=[line];i++;while(i<lines.length&&!special(lines[i]))block.push(lines[i++].trim());
    out.push('<p class="answer-paragraph">'+inline(block.join('\n'))+'</p>');
  }return out.join('');
}
