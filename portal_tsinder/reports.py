"""Offline HTML report; all experiment strings are escaped."""
import html
import json


def render(run):
    result = run["result"]
    gates = result.get("gates", [])+result.get("physical_gates", [])
    esc = lambda v: html.escape(str(v))
    table = "".join("<tr>"+"".join(f"<td>{esc(g.get(k,''))}</td>" for k in
                                 ("gate_id", "title", "status", "value", "unit"))+"</tr>" for g in gates)
    pretty = esc(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PORTAL TSINDER research report</title><style>
body{{font:16px/1.55 system-ui;margin:40px auto;max-width:1100px;padding:0 24px;color:#152938}}
h1{{letter-spacing:-1px}}aside{{border-left:4px solid #cc922f;padding:12px;background:#fff8eb}}
table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #ddd;padding:9px;text-align:left}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f7f8;padding:20px;font-size:12px}}
@media print{{body{{margin:0}}tr{{break-inside:avoid}}}}</style>
<h1>PORTAL TSINDER</h1><p>Research report · System Architect: Vadym Tsinderhoz</p>
<aside>Computational evidence only. No physical aperture or spacetime actuator is implemented.
Simulation stability is not a physical wormhole stability result.</aside>
<p>Run: {esc(run['id'])}<br>Experiment: {esc(run['kind'])}<br>Created: {esc(run['created_at'])}
<br>Result SHA-256: {esc(run['result_sha'])}<br>Code fingerprint: {esc(run['code']['sha256'])}</p>
<table><thead><tr><th>ID</th><th>Check</th><th>Status</th><th>Value</th><th>Unit</th></tr></thead>
<tbody>{table}</tbody></table><h2>Complete machine result</h2><pre>{pretty}</pre></html>'''
