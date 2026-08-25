import json,re
from pathlib import Path
from src.orchestrator import run
from src.tools import listing_docs
def test_eval_cases():
    cases=[json.loads(x) for x in Path("tests/eval_cases.jsonl").read_text().splitlines()]; results=[]
    valid=set(listing_docs())
    for c in cases:
        r=run(c["input"],consent=False); draft=r.get("draft",""); ids=re.findall(r"listing_[0-9]+",draft); results.append({"input":c["input"],"faithfulness":all(x in valid for x in ids),"tool_present":bool(r.get("tool_calls",0)) or c.get("requires_tool") is None,"hil_required":c.get("requires_hil",False),"provenance":bool(r.get("retrieved"))})
    Path("outputs/eval_report.json").write_text(json.dumps(results,indent=2,ensure_ascii=False))
    assert all(x["faithfulness"] for x in results)
