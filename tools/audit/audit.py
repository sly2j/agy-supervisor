"""Opt-in audit of Supervisor for Antigravity pack runs, read from Antigravity brain sessions.

Run as `python3 -I tools/audit/audit.py [--root DIR ...] [--since YYYY-MM-DD] [--json]`.
Standard library only; Python 3.9 compatible. Prints markdown tables or JSON to stdout.

Metrics: critic round-1 PASS by lead, round-1 empty and NIT-only findings rates by lead,
scope-critic rulings (KEEP, DOWNGRADE, DROP) and TRIM rate, scope-critic dispatches per critic
round, subagent dispatches by role and tier, worker file collisions and excess reads, quick-tier
ESCALATE rate, token and step distributions per lead tree and main thread.

Privacy: transcripts are only regex-matched, never printed. The whole report is built first and
refused (exit status 2, no offending text shown) if a line looks like a home-directory path or
contains a working directory seen in the transcripts.
"""
import argparse
import collections
import datetime
import glob
import json
import os
import re
import statistics
import sys

DEFAULT_ROOTS = ["~/.gemini/antigravity-cli/brain"]
LEADS = ["researcher", "planner", "executor", "writer"]
WORKERS = {"researcher-worker", "planner-worker", "executor-worker", "writer-worker"}
CRITICS = {"critic"}
SCOPE_CRITICS = {"scope-critic"}
QUICK = {"scout", "fixer", "clerk", "git-ops", "curator", "quick-edit"}
PACK = set(LEADS) | WORKERS | CRITICS | SCOPE_CRITICS | QUICK | {"supervisor"}

PATH_LEAK = re.compile(r"[/-](Users|home)[/-]")
FRACTION = re.compile(r"(\.\d+)")
VERDICT_LINE = re.compile(r"(?im)^.*(verdict|^\W*(PASS|REVISE)\b).*$")
ABOVE_NIT = ("BLOCKING", "MUST", "SHOULD")
LEVELS = ("BLOCKING", "MUST", "SHOULD", "NIT")


def classify_tier(agent_type):
    """Classify agent role into standard supervisor tier."""
    if not agent_type:
        return "other"
    if agent_type in LEADS:
        return "lead"
    if agent_type in WORKERS or agent_type.endswith("-worker"):
        return "worker"
    if agent_type in CRITICS:
        return "critic"
    if agent_type in SCOPE_CRITICS:
        return "scope-critic"
    if agent_type in QUICK:
        return "quick"
    return "other"


def unquote_str(val):
    """Strip surrounding quotes from a string if present."""
    if not isinstance(val, str):
        return ""
    val = val.strip()
    if len(val) >= 2 and ((val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")):
        val = val[1:-1].strip()
    return val


def parse_time(s):
    """Epoch seconds for an ISO timestamp, or None. Python 3.9 rejects non-3/6 digit fractions."""
    if not isinstance(s, str):
        return None
    s = s.replace("Z", "+00:00")
    for text in (s, FRACTION.sub(lambda m: (m.group(1) + "000000")[:7], s, count=1)):
        try:
            d = datetime.datetime.fromisoformat(text)
        except ValueError:
            continue
        if d.tzinfo is None:
            d = d.replace(tzinfo=datetime.timezone.utc)
        return d.timestamp()
    return None


def word_count(w, text):
    """Count case-insensitive whole-word occurrences of w in text."""
    if not text:
        return 0
    return len(re.findall(r"\b" + re.escape(w) + r"\b", text, re.IGNORECASE))


def critic_verdict(text):
    """PASS, REVISE, ambiguous or none."""
    if not text:
        return "none"
    m = re.search(r"(?im)^\s*VERDICT:\s*(PASS|REVISE)\b", text)
    if m:
        return m.group(1).upper()
    p = word_count("PASS", text) > 0
    r = word_count("REVISE", text) > 0
    if p and r:
        lines = [m.group(0) for m in VERDICT_LINE.finditer(text)]
        return "REVISE" if any(re.search(r"\bREVISE\b", x, re.IGNORECASE) for x in lines) else "ambiguous"
    return "PASS" if p else "REVISE" if r else "none"


def findings_rows(text, levels=LEVELS):
    """Count findings table rows matching specified severities."""
    if not text:
        return 0
    n = 0
    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            cells = [c.strip().strip("*`").upper() for c in line.strip().strip("|").split("|")]
            if any("---" in c for c in cells):
                continue
            if any(c in levels for c in cells):
                n += 1
    return n


def extract_round_no(text, fallback=1):
    """Extract round number from text or return fallback."""
    if text:
        m = re.search(r"(?im)^\s*ROUND:\s*(\d+)\b", text)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
    return fallback


def scope_verdict(text):
    """LEAN, TRIM or none."""
    if not text:
        return "none"
    m = re.search(r"(?im)^\s*VERDICT:\s*(LEAN|TRIM)\b", text)
    if m:
        return m.group(1).upper()
    has_lean = word_count("LEAN", text) > 0
    has_trim = word_count("TRIM", text) > 0
    if has_trim and not has_lean:
        return "TRIM"
    if has_lean and not has_trim:
        return "LEAN"
    if has_trim and has_lean:
        lines = [m.group(0) for m in re.finditer(r"(?im)^.*(verdict|\b(LEAN|TRIM)\b).*$", text)]
        for line in lines:
            if re.search(r"\bTRIM\b", line, re.IGNORECASE):
                return "TRIM"
            if re.search(r"\bLEAN\b", line, re.IGNORECASE):
                return "LEAN"
        return "TRIM"
    return "none"


def scope_rulings(text):
    """Count KEEP, DOWNGRADE, DROP rulings in text."""
    counts = {"KEEP": 0, "DOWNGRADE": 0, "DROP": 0}
    if not text:
        return counts

    table_counted = False
    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            cells = [c.strip().strip("*`").upper() for c in line.strip().strip("|").split("|")]
            if any("---" in c for c in cells):
                continue
            for r in ("KEEP", "DOWNGRADE", "DROP"):
                if r in cells:
                    counts[r] += 1
                    table_counted = True
    if table_counted and sum(counts.values()) > 0:
        return counts

    line_counted = False
    for line in text.splitlines():
        m = re.search(r"(?im)^\s*(?:[-*]|\d+\.|\bfinding\b|\bruling\b).*?\b(KEEP|DOWNGRADE|DROP)\b", line)
        if m:
            counts[m.group(1).upper()] += 1
            line_counted = True
    if line_counted and sum(counts.values()) > 0:
        return counts

    for m in re.finditer(r"(?im)\b(KEEP|DOWNGRADE|DROP)\b", text):
        counts[m.group(1).upper()] += 1
    return counts


def is_escalated(text):
    """Check if handback or text signals ESCALATE."""
    if not text:
        return False
    return bool(re.search(r"\bESCALATE\b", text))


def load_transcript(path):
    """Parse one JSONL transcript into tool calls, usage, handback text, and timestamps."""
    tokens_total = 0
    step_count = 0
    context_sizes = []
    tools = []
    file_reads = []
    dispatches = []
    messages_sent = []
    handback = ""
    last_text = ""
    cwds = set()
    first_time = None

    if not os.path.exists(path):
        return {
            "tokens_total": 0, "step_count": 0, "context_sizes": [],
            "tools": [], "file_reads": [], "dispatches": [], "messages_sent": [],
            "handback": "", "last_text": "", "cwds": set(), "first_time": None
        }

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict):
                continue

            t = parse_time(d.get("created_at") or d.get("timestamp"))
            if t is not None and (first_time is None or t < first_time):
                first_time = t

            if isinstance(d.get("cwd"), str) and len(d["cwd"]) > 1:
                cwds.add(d["cwd"])
            if isinstance(d.get("workspace"), str) and len(d["workspace"]) > 1:
                cwds.add(d["workspace"])
            for uri in d.get("workspaceUris", []):
                if isinstance(uri, str):
                    if uri.startswith("file://"):
                        cwds.add(uri[len("file://"):])
                    elif len(uri) > 1:
                        cwds.add(uri)

            inp = int(d.get("input_tokens") or 0)
            cache_read = int(d.get("cache_read_tokens") or d.get("cache_read_input_tokens") or 0)
            out = int(d.get("output_tokens") or 0)
            tok_turn = inp + cache_read + out
            tokens_total += tok_turn
            ctx = inp + cache_read
            if ctx > 0 or out > 0:
                context_sizes.append(ctx)

            step_count += 1

            content = d.get("content")
            if isinstance(content, str) and content.strip():
                last_text = content
            elif isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "text" and str(b.get("text", "")).strip():
                        last_text = b["text"]

            calls = d.get("tool_calls") or []
            if not isinstance(calls, list) and isinstance(content, list):
                calls = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]

            for c in calls:
                if not isinstance(c, dict):
                    continue
                name = c.get("name")
                args = c.get("args") or c.get("input") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = {}
                if not isinstance(args, dict):
                    args = {}

                tools.append((name, args))

                if name in ("read_file", "Read", "read"):
                    fpath = args.get("Path") or args.get("path") or args.get("file_path") or args.get("FilePath")
                    fpath = unquote_str(fpath)
                    if fpath:
                        file_reads.append(fpath)
                elif name in ("invoke_subagent", "Agent", "Task"):
                    stype = args.get("TypeName") or args.get("typeName") or args.get("subagent_type")
                    srole = args.get("Role") or args.get("role")
                    dispatches.append({"type": unquote_str(stype), "role": unquote_str(srole)})
                elif name in ("send_message", "SubagentHandback"):
                    msg = args.get("Message") or args.get("message") or args.get("Content") or args.get("content")
                    recip = args.get("Recipient") or args.get("recipient")
                    msg = unquote_str(msg)
                    recip = unquote_str(recip)
                    if msg:
                        handback = msg
                        messages_sent.append({"recipient": recip, "message": msg})

    return {
        "tokens_total": tokens_total,
        "step_count": step_count,
        "context_sizes": context_sizes,
        "tools": tools,
        "file_reads": file_reads,
        "dispatches": dispatches,
        "messages_sent": messages_sent,
        "handback": handback,
        "last_text": last_text,
        "cwds": cwds,
        "first_time": first_time
    }


def load_messages(session_dir):
    """Load messages from .system_generated/messages/*.json."""
    msgs = []
    msg_dir = os.path.join(session_dir, ".system_generated", "messages")
    if not os.path.isdir(msg_dir):
        return msgs
    for fname in sorted(os.listdir(msg_dir)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(msg_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(d, dict) and "content" in d:
            msgs.append(d)
    return msgs


def load_subagent_descriptors(session_dir):
    """Load subagent descriptors from .system_generated/subagents/*.json."""
    descriptors = []
    sub_dir = os.path.join(session_dir, ".system_generated", "subagents")
    if not os.path.isdir(sub_dir):
        return descriptors
    for fname in sorted(os.listdir(sub_dir)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(sub_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict):
            continue
        cid = d.get("conversationId") or fname[:-len(".json")]
        desc = d.get("subagentDescriptor") or {}
        stype = desc.get("typeName") or d.get("typeName") or d.get("agentType") or ""
        srole = desc.get("role") or d.get("role") or ""
        spawn_step = d.get("spawnStepIndex") or d.get("spawn_step_index") or 0
        workspace_uris = d.get("workspaceUris") or []
        descriptors.append({
            "id": cid,
            "type": unquote_str(stype),
            "role": unquote_str(srole),
            "spawn_step": spawn_step,
            "workspace_uris": workspace_uris
        })
    return descriptors


def load_all_sessions(roots, since_ts):
    """Discover and parse sessions and subagent hierarchies across transcript roots."""
    raw_sessions = {}
    cwds_all = set()

    for root in roots:
        root_path = os.path.expanduser(root)
        if not os.path.isdir(root_path):
            continue
        for entry in sorted(os.listdir(root_path)):
            sdir = os.path.join(root_path, entry)
            if not os.path.isdir(sdir):
                continue

            transcript_path = os.path.join(sdir, ".system_generated", "logs", "transcript.jsonl")
            if not os.path.exists(transcript_path):
                transcript_path = os.path.join(sdir, "transcript.jsonl")

            has_system = os.path.isdir(os.path.join(sdir, ".system_generated"))
            if not has_system and not os.path.exists(transcript_path):
                continue

            sub_descs = load_subagent_descriptors(sdir)
            msgs = load_messages(sdir)
            tdata = load_transcript(transcript_path)

            for uri in [u for sd in sub_descs for u in sd["workspace_uris"]]:
                if isinstance(uri, str):
                    if uri.startswith("file://"):
                        tdata["cwds"].add(uri[len("file://"):])
                    elif len(uri) > 1:
                        tdata["cwds"].add(uri)

            # Reconcile handback from messages if transcript handback is empty
            if not tdata["handback"] and msgs:
                for m in reversed(msgs):
                    c = m.get("content")
                    if isinstance(c, str) and c.strip():
                        tdata["handback"] = c
                        break

            cwds_all |= tdata["cwds"]
            raw_sessions[entry] = {
                "sid": entry,
                "dir": sdir,
                "transcript": tdata,
                "sub_descs": sub_descs,
                "messages": msgs,
            }

    # Build parent -> children mappings
    parent_of = {}  # child_id -> (parent_id, type_name, role)
    children_of = collections.defaultdict(list)  # parent_id -> list of child records

    for sid, sdata in raw_sessions.items():
        for sd in sdata["sub_descs"]:
            cid = sd["id"]
            parent_of[cid] = (sid, sd["type"], sd["role"])
            children_of[sid].append(sd)

    # Top-level sessions have no recorded parent in raw_sessions
    top_level_sids = [sid for sid in raw_sessions if sid not in parent_of]

    filtered_sessions = []
    for sid in sorted(top_level_sids):
        sdata = raw_sessions[sid]
        first_time = sdata["transcript"]["first_time"]
        if since_ts is not None and (first_time is None or first_time < since_ts):
            continue

        # Gather all descendants for this top-level session
        subs = {}
        to_visit = list(children_of.get(sid, []))
        visited = set()

        while to_visit:
            desc = to_visit.pop(0)
            cid = desc["id"]
            if cid in visited:
                continue
            visited.add(cid)

            c_sdata = raw_sessions.get(cid)
            if c_sdata is not None:
                sub_record = dict(c_sdata["transcript"])
                sub_record["meta"] = {
                    "agentType": desc["type"],
                    "role": desc["role"],
                    "parentId": parent_of.get(cid, (None,))[0]
                }
                sub_record["messages"] = c_sdata["messages"]
            else:
                # Subagent recorded in descriptors but has no directory of its own
                sub_record = {
                    "tokens_total": 0, "step_count": 0, "context_sizes": [],
                    "tools": [], "file_reads": [], "dispatches": [], "messages_sent": [],
                    "handback": "", "last_text": "", "cwds": set(), "first_time": None,
                    "meta": {
                        "agentType": desc["type"],
                        "role": desc["role"],
                        "parentId": parent_of.get(cid, (None,))[0]
                    },
                    "messages": []
                }
            subs[cid] = sub_record

            for next_desc in children_of.get(cid, []):
                if next_desc["id"] not in visited:
                    to_visit.append(next_desc)

        filtered_sessions.append({
            "sid": sid,
            "main": sdata["transcript"],
            "subs": subs,
            "children": children_of.get(sid, [])
        })

    return filtered_sessions, cwds_all


def lead_runs(session):
    """One record per lead run with reviewers, workers, tokens, and worker file reads."""
    subs = session["subs"]
    runs = []

    # Leads can be either subagents of the session, or the main session itself if it is a lead
    candidate_leads = []
    for aid, p in subs.items():
        if p["meta"].get("agentType") in LEADS:
            candidate_leads.append((aid, p, False))

    if not candidate_leads:
        # Check if main session was directly a lead
        for tool_name, args in session["main"]["tools"]:
            if tool_name in ("invoke_subagent", "Agent", "Task"):
                stype = args.get("TypeName") or args.get("typeName") or args.get("subagent_type")
                if stype in LEADS:
                    pass

    # Map children per lead
    for aid, p, is_main in candidate_leads:
        lead_type = p["meta"].get("agentType")

        # Discover children belonging to this lead
        lead_children = [cid for cid, c in subs.items() if c["meta"].get("parentId") == aid]
        if not lead_children and len(candidate_leads) == 1:
            # Flatter fallback: if there is only 1 lead, all other subagents belong to it
            lead_children = [cid for cid in subs if cid != aid]

        critics = []
        scope_dispatches = 0
        scope_reviews = []
        tok = {"lead": p["tokens_total"], "workers": 0, "reviewers": 0}
        steps = {"lead": p["step_count"], "workers": 0, "reviewers": 0}
        reads = collections.defaultdict(set)  # file -> set of worker IDs

        critic_count = 0
        for kid in lead_children:
            kp = subs[kid]
            ktype = kp["meta"].get("agentType", "")

            if ktype in CRITICS:
                tok["reviewers"] += kp["tokens_total"]
                steps["reviewers"] += kp["step_count"]
                critic_count += 1
                hb = kp["handback"] or kp["last_text"]
                round_no = extract_round_no(hb, critic_count)
                critics.append({
                    "id": kid,
                    "round": round_no,
                    "verdict": critic_verdict(hb),
                    "rows": findings_rows(hb, LEVELS),
                    "above_nit": findings_rows(hb, ABOVE_NIT)
                })

            elif ktype in SCOPE_CRITICS:
                tok["reviewers"] += kp["tokens_total"]
                steps["reviewers"] += kp["step_count"]
                scope_dispatches += 1
                hb = kp["handback"] or kp["last_text"]
                scope_reviews.append({
                    "id": kid,
                    "verdict": scope_verdict(hb),
                    "rulings": scope_rulings(hb)
                })

            else:
                tok["workers"] += kp["tokens_total"]
                steps["workers"] += kp["step_count"]
                if ktype in WORKERS or ktype.endswith("-worker"):
                    for fpath in kp["file_reads"]:
                        reads[fpath].add(kid)

        # Context sizes
        ctx = p["context_sizes"]
        final_ctx = ctx[-1] if ctx else None

        # Check skipped mentions
        skipped_mentions = len(re.findall(r"scope-critic skipped", p["handback"] or p["last_text"], re.IGNORECASE))

        dup_files = sum(1 for ks in reads.values() if len(ks) > 1)
        dup_excess = sum(len(ks) - 1 for ks in reads.values() if len(ks) > 1)

        runs.append({
            "lead": lead_type,
            "aid": aid,
            "critics": critics,
            "scope_dispatches": scope_dispatches,
            "scope_reviews": scope_reviews,
            "skipped_mentions": skipped_mentions,
            "rounds": len(critics),
            "ctx": final_ctx,
            "tok": tok,
            "steps": steps,
            "dup_files": dup_files,
            "dup_excess": dup_excess
        })

    return runs


def quick_runs(session):
    """List of (agent_type, is_escalated) records for quick-tier subagents."""
    records = []
    for p in session["subs"].values():
        atype = p["meta"].get("agentType")
        if atype in QUICK:
            text = p["handback"] or p["last_text"]
            records.append((atype, is_escalated(text)))
    return records


def subagent_dispatches(sessions):
    """Aggregate counts of all subagents dispatched across sessions, by tier and by role."""
    tier_counts = collections.defaultdict(int)
    role_counts = collections.defaultdict(int)

    for s in sessions:
        for p in s["subs"].values():
            role = p["meta"].get("agentType") or "unknown"
            tier = classify_tier(role)
            tier_counts[tier] += 1
            role_counts[role] += 1

    return tier_counts, role_counts


def ratio(a, b):
    """Formatted ratio: a/b (pct%)."""
    return "%d/%d (%d%%)" % (a, b, round(100.0 * a / b)) if b else "0/0"


def fmt(n):
    """Formatted compact token / step count."""
    if n >= 1e6:
        return "%.1fM" % (n / 1e6)
    if n >= 1e3:
        return "%dk" % round(n / 1e3)
    return str(int(n))


def table(out, header, rows):
    """Append formatted markdown table to out lines."""
    out.append("| " + " | ".join(header) + " |")
    out.append("|" + "---|" * len(header))
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    out.append("")


def by_lead(runs):
    """Group runs by lead role in LEADS order."""
    return [(lead, [r for r in runs if r["lead"] == lead]) for lead in LEADS
            if any(r["lead"] == lead for r in runs)]


def build_report(sessions):
    """Build the full human-readable markdown audit report."""
    runs = [r for s in sessions for r in lead_runs(s)]
    quick = [q for s in sessions for q in quick_runs(s)]
    out = ["# Pack audit", ""]

    n_subs = sum(len(s["subs"]) for s in sessions)
    starts = [s["main"]["first_time"] for s in sessions if s["main"]["first_time"] is not None]
    span = "%s to %s" % tuple(datetime.datetime.fromtimestamp(x, datetime.timezone.utc).strftime("%Y-%m-%d")
                              for x in (min(starts), max(starts))) if starts else "n/a"

    out += ["## Corpus", ""]
    table(out, ["sessions", "subagent transcripts", "lead runs", "critic handbacks",
                "scope reviews", "quick-tier runs", "session start range (UTC)"],
          [[len(sessions), n_subs, len(runs),
            sum(len(r["critics"]) for r in runs),
            sum(len(r["scope_reviews"]) for r in runs),
            len(quick), span]])

    out += ["## Critic round-1 PASS by lead", ""]
    rows = []
    for lead, L in by_lead(runs):
        r1 = [c for r in L for c in r["critics"] if c["round"] == 1]
        rows.append([lead, len(L), ratio(sum(c["verdict"] == "PASS" for c in r1), len(r1))])
    table(out, ["lead", "runs", "round-1 PASS"], rows)

    out += ["## Round-1 findings tables by lead", ""]
    out.append("Empty: no table row has a BLOCKING, MUST, SHOULD or NIT cell. NIT-only or empty: no "
               "BLOCKING, MUST or SHOULD cell (scope-critic skip-eligible within the size bound).")
    out.append("")
    rows = []
    for lead, L in by_lead(runs):
        r1 = [c for r in L for c in r["critics"] if c["round"] == 1]
        rows.append([lead, len(r1), ratio(sum(c["rows"] == 0 for c in r1), len(r1)),
                     ratio(sum(c["above_nit"] == 0 for c in r1), len(r1))])
    table(out, ["lead", "round-1 critic handbacks", "empty", "NIT-only or empty"], rows)

    out += ["## Scope-critic dispatches per critic round", ""]
    rows = []
    for lead, L in by_lead(runs):
        rounds = sum(r["rounds"] for r in L)
        scope = sum(r["scope_dispatches"] for r in L)
        rows.append([lead, rounds, scope, "%.2f" % (scope / rounds) if rounds else "n/a",
                     sum(r["skipped_mentions"] for r in L)])
    table(out, ["lead", "critic rounds", "scope-critic dispatches", "per critic round",
                "'scope-critic skipped' mentions"], rows)

    out += ["## Scope-critic rulings and TRIM rate", ""]
    rows = []
    for lead, L in by_lead(runs):
        reviews = [rev for r in L for rev in r["scope_reviews"]]
        keep = sum(rev["rulings"]["KEEP"] for rev in reviews)
        down = sum(rev["rulings"]["DOWNGRADE"] for rev in reviews)
        drop = sum(rev["rulings"]["DROP"] for rev in reviews)
        trim_cnt = sum(1 for rev in reviews if rev["verdict"] == "TRIM")
        lean_cnt = sum(1 for rev in reviews if rev["verdict"] == "LEAN")
        total_v = trim_cnt + lean_cnt
        rows.append([lead, len(reviews), keep, down, drop, ratio(trim_cnt, total_v)])
    table(out, ["lead", "scope reviews", "KEEP", "DOWNGRADE", "DROP", "TRIM rate"], rows)

    out += ["## Subagent dispatches by role and tier", ""]
    tier_counts, role_counts = subagent_dispatches(sessions)
    rows = []
    for tier in ("lead", "worker", "critic", "scope-critic", "quick", "other"):
        if tier in tier_counts:
            # List roles belonging to this tier
            tier_roles = sorted([r for r, c in role_counts.items() if classify_tier(r) == tier])
            for role in tier_roles:
                rows.append([tier, role, role_counts[role]])
    table(out, ["tier", "role", "dispatches"], rows)

    out += ["## Lead-tree tokens per run (all tokens incl. cache)", ""]
    out.append("Workers are every non-reviewer child; reviewers are critic and scope-critic.")
    out.append("")
    rows = []
    for lead, L in by_lead(runs):
        cells = [lead, len(L)]
        for part in ("lead", "workers", "reviewers"):
            xs = [r["tok"][part] for r in L]
            cells.append("%s total, %s median" % (fmt(sum(xs)), fmt(statistics.median(xs) if xs else 0)))
        cells.append(fmt(sum(sum(r["tok"].values()) for r in L)))
        rows.append(cells)
    table(out, ["lead", "runs", "lead", "workers", "reviewers", "tree total"], rows)

    out += ["## Lead-tree steps per run", ""]
    rows = []
    for lead, L in by_lead(runs):
        cells = [lead, len(L)]
        for part in ("lead", "workers", "reviewers"):
            xs = [r["steps"][part] for r in L]
            cells.append("%s total, %s median" % (fmt(sum(xs)), fmt(statistics.median(xs) if xs else 0)))
        cells.append(fmt(sum(sum(r["steps"].values()) for r in L)))
        rows.append(cells)
    table(out, ["lead", "runs", "lead steps", "worker steps", "reviewer steps", "tree total steps"], rows)

    out += ["## Files read by two or more workers of one run", ""]
    rows = []
    for lead, L in by_lead(runs):
        rows.append([lead, len(L), sum(1 for r in L if r["dup_files"]), sum(r["dup_files"] for r in L),
                     sum(r["dup_excess"] for r in L)])
    table(out, ["lead", "runs", "runs affected", "files", "excess reads"], rows)

    out += ["## Quick-tier ESCALATE rate", ""]
    rows = []
    for t in sorted(QUICK):
        q = [e for ty, e in quick if ty == t]
        if q:
            rows.append([t, ratio(sum(q), len(q))])
    rows.append(["all", ratio(sum(e for _, e in quick), len(quick))])
    table(out, ["agent", "ESCALATE"], rows)

    out += ["## Lead final context by lead (tokens)", ""]
    out.append("Prompt size of the lead transcript's last assistant message; watches self-doing leads for bloat.")
    out.append("")
    rows = []
    for lead, L in by_lead(runs):
        xs = [r["ctx"] for r in L if r["ctx"] is not None]
        rows.append([lead, len(xs), fmt(statistics.median(xs)) if xs else "n/a",
                     fmt(max(xs)) if xs else "n/a"])
    table(out, ["lead", "runs", "median", "max"], rows)

    out += ["## Main-thread final context (tokens)", ""]
    finals = []
    for s in sessions:
        ctx = s["main"]["context_sizes"]
        if ctx:
            finals.append((ctx[-1], s["sid"]))
    if finals:
        biggest = max(finals)
        table(out, ["sessions", "median", "max", "max session"],
              [[len(finals), fmt(statistics.median([c for c, _ in finals])), fmt(biggest[0]), biggest[1][:8]]])
    else:
        table(out, ["sessions", "median", "max", "max session"], [[0, "n/a", "n/a", "n/a"]])

    return out


def build_json_data(sessions):
    """Build machine-readable structured JSON dictionary for --json output."""
    runs = [r for s in sessions for r in lead_runs(s)]
    quick = [q for s in sessions for q in quick_runs(s)]

    n_subs = sum(len(s["subs"]) for s in sessions)
    starts = [s["main"]["first_time"] for s in sessions if s["main"]["first_time"] is not None]
    span = [
        datetime.datetime.fromtimestamp(min(starts), datetime.timezone.utc).strftime("%Y-%m-%d"),
        datetime.datetime.fromtimestamp(max(starts), datetime.timezone.utc).strftime("%Y-%m-%d")
    ] if starts else None

    # Critic round-1 pass
    critic_r1 = {}
    for lead, L in by_lead(runs):
        r1 = [c for r in L for c in r["critics"] if c["round"] == 1]
        pass_count = sum(1 for c in r1 if c["verdict"] == "PASS")
        critic_r1[lead] = {
            "runs": len(L),
            "r1_critics": len(r1),
            "pass_count": pass_count,
            "pass_rate": (pass_count / len(r1)) if r1 else 0.0
        }

    # Round-1 findings
    findings_r1 = {}
    for lead, L in by_lead(runs):
        r1 = [c for r in L for c in r["critics"] if c["round"] == 1]
        empty_count = sum(1 for c in r1 if c["rows"] == 0)
        nit_only_count = sum(1 for c in r1 if c["above_nit"] == 0)
        findings_r1[lead] = {
            "r1_critics": len(r1),
            "empty_count": empty_count,
            "empty_rate": (empty_count / len(r1)) if r1 else 0.0,
            "nit_only_count": nit_only_count,
            "nit_only_rate": (nit_only_count / len(r1)) if r1 else 0.0
        }

    # Scope-critic
    scope_by_lead = {}
    tot_scope_dispatches = 0
    tot_keep = tot_down = tot_drop = tot_lean = tot_trim = 0

    for lead, L in by_lead(runs):
        rounds = sum(r["rounds"] for r in L)
        dispatches = sum(r["scope_dispatches"] for r in L)
        skipped = sum(r["skipped_mentions"] for r in L)
        reviews = [rev for r in L for rev in r["scope_reviews"]]
        keep = sum(rev["rulings"]["KEEP"] for rev in reviews)
        down = sum(rev["rulings"]["DOWNGRADE"] for rev in reviews)
        drop = sum(rev["rulings"]["DROP"] for rev in reviews)
        trim_cnt = sum(1 for rev in reviews if rev["verdict"] == "TRIM")
        lean_cnt = sum(1 for rev in reviews if rev["verdict"] == "LEAN")
        tot_verdicts = trim_cnt + lean_cnt

        tot_scope_dispatches += dispatches
        tot_keep += keep
        tot_down += down
        tot_drop += drop
        tot_lean += lean_cnt
        tot_trim += trim_cnt

        scope_by_lead[lead] = {
            "critic_rounds": rounds,
            "dispatches": dispatches,
            "per_round": (dispatches / rounds) if rounds else 0.0,
            "skipped_mentions": skipped,
            "reviews": len(reviews),
            "keep": keep,
            "downgrade": down,
            "drop": drop,
            "lean": lean_cnt,
            "trim": trim_cnt,
            "trim_rate": (trim_cnt / tot_verdicts) if tot_verdicts else 0.0
        }

    total_v = tot_trim + tot_lean
    scope_totals = {
        "dispatches": tot_scope_dispatches,
        "keep": tot_keep,
        "downgrade": tot_down,
        "drop": tot_drop,
        "lean": tot_lean,
        "trim": tot_trim,
        "trim_rate": (tot_trim / total_v) if total_v else 0.0
    }

    # Subagent dispatches
    tier_counts, role_counts = subagent_dispatches(sessions)

    # Worker file collisions
    col_by_lead = {}
    for lead, L in by_lead(runs):
        col_by_lead[lead] = {
            "runs": len(L),
            "runs_affected": sum(1 for r in L if r["dup_files"]),
            "colliding_files": sum(r["dup_files"] for r in L),
            "excess_reads": sum(r["dup_excess"] for r in L)
        }

    # Quick tier escalate
    quick_by_agent = {}
    for t in sorted(QUICK):
        q = [e for ty, e in quick if ty == t]
        if q:
            esc = sum(q)
            quick_by_agent[t] = {
                "runs": len(q),
                "escalated": esc,
                "rate": (esc / len(q)) if q else 0.0
            }
    all_esc = sum(e for _, e in quick)
    quick_all = {
        "runs": len(quick),
        "escalated": all_esc,
        "rate": (all_esc / len(quick)) if quick else 0.0
    }

    # Token and step distributions
    tok_steps_by_lead = {}
    for lead, L in by_lead(runs):
        lead_tok = [r["tok"]["lead"] for r in L]
        work_tok = [r["tok"]["workers"] for r in L]
        rev_tok = [r["tok"]["reviewers"] for r in L]
        tree_tok = [sum(r["tok"].values()) for r in L]

        lead_st = [r["steps"]["lead"] for r in L]
        work_st = [r["steps"]["workers"] for r in L]
        rev_st = [r["steps"]["reviewers"] for r in L]
        tree_st = [sum(r["steps"].values()) for r in L]

        tok_steps_by_lead[lead] = {
            "runs": len(L),
            "lead_tokens": {"total": sum(lead_tok), "median": statistics.median(lead_tok) if lead_tok else 0},
            "worker_tokens": {"total": sum(work_tok), "median": statistics.median(work_tok) if work_tok else 0},
            "reviewer_tokens": {"total": sum(rev_tok), "median": statistics.median(rev_tok) if rev_tok else 0},
            "tree_tokens": {"total": sum(tree_tok), "median": statistics.median(tree_tok) if tree_tok else 0},
            "lead_steps": {"total": sum(lead_st), "median": statistics.median(lead_st) if lead_st else 0},
            "worker_steps": {"total": sum(work_st), "median": statistics.median(work_st) if work_st else 0},
            "reviewer_steps": {"total": sum(rev_st), "median": statistics.median(rev_st) if rev_st else 0},
            "tree_steps": {"total": sum(tree_st), "median": statistics.median(tree_st) if tree_st else 0}
        }

    # Main thread final context
    finals = []
    main_tokens = []
    for s in sessions:
        ctx = s["main"]["context_sizes"]
        main_tokens.append(s["main"]["tokens_total"])
        if ctx:
            finals.append((ctx[-1], s["sid"]))

    biggest = max(finals) if finals else (0, "")
    main_summary = {
        "sessions": len(sessions),
        "median_tokens": statistics.median(main_tokens) if main_tokens else 0,
        "max_tokens": max(main_tokens) if main_tokens else 0,
        "median_final_context": statistics.median([c for c, _ in finals]) if finals else 0,
        "max_final_context": biggest[0],
        "max_context_session": biggest[1][:8]
    }

    return {
        "corpus": {
            "sessions": len(sessions),
            "subagents": n_subs,
            "lead_runs": len(runs),
            "critic_handbacks": sum(len(r["critics"]) for r in runs),
            "scope_reviews": sum(len(r["scope_reviews"]) for r in runs),
            "quick_runs": len(quick),
            "start_range_utc": span
        },
        "critic_round1_pass": critic_r1,
        "round1_findings": findings_r1,
        "scope_critic": {
            "by_lead": scope_by_lead,
            "totals": scope_totals
        },
        "subagent_dispatches": {
            "by_tier": dict(tier_counts),
            "by_role": dict(role_counts)
        },
        "worker_file_collisions": {
            "by_lead": col_by_lead,
            "total_affected_runs": sum(c["runs_affected"] for c in col_by_lead.values()),
            "total_colliding_files": sum(c["colliding_files"] for c in col_by_lead.values()),
            "total_excess_reads": sum(c["excess_reads"] for c in col_by_lead.values())
        },
        "quick_tier_escalate": {
            "by_agent": quick_by_agent,
            "all": quick_all
        },
        "token_and_step_distributions": {
            "by_lead": tok_steps_by_lead,
            "main_thread": main_summary
        }
    }


def scrub(lines, cwds):
    """Return count of lines leaking a home/user path or seen working directory."""
    bad_lines = 0
    for line in lines:
        if PATH_LEAK.search(line):
            bad_lines += 1
            continue
        for cwd in cwds:
            if len(cwd) > 1 and cwd in line:
                bad_lines += 1
                break
    return bad_lines


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="audit.py",
        description="Print pack-usage metrics from Antigravity brain transcripts as markdown tables or JSON. "
                    "Output holds counts, medians, rates and 8-character session prefixes only.",
        epilog="Redirect stdout to tools/audit/out/run.md; nothing is written by the script itself.")
    p.add_argument("--root", action="append", metavar="DIR",
                   help="brain directory to read (repeatable; default: %s)" % " and ".join(DEFAULT_ROOTS))
    p.add_argument("--since", metavar="YYYY-MM-DD", help="only sessions starting on or after this date (UTC)")
    p.add_argument("--json", action="store_true", help="emit machine-readable JSON instead of Markdown tables")
    args = p.parse_args(argv)

    args.since_ts = None
    if args.since:
        try:
            d = datetime.datetime.strptime(args.since, "%Y-%m-%d")
        except ValueError:
            p.error("--since must be YYYY-MM-DD")
        args.since_ts = d.replace(tzinfo=datetime.timezone.utc).timestamp()

    return args


def main(argv=None):
    args = parse_args(argv)
    roots = args.root or DEFAULT_ROOTS
    sessions, cwds = load_all_sessions(roots, args.since_ts)

    if args.json:
        data = build_json_data(sessions)
        text = json.dumps(data, indent=2)
        lines = text.splitlines()
    else:
        lines = build_report(sessions)
        text = "\n".join(lines)

    if scrub(lines, cwds):
        print("audit.py: refusing to print: the report contains a path-like line; nothing was printed",
              file=sys.stderr)
        return 2

    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
