"""Validate repository documentation links without reading credential contents."""
from pathlib import Path
import re,json
ROOT=Path(__file__).parent
paths=[ROOT/'README.md',ROOT/'CONTRIBUTING.md',ROOT/'SECURITY.md',*sorted((ROOT/'docs').glob('*.md'))]
errors=[];checked=0
for path in paths:
    text=path.read_text(encoding='utf8')
    if text.count('```')%2:errors.append(path.name+': unmatched code fence')
    for href in re.findall(r'\]\(([^)]+)\)',text):
        if href.startswith(('https://','http://','#','mailto:')):continue
        checked+=1;target=(path.parent/href.split('#')[0]).resolve()
        if not target.exists():errors.append(path.name+': broken link '+href)
    if 'D:\\TestSystem' in text or 'C:\\Users\\anhna' in text:errors.append(path.name+': author-specific install path')
assert not errors,errors
report=dict(passed=True,markdown_files=len(paths),relative_links=checked)
(ROOT/'artifacts').mkdir(exist_ok=True)
(ROOT/'artifacts/documentation-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
