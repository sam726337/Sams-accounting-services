from pathlib import Path


source_path = Path(__file__).with_name("qa_mock_tally_20260827.py")
source = source_path.read_text(encoding="utf-8")
source = source.replace(
    'ledgers == ["Bank Current A/c", "Client Alpha", "Office Rent"]',
    'set(ledgers) == {"Bank Current A/c", "Client Alpha", "Office Rent"}',
)
exec(compile(source, str(source_path), "exec"))
