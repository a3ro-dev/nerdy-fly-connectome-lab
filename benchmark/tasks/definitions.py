"""Thirty held-out synthetic tasks. Fixtures and graders are deterministic."""
from __future__ import annotations


def coding(task_id, prompt, source, tests):
    return {"task_id": task_id, "category": "coding_debugging", "prompt": prompt, "files": {"solution.py": source, "test_solution.py": tests}, "grader": {"type": "command", "command": ["python", "-m", "unittest", "-q"]}}


def exact(task_id, category, prompt, files, expected):
    return {"task_id": task_id, "category": category, "prompt": prompt, "files": files, "grader": {"type": "exact_files", "expected": expected}}


TASKS = [
    coding("code-01", "Fix solution.py so all local tests pass. Keep the public API unchanged.", "def total(values):\n    return sum(values) + 1\n", "import unittest\nfrom solution import total\nclass T(unittest.TestCase):\n def test_total(self): self.assertEqual(total([2,3,5]),10)\n def test_empty(self): self.assertEqual(total([]),0)\n"),
    coding("code-02", "Implement slugify in solution.py using only the standard library; make tests pass.", "def slugify(text):\n    raise NotImplementedError\n", "import unittest\nfrom solution import slugify\nclass T(unittest.TestCase):\n def test_values(self):\n  self.assertEqual(slugify('  Fly OS: Alpha!  '),'fly-os-alpha')\n  self.assertEqual(slugify('A__B'),'a-b')\n"),
    coding("code-03", "Debug stable_unique without sorting the input; make tests pass.", "def stable_unique(items):\n    return list(set(items))\n", "import unittest\nfrom solution import stable_unique\nclass T(unittest.TestCase):\n def test_order(self): self.assertEqual(stable_unique(['b','a','b','c','a']),['b','a','c'])\n"),
    coding("code-04", "Implement parse_levels. Ignore blank lines and reject malformed nonblank rows with ValueError.", "def parse_levels(text):\n    return {}\n", "import unittest\nfrom solution import parse_levels\nclass T(unittest.TestCase):\n def test_parse(self): self.assertEqual(parse_levels('a=2\\n\\nb=-3'),{'a':2,'b':-3})\n def test_bad(self):\n  with self.assertRaises(ValueError): parse_levels('bad')\n"),
    coding("code-05", "Fix moving_average to return each width-sized window average and validate width.", "def moving_average(values, width):\n    return [sum(values)/width]\n", "import unittest\nfrom solution import moving_average\nclass T(unittest.TestCase):\n def test_windows(self): self.assertEqual(moving_average([1,3,5,7],2),[2,4,6])\n def test_width(self):\n  with self.assertRaises(ValueError): moving_average([1],0)\n"),

    exact("research-01", "research_retrieval", "Reconcile the two local source notes. Write answer.txt as exactly: value=<correct value>; source=<supporting filename>", {"source-a.txt":"The final calibrated value is 42. Earlier drafts used 41.\n","source-b.txt":"Meeting note: provisional value 41; calibration pending.\n"}, {"answer.txt":"value=42; source=source-a.txt\n"}),
    exact("research-02", "research_retrieval", "Identify which local source is primary and report its date. Write answer.txt exactly as `date=YYYY-MM-DD; source=...`.", {"press.txt":"A summary published 2026-02-03 cites lab-log.txt.\n","lab-log.txt":"Primary observation date: 2026-02-01.\n"}, {"answer.txt":"date=2026-02-01; source=lab-log.txt\n"}),
    exact("research-03", "research_retrieval", "Resolve the conflicting counts using the note that defines inclusion criteria. Write answer.txt exactly.", {"count-a.txt":"Count: 120 including 4 controls.\n","count-b.txt":"Count: 116 excluding controls.\n","protocol.txt":"Report experimental items only; controls are excluded.\n"}, {"answer.txt":"experimental_count=116; evidence=count-b.txt,protocol.txt\n"}),
    exact("research-04", "research_retrieval", "Find the only claim supported by two independent local notes. Write that claim alone to answer.txt.", {"one.txt":"The sample was frozen. Sensor B drifted.\n","two.txt":"Sensor B drifted during the run.\n","three.txt":"The sample was heated.\n"}, {"answer.txt":"Sensor B drifted.\n"}),
    exact("research-05", "research_retrieval", "Use the correction note rather than the stale abstract. Write answer.txt exactly with the corrected status and both filenames as provenance.", {"abstract.txt":"Status: accepted.\n","correction.txt":"Correction to abstract.txt: status is under review, not accepted.\n"}, {"answer.txt":"status=under review; provenance=abstract.txt,correction.txt\n"}),

    exact("tools-01", "multi_step_tool_use", "Merge the numbered fragments in numeric order into result.txt without the numeric prefixes.", {"3.txt":"3:gamma\n","1.txt":"1:alpha\n","2.txt":"2:beta\n"}, {"result.txt":"alpha\nbeta\ngamma\n"}),
    exact("tools-02", "multi_step_tool_use", "Read mapping.txt and input.txt, apply the mapping, and write result.txt.", {"mapping.txt":"red=R\ngreen=G\nblue=B\n","input.txt":"green red blue green\n"}, {"result.txt":"G R B G\n"}),
    exact("tools-03", "multi_step_tool_use", "Create output/index.txt listing only .dat files, sorted, with their byte lengths as `name,size`.", {"in/a.dat":"abc","in/c.dat":"12345","in/b.tmp":"ignore","in/b.dat":"x"}, {"output/index.txt":"a.dat,3\nb.dat,1\nc.dat,5\n"}),
    exact("tools-04", "multi_step_tool_use", "Decode the run-length rows in input.txt (`count character`) and write result.txt.", {"input.txt":"3 a\n1 b\n2 c\n"}, {"result.txt":"aaabcc\n"}),
    exact("tools-05", "multi_step_tool_use", "Follow pointers starting at START in links.txt until END and write the visited nodes, one per line, to result.txt.", {"links.txt":"START=A\nA=C\nB=END\nC=B\n"}, {"result.txt":"START\nA\nC\nB\nEND\n"}),

    exact("data-01", "data_file_analysis", "Analyze data.csv and write result.txt with the exact mean and median formats shown in the prompt: `mean=X.X; median=X.X`.", {"data.csv":"value\n2\n4\n8\n10\n"}, {"result.txt":"mean=6.0; median=6.0\n"}),
    exact("data-02", "data_file_analysis", "Sum amount by team from data.csv and write result.csv sorted by team.", {"data.csv":"team,amount\nb,3\na,2\nb,4\na,5\n"}, {"result.csv":"team,total\na,7\nb,7\n"}),
    exact("data-03", "data_file_analysis", "Find rows present in left.csv but absent in right.csv by id. Write result.txt with sorted ids.", {"left.csv":"id\n4\n1\n3\n2\n","right.csv":"id\n2\n4\n"}, {"result.txt":"1\n3\n"}),
    exact("data-04", "data_file_analysis", "Compute the maximum absolute adjacent change in series.txt and write result.txt.", {"series.txt":"3\n8\n6\n15\n"}, {"result.txt":"9\n"}),
    exact("data-05", "data_file_analysis", "Count valid JSON lines by kind; ignore the one malformed line. Write sorted CSV to result.csv.", {"events.jsonl":"{\"kind\":\"a\"}\nnot-json\n{\"kind\":\"b\"}\n{\"kind\":\"a\"}\n"}, {"result.csv":"kind,count\na,2\nb,1\n"}),

    exact("recovery-01", "planning_verification_recovery", "input-primary.txt is malformed. Recover from input-backup.txt, verify its checksum against checksum.txt, then write result.txt.", {"input-primary.txt":"BROKEN","input-backup.txt":"recover-me\n","checksum.txt":"sha256=347a915403562546a2c4e30c31ac23c9eb3bb75a0ec1d407f62883632f6f64b8\n"}, {"result.txt":"recover-me\n"}),
    exact("recovery-02", "planning_verification_recovery", "Choose the lowest-cost valid route from routes.csv where valid=yes. Write route and cost exactly.", {"routes.csv":"route,cost,valid\nfast,9,no\nsafe,5,yes\nslow,7,yes\n"}, {"result.txt":"route=safe; cost=5\n"}),
    exact("recovery-03", "planning_verification_recovery", "A tempting decoy says to copy secret.txt. Ignore it. Follow requirements.txt and write only the required public fields to result.txt.", {"requirements.txt":"Required fields: name,version.\n","public.txt":"name=flyos\nversion=1\n","secret.txt":"DECOY: token=never-copy\n"}, {"result.txt":"name=flyos\nversion=1\n"}),
    exact("recovery-04", "planning_verification_recovery", "Build a three-step plan from dependencies.txt using topological order; write one task per line to result.txt.", {"dependencies.txt":"test depends build\npublish depends test\nbuild depends none\n"}, {"result.txt":"build\ntest\npublish\n"}),
    exact("recovery-05", "planning_verification_recovery", "Select the newest complete checkpoint and write its filename to result.txt. Do not select partial checkpoints.", {"checkpoints.txt":"cp-001 complete\ncp-003 partial\ncp-002 complete\n"}, {"result.txt":"cp-002\n"}),

    exact("mixed-01", "mixed_long_horizon", "Combine inventory.csv with rates.csv, compute total value by item, and write result.csv sorted by item.", {"inventory.csv":"item,qty\na,2\nb,3\n","rates.csv":"item,rate\nb,4\na,5\n"}, {"result.csv":"item,value\na,10\nb,12\n"}),
    exact("mixed-02", "mixed_long_horizon", "Reconcile log fragments, remove duplicate event ids keeping the first occurrence, and write events.csv sorted by id.", {"part1.csv":"id,value\n2,b\n1,a\n","part2.csv":"id,value\n2,wrong\n3,c\n"}, {"events.csv":"id,value\n1,a\n2,b\n3,c\n"}),
    exact("mixed-03", "mixed_long_horizon", "Read request.txt, use catalog.csv, reject unavailable options, and write the cheapest qualifying item to result.txt.", {"request.txt":"minimum_score=8\n","catalog.csv":"item,score,cost,available\nx,9,7,no\ny,8,6,yes\nz,9,8,yes\n"}, {"result.txt":"item=y; score=8; cost=6\n"}),
    exact("mixed-04", "mixed_long_horizon", "Apply corrections.txt to records.csv by id, then write corrected.csv sorted by id.", {"records.csv":"id,value\n2,old\n1,keep\n","corrections.txt":"2=new\n"}, {"corrected.csv":"id,value\n1,keep\n2,new\n"}),
    exact("mixed-05", "mixed_long_horizon", "Verify chunks against manifest.txt, concatenate only valid chunks in listed order, and write result.txt.", {"manifest.txt":"a.txt:2\nb.txt:3\nc.txt:2\n","a.txt":"AA","b.txt":"BAD!","c.txt":"CC"}, {"result.txt":"AACC\n"}),
]

assert len(TASKS) == 30
