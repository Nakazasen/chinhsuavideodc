import json
import sys
from pathlib import Path

# Force stdout UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def query_graph():
    graph_path = Path('graphify-out/graph.json')
    if not graph_path.exists():
        print("graph.json not found")
        return
    
    data = json.loads(graph_path.read_text(encoding='utf-8'))
    nodes = data.get('nodes', [])

    print(f"Total nodes in graph: {len(nodes)}")
    
    matched_docs = []
    
    for n in nodes:
        node_id = str(n.get('id', ''))
        if n.get('type') == 'DOCUMENT' or any(ext in node_id.lower() for ext in ['.md', 'docs/', 'plan', 'handover']):
            matched_docs.append(n)
            
    print("\n--- FOUND DOCUMENT NODES IN GRAPH ---")
    for doc in matched_docs:
        print(f"\n[DOC] ID: {doc.get('id')}")
        print(f"   Label: {doc.get('label')}")
        print(f"   Source File: {doc.get('source_file')}")
        if doc.get('summary'):
            print(f"   Summary: {doc.get('summary')[:300]}...")

if __name__ == '__main__':
    query_graph()
