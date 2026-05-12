import json
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

WORKBOOK_PATH = Path(r"c:/Users/Ani/OneDrive/Desktop/knowledge graph/NewSample.xlsx")
OUTPUT_JSON = Path(r"c:/Users/Ani/OneDrive/Desktop/knowledge graph/knowledge_graph.json")
OUTPUT_HTML = Path(r"c:/Users/Ani/OneDrive/Desktop/knowledge graph/knowledge_graph.html")

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    shared = []
    for si in root.findall("a:si", NS):
        shared.append("".join(t.text or "" for t in si.iterfind(".//a:t", NS)))
    return shared


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    value = cell.findtext("a:v", default="", namespaces=NS)
    if cell.attrib.get("t") == "s" and value:
        return shared_strings[int(value)]
    if cell.attrib.get("t") == "inlineStr":
        return "".join(t.text or "" for t in cell.iterfind(".//a:t", NS))
    return value or ""


def worksheet_rows(zf: zipfile.ZipFile, sheet_path: str) -> list[dict[str, str]]:
    shared_strings = read_shared_strings(zf)
    root = ET.fromstring(zf.read(sheet_path))
    rows = root.find("a:sheetData", NS).findall("a:row", NS)
    if not rows:
        return []

    headers = []
    for cell in rows[0].findall("a:c", NS):
        headers.append(cell_value(cell, shared_strings).strip())

    data = []
    for row in rows[1:]:
        values = []
        for cell in row.findall("a:c", NS):
            values.append(cell_value(cell, shared_strings).strip())
        record = {headers[i]: values[i] if i < len(values) else "" for i in range(len(headers))}
        if any(record.values()):
            data.append(record)
    return data


def load_workbook_records(path: Path) -> list[dict[str, str]]:
    records = []
    with zipfile.ZipFile(path) as zf:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        sheets = workbook.find("a:sheets", NS)
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rid_to_target = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}

        for sheet in sheets:
            rid = sheet.attrib[f"{{{REL_NS}}}id"]
            target = rid_to_target[rid]
            sheet_path = target if target.startswith("xl/") else f"xl/{target}"
            records.extend(worksheet_rows(zf, sheet_path))
    return records


def normalize_text(value: str) -> str:
    return " ".join((value or "").split())


def build_graph(records: list[dict[str, str]]) -> dict:
    nodes = []
    edges = []
    node_index = {}
    class_index = {}

    def add_node(node_id: str, label: str, group: str, details: dict[str, str]) -> None:
        if node_id in node_index:
            return
        node = {
            "id": node_id,
            "label": label,
            "group": group,
            "details": details,
        }
        node_index[node_id] = node
        nodes.append(node)

    for record in records:
        medicine_name = normalize_text(record.get("Medicine Name", ""))
        therapeutic_class = normalize_text(record.get("Therapeutic Class", ""))
        if not medicine_name:
            continue

        if not therapeutic_class:
            therapeutic_class = "Unknown Therapeutic Class"

        class_id = f"class::{therapeutic_class}"
        medicine_id = f"medicine::{therapeutic_class}::{medicine_name}"

        if class_id not in class_index:
            class_index[class_id] = True
            add_node(
                class_id,
                therapeutic_class,
                "therapeutic_class",
                {"Therapeutic Class": therapeutic_class},
            )

        details = {key: value for key, value in record.items() if value}
        details.setdefault("Medicine Name", medicine_name)
        details.setdefault("Therapeutic Class", therapeutic_class)
        add_node(medicine_id, medicine_name, "medicine", details)
        edges.append({"from": class_id, "to": medicine_id})

    return {"nodes": nodes, "edges": edges}


def write_html(graph: dict, output_path: Path) -> None:
    graph_json = json.dumps(graph, ensure_ascii=True, indent=2)
    html = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Medicine Knowledge Graph</title>
  <script src=\"https://unpkg.com/vis-network/standalone/umd/vis-network.min.js\"></script>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f3ee;
      --panel: #fffdf8;
      --ink: #1f2933;
      --muted: #5c6773;
      --accent: #0f766e;
      --accent-2: #b45309;
      --border: rgba(31, 41, 51, 0.12);
    }}
    html, body {{ height: 100%; margin: 0; }}
    body {{
      font-family: Georgia, 'Times New Roman', serif;
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.12), transparent 36%),
        radial-gradient(circle at bottom right, rgba(180, 83, 9, 0.12), transparent 32%),
        var(--bg);
      color: var(--ink);
    }}
    .app {{ display: grid; grid-template-rows: auto 1fr; height: 100%; }}
    .hero {{
      padding: 20px 24px 12px;
      border-bottom: 1px solid var(--border);
      background: linear-gradient(180deg, rgba(255,255,255,0.8), rgba(255,255,255,0.45));
      backdrop-filter: blur(8px);
    }}
    h1 {{ margin: 0; font-size: 30px; letter-spacing: 0.2px; }}
    .sub {{ margin-top: 6px; color: var(--muted); font-size: 14px; }}
    .legend {{ margin-top: 12px; display: flex; gap: 14px; flex-wrap: wrap; font-size: 13px; color: var(--muted); }}
    .legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
    .dot {{ width: 10px; height: 10px; border-radius: 999px; display: inline-block; }}
    .workspace {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 320px;
      gap: 16px;
      padding: 16px 24px 24px;
      min-height: 0;
    }}
    #network {{ width: 100%; height: 100%; min-height: 560px; border-radius: 18px; }}
    .card {{
      background: rgba(255, 253, 248, 0.82);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 14px 16px;
      box-shadow: 0 18px 50px rgba(31, 41, 51, 0.08);
    }}
    .details-card {{
      align-self: start;
      position: sticky;
      top: 16px;
    }}
    .details-label {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
    }}
    pre {{
      margin: 12px 0 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      font-size: 12px;
      color: var(--ink);
    }}
  </style>
</head>
<body>
  <div class=\"app\">
    <div class=\"hero\">
      <h1>Medicine Knowledge Graph</h1>
      <div class=\"sub\">Therapeutic Class is the parent node. Medicine Name is the child node, and every medicine node carries the full row details from the workbook.</div>
      <div class=\"legend\">
        <span><i class=\"dot\" style=\"background:#0f766e\"></i>Therapeutic Class</span>
        <span><i class=\"dot\" style=\"background:#b45309\"></i>Medicine</span>
      </div>
    </div>
    <div class="workspace">
      <div id="network"></div>
      <div class="card details-card">
        <strong>Hover details</strong>
        <div class="details-label">Move over a medicine node to see its full row data here.</div>
        <pre id="selected">Hover a medicine node to inspect its details.</pre>
      </div>
    </div>
  </div>
  <script>
    const graph = __GRAPH_JSON__;
    const container = document.getElementById('network');
    const nodes = new vis.DataSet(graph.nodes.map(node => ({
      ...node,
      level: node.group === 'therapeutic_class' ? 0 : 1,
      color: node.group === 'therapeutic_class'
        ? {{ background: '#0f766e', border: '#0b4f4a', highlight: {{ background: '#115e59', border: '#083f3c' }} }}
        : {{ background: '#b45309', border: '#7c2d12', highlight: {{ background: '#c2410c', border: '#7c2d12' }} }},
      shape: node.group === 'therapeutic_class' ? 'box' : 'dot',
      font: {{ color: '#1f2933', size: node.group === 'therapeutic_class' ? 18 : 14, face: 'Georgia' }},
      margin: node.group === 'therapeutic_class' ? 14 : 8,
    })));
    const edges = new vis.DataSet(graph.edges.map(edge => ({ ...edge, arrows: 'to', color: '#8b8f97' })));
    const data = {{ nodes, edges }};
    const options = {{
      physics: {{
        enabled: true,
        solver: 'barnesHut',
        barnesHut: {{
          gravitationalConstant: -6500,
          springLength: 120,
          springConstant: 0.03,
          avoidOverlap: 0.4,
        }},
        stabilization: {{ iterations: 250, fit: true }},
      }},
      layout: {{ improvedLayout: true }},
      interaction: {{ hover: true, multiselect: false, tooltipDelay: 100 }},
      nodes: {{ borderWidth: 2 }},
      edges: {{ smooth: {{ type: 'cubicBezier', forceDirection: 'vertical' }}, width: 1.2 }},
    }};
    const network = new vis.Network(container, data, options);
    network.once('stabilizationIterationsDone', () => network.fit({{ animation: false }}));
    const selected = document.getElementById('selected');
    const showDetails = node => {{
      if (!node) {{
        selected.textContent = 'Hover a medicine node to inspect its details.';
        return;
      }}
      selected.textContent = JSON.stringify(node.details, null, 2);
    }};
    network.on('hoverNode', params => {{
      const node = nodes.get(params.node);
      if (node && node.group === 'medicine') {{
        showDetails(node);
      }}
    }});
    network.on('blurNode', () => {{
      showDetails(null);
    }});
  </script>
</body>
</html>"""
    html = html.replace("{{", "{").replace("}}", "}")
    html = html.replace("__GRAPH_JSON__", graph_json)
    output_path.write_text(html, encoding="utf-8")


def main() -> None:
    records = load_workbook_records(WORKBOOK_PATH)
    graph = build_graph(records)
    OUTPUT_JSON.write_text(json.dumps(graph, ensure_ascii=True, indent=2), encoding="utf-8")
    write_html(graph, OUTPUT_HTML)
    print(f"Loaded {len(records)} workbook rows")
    print(f"Created {len(graph['nodes'])} nodes and {len(graph['edges'])} edges")
    print(f"Wrote {OUTPUT_JSON}")
    print(f"Wrote {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
