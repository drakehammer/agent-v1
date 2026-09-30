# Herramientas del agente de triage
from tools.read_report import read_report, TOOL_SCHEMA as READ_REPORT_SCHEMA
from tools.read_test import read_test, TOOL_SCHEMA as READ_TEST_SCHEMA
from tools.write_summary import write_summary, TOOL_SCHEMA as WRITE_SUMMARY_SCHEMA

TOOLS = {
    "read_report": {"schema": READ_REPORT_SCHEMA, "handler": read_report},
    "read_test": {"schema": READ_TEST_SCHEMA, "handler": read_test},
    "write_summary": {"schema": WRITE_SUMMARY_SCHEMA, "handler": write_summary},
}

TOOL_SCHEMAS = [READ_REPORT_SCHEMA, READ_TEST_SCHEMA, WRITE_SUMMARY_SCHEMA]