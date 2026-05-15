"""RPC server. Runs inside the sandbox container."""

import base64
import os
import subprocess
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException

app = FastAPI()
TOKEN = os.environ['HF_SANDBOX_TOKEN']

def auth(authorization: str = Header(...)):
  if authorization != f'Bearer {TOKEN}':
    raise HTTPException(401)

@app.post('/exec')
def exec_(req: dict, _=Depends(auth)):
  try:
    p = subprocess.run(
      req['cmd'],
      cwd=req.get('workdir'),
      input=req['stdin'].encode() if req.get('stdin') else None,
      capture_output=True,
      timeout=req.get('timeout', 600),
    )
    return {
      'rc': p.returncode,
      'stdout': p.stdout.decode('utf-8', 'replace'),
      'stderr': p.stderr.decode('utf-8', 'replace'),
    }

  except subprocess.TimeoutExpired:
    return {'rc': -1, 'stdout': '', 'stderr': 'timeout'}

  
@app.post('/write')
def write(req: dict, _=Depends(auth)):
  if 'content_b64' in req:
    Path(req['path']).write_bytes(base64.b64decode(req['content_b64']))
  else:
    Path(req['path']).write_text(req['content'])
  return {'ok': True}

@app.post('/read')
def read(req: dict, _=Depends(auth)):
  p = Path(req['path'])
  if not p.exists():
    raise HTTPException(404, f'file not found: {req["path"]}')
  return {'content_b64': base64.b64encode(p.read_bytes()).decode()}


@app.get('/health')
def health():
  return {'ok': True}


if __name__ == '__main__':
  uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')
