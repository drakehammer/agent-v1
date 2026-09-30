"""Tests unitarios para read_report."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tools.read_report import read_report


def test_read_report_with_failure():
    """Parser con elemento failure."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="TestClass" tests="1" failures="1">
  <testcase name="testMethod" classname="TestClass">
    <failure message="expected &lt;200&gt; but was &lt;404&gt;" type="AssertionError">
      java.lang.AssertionError: expected:&lt;200&gt; but was:&lt;404&gt;
    </failure>
  </testcase>
</testsuite>"""
    samples_dir = Path(__file__).resolve().parent.parent / "data" / "samples" / "synthetic"
    samples_dir.mkdir(parents=True, exist_ok=True)
    real_file = samples_dir / "test_failure.xml"
    real_file.write_text(xml_content, encoding="utf-8")

    result = read_report("test_failure.xml")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["type"] == "failure"
    assert "expected" in result[0]["message"]

    real_file.unlink()


def test_read_report_with_error():
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="ApiTest" tests="2" errors="1">
  <testcase name="testConnection" classname="ApiTest">
    <error message="Connection refused" type="java.net.ConnectException">
      java.net.ConnectException: Connection refused
    </error>
  </testcase>
  <testcase name="testOk" classname="ApiTest"/>
</testsuite>"""
    samples_dir = Path(__file__).resolve().parent.parent / "data" / "samples" / "synthetic"
    samples_dir.mkdir(parents=True, exist_ok=True)
    real_file = samples_dir / "test_error.xml"
    real_file.write_text(xml_content, encoding="utf-8")

    result = read_report("test_error.xml")
    assert len(result) == 1
    assert result[0]["type"] == "error"
    assert result[0]["message"] == "Connection refused"

    real_file.unlink()


def test_read_report_with_skipped():
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="ApiTest" tests="1" skipped="1">
  <testcase name="testSkip" classname="ApiTest">
    <skipped message="Dependency not met"/>
  </testcase>
</testsuite>"""
    samples_dir = Path(__file__).resolve().parent.parent / "data" / "samples" / "synthetic"
    samples_dir.mkdir(parents=True, exist_ok=True)
    real_file = samples_dir / "test_skipped.xml"
    real_file.write_text(xml_content, encoding="utf-8")

    result = read_report("test_skipped.xml")
    assert len(result) == 1
    assert result[0]["type"] == "skipped"

    real_file.unlink()


def test_read_report_empty():
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="ApiTest" tests="1">
  <testcase name="testOk" classname="ApiTest" time="0.01"/>
</testsuite>"""
    samples_dir = Path(__file__).resolve().parent.parent / "data" / "samples" / "synthetic"
    samples_dir.mkdir(parents=True, exist_ok=True)
    real_file = samples_dir / "test_ok.xml"
    real_file.write_text(xml_content, encoding="utf-8")

    result = read_report("test_ok.xml")
    assert result == []

    real_file.unlink()


def test_read_report_path_traversal():
    result = read_report("../../../etc/passwd")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["type"] == "security"
