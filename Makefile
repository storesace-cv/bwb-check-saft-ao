.PHONY: agt-rules

agt-rules:
	python scripts/agt_ingest_rules.py --rebuild --verbose
	pytest tests/agt_rules
