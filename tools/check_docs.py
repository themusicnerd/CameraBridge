"""Limited documentation checks. This is not an ASD-STE100 validator."""
import pathlib
import re
import sys
from urllib.parse import unquote,urlsplit

ROOT=pathlib.Path(__file__).resolve().parents[1]

def check(root=ROOT):
    files=sorted(root.glob('*.md'))+sorted((root/'docs').glob('*.md'));errors=[]
    for path in files:
        text=path.read_text(encoding='utf-8');code=False;prose=[]
        for number,line in enumerate(text.splitlines(),1):
            if re.fullmatch(r'\s*`{1,2}[A-Za-z0-9_-]*\s*',line):errors.append(f'{path.relative_to(root)}:{number}: incomplete code fence')
            if line.strip().startswith('```'):code=not code;continue
            if code:continue
            for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',line):
                if urlsplit(target).scheme or target.startswith('#'):continue
                local=unquote(target.split('#')[0])
                if local and not (path.parent/local).is_file():errors.append(f'{path.relative_to(root)}:{number}: missing link {local}')
            if not line.strip() or line.startswith(('#','|')):continue
            cleaned=re.sub(r'!?\[([^\]]*)\]\([^)]+\)',r'\1',line)
            cleaned=re.sub(r'`[^`]+`','CODE',cleaned)
            cleaned=re.sub(r'https?://\S+','URL',cleaned)
            cleaned=re.sub(r'^\s*(?:\d+\.|[-*])\s+','',cleaned)
            limit=20 if re.match(r'^\s*\d+\.\s',line) else 25
            for sentence in re.split(r'(?<=[.!?])\s+',cleaned):
                words=re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*",sentence)
                if len(words)>limit:errors.append(f'{path.relative_to(root)}:{number}: {len(words)} words; limit {limit}')
            if re.search(r'\b(utilize|leverage|etc\.?|and/or)\b',cleaned,re.I):errors.append(f'{path.relative_to(root)}:{number}: review selected wording')
        if code:errors.append(f'{path.relative_to(root)}: unclosed code block')
    return files,errors

def main():
    files,errors=check()
    for error in errors:print(error)
    print(f'{len(files)} documents checked; {len(errors)} findings.')
    print('Scope: local links, code fences, selected wording and sentence length. Not full ASD-STE100 compliance.')
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
