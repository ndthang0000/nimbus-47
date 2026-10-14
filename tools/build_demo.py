"""Create a captioned video from actual source, evidence and a supplied screenshot.
Requires Pillow and imageio-ffmpeg in a separate artifact-building environment.
"""
from pathlib import Path
import json
import subprocess
import tempfile
import textwrap
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'artifacts'
FONT = 'C:/Windows/Fonts/segoeui.ttf'
MONO = 'C:/Windows/Fonts/consola.ttf'
report = json.loads((OUT/'digitalocean-last-run.json').read_text())
def read(path):
    return (ROOT/path).read_text(encoding='utf-8-sig')
provider = read('src/sync.py')
slides = [
('Nimbus 47 | Coding Test', 'Evidence walkthrough â€” Nguyen Duc Thang\n\n50 public English articles â†’ clean Markdown â†’ API vector store â†’ cited support answers.\n\nPython + Zendesk + OpenAI Responses/File Search + Docker + DigitalOcean.\n\nThis video shows actual code, verified logs and the supplied Playground screenshot. It is not a continuous screen recording.', False),
('1 | Public English article ingestion', read('src/scraper.py').split('    def collect',1)[1][:2100], True),
('2 | Clean Markdown with source URLs', read('src/markdown.py'), True),
('3 | Python API upload and indexing', provider[provider.index("        name = transaction['filename']"):provider.index('        # Detach the previous article')], True),
('4 | Chunking and grounded retrieval', '50 articles are uploaded as 50 complete Markdown files.\n\nPython uploads the complete article. OpenAI performs chunking and embedding. Provider strategy: static 4096-token chunks / zero overlap.\n\nCounts separate source articles, article files and indexed files. Internal embedding chunk totals are not exposed.\n\nResponses uses the exact required instructions and file_search linked to the uploaded vector store. No files were uploaded through the UI.', False),
('5 | Article-level delta and recovery', 'Article ID identifies each source. SHA-256 compares normalized Markdown.\n\nADDED: upload and index. SKIPPED: no upload. UPDATED: index replacement, then detach the old file.\n\nJournal retains remote IDs and indexing progress. Failure recovery and renamed/shrunk articles are covered by tests. OS and host locks prevent overlapping sync.\n\nReplacement is not atomic; omitted articles and detached raw files are retained.', False),
('6 | Container and daily cloud job', read('Dockerfile')+'\nDaily schedule: 0 19 * * * (UTC) = 02:00 Vietnam\nState and data are bind-mounted outside the container.\nCron installed and active; scheduled invocation verified at 02:00 Vietnam, October 14, 2026.', True),
('7 | Actual DigitalOcean execution', read('artifacts/cloud-verification.txt')+'\n'+json.dumps({k:report[k] for k in ['status','exit_code','added','updated','skipped','uploaded_files','source_articles','indexed_files']},indent=2), True),
('8 | Playground YouTube answer', 'SCREENSHOT', False),
('9 | Verification and submission', '12 behavioral tests passed. Live cloud run: 50 skipped, zero uploads, exit 0.\n\nRepository: github.com/ndthang0000/nimbus-47\nEvidence: artifacts/digitalocean-last-run.json and cloud-verification.txt\n\nUI: GPT-6 Luna. CLI: GPT-5.4 Mini. Screenshot answer is correct and cited, but uses numbered steps instead of bullets; draft prompt persistence is unverified.\n\nPart 2 Planning is a separate submission. See README and docs/SUBMISSION.md for setup and limitations.', False),
]
with tempfile.TemporaryDirectory() as folder:
    temp = Path(folder)
    frames=[]
    for index,(title,body,code) in enumerate(slides):
        im=Image.new('RGB',(1600,900),'#101827')
        draw=ImageDraw.Draw(im)
        draw.text((55,30), title, font=ImageFont.truetype(FONT,38), fill='#74d8ef')
        draw.line((55,92,1545,92),fill='#33465a',width=2)
        if body=='SCREENSHOT':
            shot=Image.open(OUT/'assistant-playground.png').convert('RGB')
            shot.thumbnail((1490,700))
            im.paste(shot,((1600-shot.width)//2,115))
            draw.text((55,835),'Actual supplied screenshot: File Search enabled, retrieved file and YouTube answer with Article URL.',font=ImageFont.truetype(FONT,21),fill='white')
        else:
            font=ImageFont.truetype(MONO if code else FONT,21 if code else 29)
            width=112 if code else 88
            lines=[]
            for line in body.splitlines():
                lines.extend(textwrap.wrap(line,width=width,replace_whitespace=False) or [''])
            maxlines=27 if code else 20
            if len(lines)>maxlines:
                lines=lines[:maxlines-1]+['[Excerpt; full source is available in the repository.]']
            y=125
            for line in lines:
                draw.text((55,y),line,font=font,fill='#e6edf5')
                y+=26 if code else 34
        draw.text((1430,855),f'{index+1:02d} / {len(slides):02d}',font=ImageFont.truetype(FONT,20),fill='#8ca0b7')
        file=temp/f'{index:02d}.png'
        im.save(file)
        frames.append(file)
    manifest=temp/'frames.txt'
    manifest.write_text(''.join(f"file '{p.as_posix()}'\nduration 14\n" for p in frames)+f"file '{frames[-1].as_posix()}'\n")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-f','concat','-safe','0','-i',str(manifest),'-r','10','-c:v','libx264','-crf','24','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'coding-demo.mp4')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
print('Created coding-demo.mp4: captioned evidence walkthrough.')
