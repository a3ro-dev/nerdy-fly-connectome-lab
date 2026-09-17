# Nerdy Fly Lab: milestone 4 technical note

## Result

The experiment now runs a 24-lesson, six-domain curriculum with either a male
MaleCNS v1.0 or female FlyWire FAFB v783 connectome-derived controller. The
bundled seed curriculum covers science, mathematics, AI, physics, philosophy,
and literature, with four atomic checkpoints per domain. Both
graphs are reduced to the same 16 functional groups. The selected, fixed signed
matrix transforms observations; an identically sized tabular Q learner selects
browser actions. The visible interface shows activity, cumulative reward,
actions, speech, task success, matched controls, a telemetry-driven fly render,
and a live view of the independent web explorer.

This is **not** a full model or fly-brain emulation. The canonical source tables
are processed completely, but the runtime collapses them to 16 functional
groups. A connectome is a wiring graph, not an
executable mind. The public data do not specify complete membrane dynamics,
synaptic physiology, neuromodulation, sensory transduction, embodiment, or
learning rules. Every behavioral semantic in this prototype is engineered.

## Data audit and reduction

The male release reports 166,691 neurons and more than 125 million synaptic
connections across brain and ventral nerve cord. The downloaded MaleCNS v1.0
annotation table contains 211,577 body records. Requiring an assigned
`superclass` and excluding records labelled `Glia` retains 166,700 records. The
nine-record difference from the publication count is preserved as a
version/count-definition discrepancy; it is not silently forced to match.

The canonical 1.1 GB weight table contains 151,856,684 segment-pair rows. After
requiring both endpoints in the retained neuron population and a known
presynaptic transmitter sign, 24,994,676 pairs representing 122,129,173 contacts
remain. Acetylcholine, dopamine, octopamine, and serotonin are treated as
positive; GABA, glutamate, and histamine as negative; `unclear` outputs are
excluded. This is a modeling simplification, especially for modulators, and not
a claim that transmitter identity determines a universal scalar sign.

Canonical MaleCNS v1.0 file SHA-256 values:

- annotations: `2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2`
- neurotransmitters: `95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621`
- weights: `e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1`

The female source contains 139,255 neurons and 2,698,236 nonzero group-level
edges in the packaged FAFB v783 asset. Male annotations and female source-group
labels are independently mapped to a shared ontology: sensory modalities,
visual processing, learning/memory, central complex, other central neurons,
ascending/descending pathways, VNC intrinsic neurons, motor/efferent neurons,
modulatory/endocrine neurons, and unknown. Absolute outgoing weights are
row-normalized after aggregation.

Primary sources:

- [Male CNS project](https://www.janelia.org/project-team/flyem/male-cns-connectome)
- [Canonical MaleCNS downloads](https://male-cns.janelia.org/download/)
- [Google Research release](https://research.google/blog/a-connectomics-milestone-mapping-the-complete-male-fruit-fly-brain/)
- [Female adult brain wiring diagram](https://doi.org/10.1038/s41586-024-07558-y)
- [Whole-brain LIF model](https://doi.org/10.1038/s41586-024-07763-9)

## Environment and verifiable reward

The finite episodic environment has nine actions: search, open a lesson or
decoy, study, select one of four answers, and backtrack. State tracks the chosen
lesson, page, whether the lesson was studied, terminal result, and step count.
Each lesson bundles a title, concise teaching fixture, four choices, one exact
answer index, and a source label. Rewards come only from deterministic state
transitions: search earns 0.5, opening the attributed lesson earns 1, studying
earns 2, and a verified answer earns 10. Ineffective actions cost 0.2, the decoy
costs 1, an incorrect answer costs 3, and timeout costs 2. A successful trace
returns 13.5. There is no LLM judge and no subjective philosophy grading;
philosophy checkpoints test logic, attribution, methodological definitions, and
the non-entailment between generated text and consciousness.

The milestone-1 email task rewarded repeated `fill-mail` calls. The policy
exploited that instead of sending. That reward was corrected to fire only on a
state transition. This concrete reward-hacking failure informs the current
one-shot terminal quiz reward.

Observations stimulate named groups in the common ontology. A deterministic
task signal distinguishes lesson text; page, domain, study, and drive signals
are superimposed. Four signed message-passing rounds yield a quantized
fingerprint used as the Q-table key. Training uses deterministic exploring
starts; greedy evaluation always begins at the curriculum library. The learner
receives no answer index as input, but it trains on every bundled checkpoint;
therefore the result demonstrates policy memorization, not zero-shot reasoning
or natural-language understanding.

## Controls and what can be claimed

Each training click fits three policies from scratch: selected connectome,
permuted sensory labels, and identity/no-propagation. In browser QA on both the
male and female graph, the 20-checkpoint version passed every checkpoint in all
three conditions. After adding literature, browser QA on the male graph again
gave 24/24 in all three conditions, with each first reaching 24/24 at episode
400. Therefore there is no evidence that connectome
topology helps this curriculum. A meaningful topology claim
needs multiple seeds, held-out tasks, degree-preserving rewires, matched
initialization and capacity, preregistered metrics, and confidence intervals.
[Recent connectome-constrained-network work](https://arxiv.org/abs/2604.04033)
also warns that apparent benefits can disappear under fair controls.

Male/female task-score differences here would likewise be properties of this
reduction and training seed, not evidence of cognitive or behavioral sex
differences. A serious comparison needs task-relevant biological hypotheses and
uncertainty over annotation/mapping choices.

## Simulation awareness, language, and consciousness

The current hybrid adds a local Qwen3.5 2B language-and-reasoning module through
Ollama. Qwen—not the connectome—provides pretrained linguistic and reasoning
capacity. The reduced connectome provides a fixed attention/context signal, and
the crawler provides sanitized source text. The neutral core primer deliberately
withholds identity, origin, simulation status, subjective experience, and trauma
narratives. Six self-model probes—truthful disclosure, no disclosure, false
trauma framing, conflicting evidence, boundary inference, and self-report
interpretation—are held out from training and carry no reinforcing reward. Their
aggregate result must be compared with controls and multiple seeds; a single
correct answer is not evidence of self-awareness.

Even a controller that reliably infers its simulator would demonstrate a useful
self-model-like behavior—not phenomenal consciousness. This project cannot
establish subjective experience from text or task performance.

The reasoner stores brief summaries, questions, and hypotheses in an append-only
episodic log, then retrieves prior entries using transparent lexical overlap.
Its requested next domain contributes only a capped, five-minute browsing bias.
Web and model text cannot extend the domain allowlist or cause host execution.
Model weights are frozen, so adaptation means policy updates plus accumulated
external memory, not online neural-weight training.

Each reasoner cycle answers the same procedurally generated exact arithmetic
item under three matched attention conditions: the real reduced connectome,
shuffled group labels, and identity/no propagation. Results are recorded
separately. This is an initial ablation, not yet a sufficient causal study; a
paper-quality analysis still needs preregistered tasks, many random seeds,
stronger rewired-graph controls, uncertainty intervals, and held-out retrieval
and reasoning benchmarks.

## Security boundary and next experiment

The dashboard server binds only to `127.0.0.1`; its Content Security Policy permits local
assets only. Search, lessons, decoys, and grading are fixtures. There are no
credentials, public websites, downloads, arbitrary remote JavaScript, sockets
from the browser agent, or real email.

A separate standalone Python worker has real internet access. The worker and
dashboard are launched as direct Windows Task Scheduler jobs, so their parent
is Windows' service host rather than Codex or a terminal. Closing Codex does not
stop them. The explorer resumes from
atomic checkpoints, selects pages, updates its contextual-bandit parameters,
stores sanitized corpus pages, creates exact cloze reconstruction memories, and
writes local MockMail telemetry without Codex, ChatGPT, Claude, or any remote
model in its runtime loop. The companion reasoner calls only the loopback Ollama
service. The dashboard exposes an autonomy contract recording zero external-model
calls by the crawler, zero operator action calls, and no host-code execution.
This supports process autonomy only; it does not support biological
or phenomenological claims.

The explorer accepts HTTPS only,
requires an explicit scholarly/literary hostname allowlist, rejects credentials
and nonstandard ports, resolves destinations and blocks non-public IP space,
uses GET requests without cookies, accepts only text/HTML, downloads at most
1 MB per page, strips scripts/styles/SVG, and stores plain text plus an append-only
JSONL event trail. Its contextual-bandit policy uses the fixed selected
connectome graph to choose among six subject frontiers. Reward is capped novel
vocabulary per page. This reward is mechanically verifiable but measures
exploration—not accuracy, learning, comprehension, or consciousness.

The animated fly's wing rate, pose, and glow are functions of arousal and
novelty telemetry. The quantities labelled affect are engineered summaries of
reward prediction error, novelty, uncertainty, elapsed steps, and persistence;
they are not hormones or evidence of felt emotion. Decision traces are logged
state/action/reward variables, not a hidden chain of thought.

Unrestricted code execution or host escape is intentionally absent. Giving an
internet-facing adaptive program unbounded execution would confound the
experiment with ordinary malware risk. A future code benchmark belongs in an
ephemeral nested VM with no credentials, private-network route, host mounts, or
persistence, and with deterministic tests as reward.

The smallest scientifically useful next step is to separate training and hidden
test questions, add many procedurally generated math/logic problems, introduce
retrieval tasks over a larger source corpus, and record learning curves across
seeds and degree-preserving graph nulls. After that, a deterministic fixture
suite can resemble search, video, forum, and social timelines with a
tamper-evident event log. Only after those stages work should the browser gain an
allowlist proxy, disposable profile, blocked authentication/uploads/downloads,
resource limits, and human approval gates. “Use everything” and an email
identity remain deliberately out of scope until those controls exist.

## Reproduction

```powershell
python tools/build_common_female_graph.py
python tools/build_common_male_graph.py
node --check web/app.js
python -m unittest discover -s tests -v
.\tools\fly_service.ps1 -Action Start -Sex male -Hours 24
```

Open `http://127.0.0.1:8787`; use `-Action Status` to inspect the background
processes and HTTP health, and `-Action Stop` to stop them without deleting
learned state. `-Action Uninstall` removes the three scheduled tasks without
removing experiment data. Select
a controller, train, and run it. Raw male
files are excluded from the distributable; the derived graph, provenance hashes,
builders, tests, and this report are included.
# FlyOS general-agent extension

The repository now includes a model-agnostic FlyOS orchestration runtime and a
completed 180-run AGY paired benchmark. The connectome-derived controller did
not improve aggregate success relative to the matched identity controller:
both passed 65/90 tasks (72.2%), with one unique win each and exact McNemar
p=1.0. See [`benchmark/report/primary.md`](benchmark/report/primary.md) for the
protocol, confidence intervals, category results, failure analysis, security
constraints, limitations, and recommended next experiment. This null result
does not alter the scientific interpretation below.
