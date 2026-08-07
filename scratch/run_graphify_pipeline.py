import sys
import json
from pathlib import Path

def main():
    from graphify.extract import collect_files, extract
    from graphify.build import build_from_json
    from graphify.cluster import cluster, score_all
    from graphify.analyze import god_nodes, surprising_connections, suggest_questions
    from graphify.report import generate
    from graphify.export import to_json

    root = Path('.').resolve()

    # 1. AST Extraction
    detect_data = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding='utf-8'))
    code_files = []
    for f in detect_data.get('files', {}).get('code', []):
        p = Path(f)
        if p.exists() and not p.is_dir():
            code_files.append(p)

    if code_files:
        ast_result = extract(code_files, cache_root=root, max_workers=1)
        print(f"AST: {len(ast_result['nodes'])} nodes, {len(ast_result['edges'])} edges")
    else:
        ast_result = {'nodes': [], 'edges': [], 'input_tokens': 0, 'output_tokens': 0}
    Path('graphify-out/.graphify_ast.json').write_text(json.dumps(ast_result, indent=2, ensure_ascii=False), encoding='utf-8')

    # 2. Semantic Extraction for docs
    doc_files = [f for cat in ('document', 'paper', 'image') for f in detect_data.get('files', {}).get(cat, []) if Path(f).exists()]

    sem_nodes = []
    sem_edges = []

    for doc_path_str in doc_files:
        dp = Path(doc_path_str)
        try:
            rel_p = str(dp.relative_to(root)).replace("\\", "/")
        except ValueError:
            rel_p = str(dp).replace("\\", "/")
        
        text = dp.read_text(encoding='utf-8', errors='ignore')
        node_id = rel_p
        sem_nodes.append({
            "id": node_id,
            "label": dp.name,
            "type": "DOCUMENT",
            "source_file": rel_p,
            "summary": text[:500].replace("\n", " ")
        })
        
        # Link doc to code / concepts mentioned
        for code_node in ast_result['nodes']:
            lbl = code_node.get('label', '')
            if lbl and len(lbl) > 3 and lbl in text:
                sem_edges.append({
                    "source": node_id,
                    "target": code_node['id'],
                    "relation": "REFERENCES",
                    "confidence": "EXTRACTED",
                    "source_file": rel_p
                })

    sem_result = {
        'nodes': sem_nodes,
        'edges': sem_edges,
        'hyperedges': [],
        'input_tokens': 0,
        'output_tokens': 0
    }
    Path('graphify-out/.graphify_semantic.json').write_text(json.dumps(sem_result, indent=2, ensure_ascii=False), encoding='utf-8')

    # 3. Merge AST + Semantic
    seen_nodes = {n['id'] for n in ast_result['nodes']}
    merged_nodes = list(ast_result['nodes'])
    for n in sem_nodes:
        if n['id'] not in seen_nodes:
            merged_nodes.append(n)
            seen_nodes.add(n['id'])

    merged_edges = ast_result['edges'] + sem_edges
    merged_extract = {
        'nodes': merged_nodes,
        'edges': merged_edges,
        'hyperedges': [],
        'input_tokens': 0,
        'output_tokens': 0
    }
    Path('graphify-out/.graphify_extract.json').write_text(json.dumps(merged_extract, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Merged: {len(merged_nodes)} nodes, {len(merged_edges)} edges")

    # 4. Build graph & cluster
    G = build_from_json(merged_extract, root=str(root), directed=False)
    if G.number_of_nodes() == 0:
        print("Graph is empty")
        sys.exit(1)

    communities = cluster(G)
    cohesion = score_all(G, communities)
    gods = god_nodes(G)
    surprises = surprising_connections(G, communities)

    labels = {cid: f"Community {cid}" for cid in communities}
    questions = suggest_questions(G, communities, labels)

    to_json(G, communities, 'graphify-out/graph.json')
    report = generate(G, communities, cohesion, labels, gods, surprises, detect_data, {'input': 0, 'output': 0}, str(root), suggested_questions=questions)
    Path('graphify-out/GRAPH_REPORT.md').write_text(report, encoding='utf-8')

    print(f"Graph generated successfully: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

if __name__ == '__main__':
    main()
