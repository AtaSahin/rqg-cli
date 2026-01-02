from pathlib import Path
from typing import List, Optional
from lxml import etree
from rqg.models import TestCaseResult
from rqg.config import PolicyConfig


def parse_junit_xml(xml_path: Path, config: PolicyConfig) -> List[TestCaseResult]:
    results = []
    
    try:
        tree = etree.parse(str(xml_path))
        root = tree.getroot()
        
        if root.tag == "testsuites":
            for testsuite in root:
                if testsuite.tag == "testsuite":
                    results.extend(_parse_testsuite(testsuite, config))
        elif root.tag == "testsuite":
            results.extend(_parse_testsuite(root, config))
        else:
            for testsuite in root.xpath(".//testsuite"):
                results.extend(_parse_testsuite(testsuite, config))
    
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Invalid XML in {xml_path}: {e}")
    
    return results


def _parse_testsuite(testsuite_elem, config: PolicyConfig) -> List[TestCaseResult]:
    results = []
    suite_name = testsuite_elem.get("name", "unknown")
    
    for testcase in testsuite_elem.xpath(".//testcase"):
        classname = testcase.get("classname", "")
        name = testcase.get("name", "")
        
        test_id = _build_test_id(classname, name, config.get_test_id_strategy())
        
        duration = testcase.get("time")
        duration_ms = float(duration) * 1000 if duration else None
        
        outcome = "pass"
        failure_text = None
        system_out = None
        system_err = None
        
        failure = testcase.find("failure")
        error = testcase.find("error")
        skipped = testcase.find("skipped")
        
        if skipped is not None:
            outcome = "skip"
        elif failure is not None:
            outcome = "fail"
            failure_text = failure.text or failure.get("message", "")
        elif error is not None:
            outcome = "fail"
            failure_text = error.text or error.get("message", "")
        
        system_out_elem = testcase.find("system-out")
        if system_out_elem is not None:
            system_out = system_out_elem.text
        
        system_err_elem = testcase.find("system-err")
        if system_err_elem is not None:
            system_err = system_err_elem.text
        
        result = TestCaseResult(
            test_id=test_id,
            suite=suite_name,
            classname=classname,
            name=name,
            duration_ms=duration_ms,
            outcome=outcome,
            failure_text=failure_text,
            system_out=system_out,
            system_err=system_err,
        )
        results.append(result)
    
    return results


def _build_test_id(classname: str, name: str, strategy: str) -> str:
    if strategy == "classname::name":
        if classname:
            return f"{classname}::{name}"
        return name
    elif strategy == "package.class::name":
        parts = classname.split(".")
        if len(parts) > 1:
            return f"{'.'.join(parts[:-1])}.{parts[-1]}::{name}"
        return f"{classname}::{name}"
    else:
        return name

