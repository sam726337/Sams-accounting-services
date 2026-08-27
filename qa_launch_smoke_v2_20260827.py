from pathlib import Path


source_path = Path(__file__).with_name("qa_launch_smoke_20260827.py")
source = source_path.read_text(encoding="utf-8")
source = source.replace(
    'reco[0]["status"] == "matched", reco[0]["status"]',
    'reco["results"][0]["status"] == "matched", reco["results"][0]["status"]',
)
exec(compile(source, str(source_path), "exec"))
