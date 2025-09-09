import json
import os
import tarfile
import io
from typing import Optional

import etcd3
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import Response
from pydantic import BaseModel

ETCD_HOST = os.getenv("ETCD_HOST", "localhost")
ETCD_PORT = int(os.getenv("ETCD_PORT", "2379"))

POLICY_PREFIX = "/policies/projects/demo"
REGO_KEY = f"{POLICY_PREFIX}/rego.rego"
DATA_KEY = f"{POLICY_PREFIX}/data.json"

etcd = etcd3.client(host=ETCD_HOST, port=ETCD_PORT)

app = FastAPI(title="CMS", version="0.1.0")


class Policy(BaseModel):
    rego: Optional[str] = None
    data: Optional[dict] = None


def _get_etag() -> Optional[str]:
    # Use the max mod_revision of both keys as an ETag surrogate
    max_rev = 0
    for key in (REGO_KEY, DATA_KEY):
        val, meta = etcd.get(key)
        if meta and meta.mod_revision and meta.mod_revision > max_rev:
            max_rev = meta.mod_revision
    return str(max_rev) if max_rev else None


# CMS serves OPA bundles for policy propagation


def _create_bundle() -> bytes:
    """Create an OPA bundle tar.gz from etcd data"""
    rego_b, _ = etcd.get(REGO_KEY)
    data_b, _ = etcd.get(DATA_KEY)
    
    rego_content = (rego_b or b"").decode("utf-8")
    if not rego_content:
        # Default deny policy if no rego found
        rego_content = "package demo\n\ndefault allow = false\n"
    
    try:
        data_content = json.loads((data_b or b"{}").decode("utf-8"))
    except json.JSONDecodeError:
        data_content = {}
    
    # Create tar.gz bundle in memory
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
        # Add rego file
        rego_info = tarfile.TarInfo(name='demo.rego')
        rego_info.size = len(rego_content.encode('utf-8'))
        tar.addfile(rego_info, io.BytesIO(rego_content.encode('utf-8')))
        
        # Add data file
        data_json = json.dumps(data_content)
        data_info = tarfile.TarInfo(name='data.json')
        data_info.size = len(data_json.encode('utf-8'))
        tar.addfile(data_info, io.BytesIO(data_json.encode('utf-8')))
    
    return tar_buffer.getvalue()


@app.get("/bundles/demo")
def get_bundle(if_none_match: Optional[str] = Header(default=None, alias="If-None-Match")):
    """OPA bundle endpoint for policy distribution"""
    current_etag = _get_etag()
    
    # Check if client has current version
    if if_none_match and if_none_match == current_etag:
        return Response(status_code=304)
    
    # Create and return bundle
    bundle_data = _create_bundle()
    
    headers = {}
    if current_etag:
        headers["ETag"] = current_etag
    
    return Response(
        content=bundle_data,
        media_type="application/gzip",
        headers=headers
    )


@app.get("/health")
def health():
    # basic check: can we talk to etcd
    try:
        etcd.status()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/policies/demo")
def get_policy():
    rego_b, _ = etcd.get(REGO_KEY)
    data_b, _ = etcd.get(DATA_KEY)

    etag = _get_etag()
    policy = {
        "rego": (rego_b or b"").decode("utf-8"),
        "data": json.loads((data_b or b"{}").decode("utf-8")) if data_b else {},
    }
    return policy if not etag else policy


@app.put("/policies/demo")
@app.patch("/policies/demo")
def upsert_policy(body: Policy, if_match: Optional[str] = Header(default=None, alias="If-Match")):
    if body.rego is None and body.data is None:
        raise HTTPException(status_code=400, detail="Provide rego and/or data")

    # ETag check if provided
    current = _get_etag()
    if if_match is not None and current is not None and if_match != current:
        raise HTTPException(status_code=409, detail="ETag mismatch")

    if body.rego is not None:
        etcd.put(REGO_KEY, body.rego)
    if body.data is not None:
        etcd.put(DATA_KEY, json.dumps(body.data))

    # Propagation to OPA is handled by a separate etcd→OPA sync process
    return {"status": "updated", "etag": _get_etag()}
