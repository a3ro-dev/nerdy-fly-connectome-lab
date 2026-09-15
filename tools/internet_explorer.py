"""Read-only, allowlisted real-web explorer with connectome-fixed features.

Web text is untrusted data: it is never executed or treated as instructions.
The contextual bandit learns which subject frontier yields novel vocabulary.
That reward measures exploration, not truth, understanding, or consciousness.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import math
import os
import random
import re
import socket
import time
from collections import Counter, deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

import numpy as np

ALLOWED_HOSTS = {
    "en.wikipedia.org", "arxiv.org", "plato.stanford.edu", "www.gutenberg.org",
    "openstax.org", "research.google", "www.janelia.org",
}
MAX_BYTES = 1_000_000
MAX_TEXT = 30_000
USER_AGENT = "NerdyFlyResearch/0.3 (local read-only learning experiment)"
WORDS = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")
STOPWORDS = {"about","after","again","also","because","before","being","between","could","first","from","have","into","more","most","other","over","such","than","that","their","there","these","they","this","through","under","used","using","were","which","while","with","would"}
DOMAIN_GROUP = {
    "science": "other_sensory", "math": "central_complex", "ai": "learning_memory",
    "physics": "visual_processing", "philosophy": "central_other", "literature": "visual_sensory",
}
DOMAINS = tuple(DOMAIN_GROUP)


def allowed_host(host: str | None) -> bool:
    host = (host or "").lower().rstrip(".")
    return any(host == item or host.endswith("." + item) for item in ALLOWED_HOSTS)


def validate_url(url: str, resolve: bool = True) -> str:
    clean, _ = urldefrag(url)
    parsed = urlparse(clean)
    if parsed.scheme != "https" or not allowed_host(parsed.hostname):
        raise ValueError("URL is outside the HTTPS allowlist")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("credentials and nonstandard ports are blocked")
    if resolve:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
            raise ValueError("destination resolved to a non-public address")
    return clean


def crawlable_url(url: str) -> bool:
    """Keep the learning frontier on content pages, not site machinery."""
    parsed = urlparse(url)
    if parsed.query or parsed.fragment:
        return False
    host, path = (parsed.hostname or "").lower(), unquote(parsed.path)
    if host == "en.wikipedia.org":
        slug = path.removeprefix("/wiki/")
        return path.startswith("/wiki/") and ":" not in slug and slug != "Main_Page"
    if host == "arxiv.org": return path.startswith("/abs/")
    if host == "plato.stanford.edu": return path.startswith("/entries/")
    if host == "www.gutenberg.org": return path.startswith("/ebooks/")
    return allowed_host(host)


class SafeRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, validate_url(newurl),)


class PageParser(HTMLParser):
    def __init__(self, base: str):
        super().__init__(convert_charrefs=True)
        self.base, self.text, self.links, self.title, self.capture, self.in_title, self.skip = base, [], [], [], False, False, 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "svg", "noscript"}: self.skip += 1
        if tag in {"title", "h1", "h2", "p"}: self.capture = True
        if tag == "title": self.in_title = True
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                candidate = urljoin(self.base, href)
                try:
                    candidate = validate_url(candidate, resolve=False)
                    if crawlable_url(candidate): self.links.append(candidate)
                except (ValueError, TypeError): pass

    def handle_endtag(self, tag):
        if tag in {"script", "style", "svg", "noscript"} and self.skip: self.skip -= 1
        if tag in {"title", "h1", "h2", "p"}: self.capture = False
        if tag == "title": self.in_title = False

    def handle_data(self, data):
        if self.capture and not self.skip:
            value = " ".join(data.split())
            if value:
                self.text.append(value)
                if self.in_title: self.title.append(value)


def fetch(url: str) -> tuple[str, str, list[str], str]:
    url = validate_url(url)
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.8"})
    with build_opener(SafeRedirects).open(request, timeout=20) as response:
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "text/plain"}: raise ValueError(f"blocked content type {content_type}")
        # Deliberately stop after the cap instead of following an unbounded body.
        # HTMLParser tolerates a truncated tail; only extracted text is retained.
        raw = response.read(MAX_BYTES)
        final = validate_url(response.geturl())
        charset = response.headers.get_content_charset() or "utf-8"
    body = raw.decode(charset, errors="replace")
    if content_type == "text/plain": return urlparse(final).path.rsplit("/",1)[-1], " ".join(body.split())[:MAX_TEXT], [], final
    parser = PageParser(final); parser.feed(body)
    text = "\n".join(parser.text)[:MAX_TEXT]
    links = [link for link in dict.fromkeys(parser.links) if link != final][:80]
    title = " ".join(parser.title).strip()[:200] or urlparse(final).path.rsplit("/",1)[-1]
    return title, text, links, final


def make_cloze(title: str, text: str, domain: str, url: str) -> dict | None:
    """Create an exact reconstruction task; this does not verify the source text."""
    counts = Counter(word.lower() for word in WORDS.findall(text))
    sentences = [" ".join(item.split()) for item in re.split(r"(?<=[.!?])\s+", text)]
    candidates = []
    for sentence in sentences:
        if not 70 <= len(sentence) <= 260: continue
        for word in WORDS.findall(sentence):
            low = word.lower()
            if 6 <= len(low) <= 16 and low not in STOPWORDS and counts[low] >= 2:
                candidates.append((counts[low], sentence, word))
    if not candidates: return None
    _, sentence, answer = max(candidates, key=lambda item: (item[0], len(item[1])))
    pool = [word for word,count in counts.most_common() if word != answer.lower() and word not in STOPWORDS and 6 <= len(word) <= 16]
    rnd = random.Random(int(hashlib.sha256(url.encode()).hexdigest()[:16],16))
    rnd.shuffle(pool); distractors = pool[:3]
    if len(distractors) < 3: return None
    options = [answer.lower(), *distractors]; rnd.shuffle(options)
    question = re.sub(rf"\b{re.escape(answer)}\b", "____", sentence, count=1, flags=re.IGNORECASE)
    return {"id":"web-"+hashlib.sha256(url.encode()).hexdigest()[:16],"domain":domain,"title":f"web memory: {title}","question":f"Restore the missing word from the page: {question}","lesson":sentence,"options":options,"answer":options.index(answer.lower()),"source":url,"web_derived":True}


def features(graph: dict, domain: str) -> np.ndarray:
    groups, matrix = graph["groups"], np.asarray(graph["weights"], dtype=float)
    x = np.zeros(len(groups)); x[groups.index(DOMAIN_GROUP[domain])] = 1
    x[groups.index("modulatory_endocrine")] += .25
    original = x.copy()
    for _ in range(4): x = np.tanh(.55 * original + 1.8 * (x @ matrix))
    norm = np.linalg.norm(x)
    return x / norm if norm else x


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def run(args) -> None:
    root = Path(__file__).resolve().parents[1]
    graph = json.loads((root / f"web/data/{args.sex}_common_graph.json").read_text(encoding="utf-8"))
    seeds = json.loads((root / "web/data/internet_seeds.json").read_text(encoding="utf-8"))
    primer_bytes = (root / "web/data/core_primer.json").read_bytes()
    primer = json.loads(primer_bytes)
    primer_words = {word.lower() for word in WORDS.findall(json.dumps(primer,ensure_ascii=False))}
    frontier = {domain: deque(urls) for domain, urls in seeds.items()}
    seen_urls, vocabulary = set(), set()
    domain_counts = {domain: 0 for domain in DOMAINS}
    theta = np.zeros(len(graph["groups"])); rnd = random.Random(args.seed)
    status_path = root / "web/data/internet_status.json"
    corpus_dir = root / "work/corpus"; corpus_dir.mkdir(parents=True, exist_ok=True)
    log_path = root / "work/internet_events.jsonl"
    checkpoint_path = root / "work/explorer_checkpoint.json"
    discovered_path = root / "web/data/discovered_lessons.json"
    preview_path = root / "web/data/internet_page.json"
    mailbox_path = root / "web/data/mock_mailbox.json"
    stop_path = root / "work/explorer.stop"
    intent_path = root / "web/data/reasoner_intent.json"
    discovered = json.loads(discovered_path.read_text(encoding="utf-8")) if discovered_path.exists() else []
    mailbox = json.loads(mailbox_path.read_text(encoding="utf-8")) if mailbox_path.exists() else []
    step = 0
    if checkpoint_path.exists() and not args.fresh:
        saved = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if saved.get("sex") == args.sex:
            frontier = {domain: deque(urls) for domain, urls in saved["frontier"].items()}
            seen_urls, vocabulary = set(saved["seen_urls"]), set(saved["vocabulary"])
            theta = np.asarray(saved["theta"], dtype=float)
            step = saved.get("total_steps", 0)
            domain_counts.update(saved.get("domain_counts", {}))
            if sum(domain_counts.values()) < step * .8 and log_path.exists():
                domain_counts = {domain: 0 for domain in DOMAINS}
                for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
                    try:
                        logged_domain = json.loads(line).get("domain")
                    except json.JSONDecodeError:
                        continue
                    if logged_domain in domain_counts:
                        domain_counts[logged_domain] += 1
    vocabulary.update(primer_words)
    deadline = time.monotonic() + args.hours * 3600 if args.hours else math.inf
    while step < args.steps and time.monotonic() < deadline and not stop_path.exists():
        available = [domain for domain, queue in frontier.items() if queue]
        if not available: break
        epsilon = max(.05, .3 / math.sqrt(step + 1))
        base_values = {item: float(features(graph,item) @ theta) for item in available}
        domain_values = dict(base_values)
        coverage_bonus = {item: min(args.coverage_bonus, args.coverage_bonus * math.log((step + len(DOMAINS)) / (domain_counts.get(item, 0) + 1))) for item in available}
        for item, bonus in coverage_bonus.items():
            domain_values[item] += max(0.0, bonus)
        reasoner_intent = None
        if intent_path.exists():
            try:
                candidate = json.loads(intent_path.read_text(encoding="utf-8"))
                age = datetime.now(timezone.utc).timestamp() - datetime.fromisoformat(candidate["created_at"].replace("Z", "+00:00")).timestamp()
                if candidate.get("domain") in available and 0 <= age < 300:
                    reasoner_intent = candidate
                    domain_values[candidate["domain"]] += max(0.0, min(args.reasoner_bias, 1.0))
            except (AttributeError, KeyError, ValueError, TypeError, json.JSONDecodeError):
                pass
        exploring = rnd.random() < epsilon
        if exploring: domain = rnd.choice(available)
        else: domain = max(available, key=domain_values.get)
        url = frontier[domain].popleft()
        if not crawlable_url(url):
            seen_urls.add(url)
            continue
        if url in seen_urls: continue
        seen_urls.add(url); before = len(vocabulary); error = None
        try:
            title, text, links, final = fetch(url)
            words = {word.lower() for word in WORDS.findall(text)}
            vocabulary.update(words); novel = len(vocabulary) - before
            reward = min(10.0, novel / 100.0)
            for link in links:
                if link not in seen_urls and len(frontier[domain]) < 5000: frontier[domain].append(link)
            digest = hashlib.sha256(final.encode()).hexdigest()[:16]
            atomic_json(corpus_dir / f"{domain}-{digest}.json", {"url":final,"domain":domain,"text":text,"fetched_at":datetime.now(timezone.utc).isoformat()})
            atomic_json(preview_path,{"url":final,"title":title,"domain":domain,"excerpt":text[:5000],"links":links[:20],"fetched_at":datetime.now(timezone.utc).isoformat()})
            memory = make_cloze(title,text,domain,final)
            if memory:
                discovered = [item for item in discovered if item.get("id") != memory["id"]]
                discovered.append(memory); discovered = discovered[-200:]
                atomic_json(discovered_path,discovered)
        except Exception as exc:
            final, novel, reward, error = url, 0, -1.0, f"{type(exc).__name__}: {exc}"
        phi = features(graph, domain); prediction = float(phi @ theta); prediction_error = reward - prediction; theta += args.alpha * prediction_error * phi
        step += 1
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        event = {"time":datetime.now(timezone.utc).isoformat(),"step":step,"sex":args.sex,"domain":domain,"url":final,"decision_mode":"explore" if exploring else "exploit","epsilon":round(epsilon,4),"base_candidate_values":{k:round(v,4) for k,v in base_values.items()},"coverage_bonus":{k:round(v,4) for k,v in coverage_bonus.items()},"candidate_values":{k:round(v,4) for k,v in domain_values.items()},"reasoner_intent":reasoner_intent,"connectome_features":[round(float(v),5) for v in phi],"predicted_reward":round(prediction,4),"reward":round(reward,3),"prediction_error":round(prediction_error,4),"novel_words":novel,"error":error}
        with log_path.open("a", encoding="utf-8") as stream: stream.write(json.dumps(event, ensure_ascii=False) + "\n")
        values = {item: round(float(features(graph,item) @ theta),3) for item in frontier}
        raw_values = list(domain_values.values()) or [0.0]
        span = max(raw_values)-min(raw_values)
        affect_proxies = {
            "positive_reward_prediction_error": round(math.tanh(max(0.0,prediction_error)/5),4),
            "negative_reward_prediction_error": round(math.tanh(max(0.0,-prediction_error)/5),4),
            "novelty_drive": round(min(1.0,novel/1000),4),
            "choice_uncertainty": round(1.0/(1.0+span),4),
            "arousal": round(min(1.0,(abs(prediction_error)+novel/500)/3),4),
            "fatigue": round(step/(step+1000),4),
            "persistence": round(1.0-math.exp(-step/100),4),
        }
        checkpoint = {"sex":args.sex,"total_steps":step,"theta":theta.tolist(),"seen_urls":sorted(seen_urls),"vocabulary":sorted(vocabulary),"frontier":{item:list(queue) for item,queue in frontier.items()},"domain_counts":domain_counts}
        if step % args.checkpoint_every == 0: atomic_json(checkpoint_path,checkpoint)
        autonomy_contract = {
            "runtime": "standalone Python background worker",
            "external_model_calls": 0,
            "operator_action_calls": 0,
            "host_code_execution": False,
            "controller_scope": f"full source graph reduced to {len(graph['groups'])} functional groups; not a whole-brain neuron simulation",
        }
        status = {**event,"running":True,"pid":os.getpid(),"pages":len(seen_urls),"vocabulary":len(vocabulary),"frontier":sum(map(len,frontier.values())),"core_seed_words":len(primer_words),"core_seed_sha256":hashlib.sha256(primer_bytes).hexdigest(),"learned_domain_values":values,"affect_proxies":affect_proxies,"affect_caveat":"engineered telemetry, not measured hormones or evidence of felt emotion","autonomy_contract":autonomy_contract,"security":"HTTPS allowlist; GET-only; no cookies/JS/forms/files/auth; public-IP check; 1MB cap","claim":"novelty-seeking corpus exploration and exact text reconstruction, not verified truth or consciousness"}
        atomic_json(status_path,status); print(json.dumps(event),flush=True)
        if step % args.report_every == 0:
            mailbox.append({"id":f"report-{step}","time":event["time"],"from":"fly@localhost","to":"lab@localhost","subject":f"exploration report · step {step}","body":f"Selected {domain} in {event['decision_mode']} mode. Predicted novelty reward {prediction:.3f}; observed {reward:.3f}; prediction error {prediction_error:.3f}. Memory now contains {len(seen_urls)} pages and {len(vocabulary)} vocabulary items including the neutral seed. Latest source: {final}. This message is automated decision telemetry; it does not assert a subjective state."})
            mailbox = mailbox[-100:]; atomic_json(mailbox_path,mailbox)
        if args.delay and step < args.steps:
            remaining = args.delay
            while remaining > 0 and not stop_path.exists():
                pause = min(.5, remaining); time.sleep(pause); remaining -= pause
    atomic_json(checkpoint_path,checkpoint if 'checkpoint' in locals() else {"sex":args.sex,"total_steps":step,"theta":theta.tolist(),"seen_urls":sorted(seen_urls),"vocabulary":sorted(vocabulary),"frontier":{item:list(queue) for item,queue in frontier.items()},"domain_counts":domain_counts})
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    status.update({"running":False,"finished_at":datetime.now(timezone.utc).isoformat()}); atomic_json(status_path,status)


def parse_args():
    parser=argparse.ArgumentParser();parser.add_argument("--sex",choices=("male","female"),default="male");parser.add_argument("--steps",type=int,default=100000);parser.add_argument("--hours",type=float,default=0);parser.add_argument("--delay",type=float,default=5);parser.add_argument("--alpha",type=float,default=.08);parser.add_argument("--reasoner-bias",type=float,default=.2);parser.add_argument("--coverage-bonus",type=float,default=.3);parser.add_argument("--seed",type=int,default=7);parser.add_argument("--checkpoint-every",type=int,default=20);parser.add_argument("--report-every",type=int,default=10);parser.add_argument("--fresh",action="store_true",help="ignore any saved explorer checkpoint");return parser.parse_args()


if __name__ == "__main__": run(parse_args())
