#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""first-timer and retention analysis for NANOG attendees.

reads the consolidated attendee CSV (NANOG,LAST,FIRST,ORG with no header,
as written by `export-nanog.sh export-attendees`) and reports on everyone
who attended NANOG <since> or later, split by when they first attended:

  veterans    first NANOG before <veteran-before>
  newcomers   first NANOG at <since> or later
  (in between is reported as a count only)

a person's first NANOG comes from the whole file. people are matched on
last name plus the first word of the first name, ignoring case, accents and
punctuation, so "Majdi S. Abbas" and "Majdi Abbas" are the same person.
nicknames (Bob/Robert) and name changes are not matched.

the newest meeting in the file is used as the end of the window, so adding
a NANOG to the CSV is all a re-run needs.
"""

import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter, defaultdict

# (label, low, high) inclusive ranges for the bucket tables
SINCE_BUCKETS = [("1", 1, 1), ("2", 2, 2), ("3-4", 3, 4), ("5-8", 5, 8), ("9+", 9, 999)]
TOTAL_BUCKETS = [
    ("1-5", 1, 5),
    ("6-10", 6, 10),
    ("11-20", 11, 20),
    ("21-40", 21, 40),
    ("41+", 41, 999),
]
NEWCOMER_BUCKETS = [
    ("1", 1, 1),
    ("2", 2, 2),
    ("3", 3, 3),
    ("4-5", 4, 5),
    ("6+", 6, 999),
]


def name_tokens(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", s.lower().replace("-", " ")).split()


def person_key(last, first):
    lname, fname = name_tokens(last), name_tokens(first)
    if not lname or not fname:
        return None
    return " ".join(lname) + "|" + fname[0]


def load(path):
    """return {key: person} where person has meetings, name and org."""
    people = defaultdict(
        lambda: {"meetings": set(), "name": "", "org": "", "latest": 0}
    )
    skipped = 0
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if len(row) < 3 or not row[0].strip().isdigit():
                skipped += 1
                continue
            n = int(row[0])
            key = person_key(row[1], row[2])
            if key is None:
                skipped += 1
                continue
            p = people[key]
            p["meetings"].add(n)
            # keep the name and org from the most recent meeting
            if n >= p["latest"]:
                p["latest"] = n
                p["name"] = f"{row[2].strip()} {row[1].strip()}"
                p["org"] = row[3].strip() if len(row) > 3 else ""
    if skipped:
        # mononyms and names with no latin characters, e.g. "jof" or "ハタ"
        print(f"note: skipped {skipped} rows without a usable name", file=sys.stderr)
    return people


def bucket(value, buckets):
    for label, low, high in buckets:
        if low <= value <= high:
            return label
    raise ValueError(f"no bucket for {value}")


def pct(part, whole):
    return f"{100 * part / whole:5.1f}%" if whole else "    -"


def print_distribution(title, values, buckets):
    counts = Counter(bucket(v, buckets) for v in values)
    print(f"\n{title}")
    print(f"  {'mtgs':>6} {'people':>7} {'share':>7}")
    for label, _, _ in buckets:
        print(f"  {label:>6} {counts[label]:>7} {pct(counts[label], len(values)):>7}")


def print_crosstab(title, pairs, row_buckets, col_buckets, row_name, col_name):
    """pairs is a list of (row_value, col_value)."""
    grid = Counter((bucket(r, row_buckets), bucket(c, col_buckets)) for r, c in pairs)
    labels = [c[0] for c in col_buckets]
    print(f"\n{title}")
    print(f"  rows: {row_name}, columns: {col_name}")
    print(f"  {'':>6} " + " ".join(f"{c:>6}" for c in labels) + f" {'total':>6}")
    for r, _, _ in row_buckets:
        cells = [grid[(r, c)] for c in labels]
        print(f"  {r:>6} " + " ".join(f"{x:>6}" for x in cells) + f" {sum(cells):>6}")


def main():
    parser = argparse.ArgumentParser(
        description="first-timer and retention analysis for NANOG attendees"
    )
    parser.add_argument("attendees", help="consolidated attendee CSV")
    parser.add_argument(
        "--since",
        type=int,
        default=83,
        help="first meeting of the window being studied (default: 83, the "
        "first in-person meeting after the pandemic)",
    )
    parser.add_argument(
        "--veteran-before",
        type=int,
        default=78,
        help="first attended before this meeting counts as a veteran (default: 78)",
    )
    parser.add_argument(
        "--regular",
        type=int,
        default=3,
        help="meetings attended, first one included, to count as a regular "
        "(default: 3)",
    )
    parser.add_argument(
        "--mature",
        type=int,
        default=6,
        help="newcomer groups need this many later meetings to count toward "
        "the settled conversion rate (default: 6)",
    )
    parser.add_argument(
        "--people-csv",
        help="write one row per attendee since --since, with first NANOG, "
        "group and meeting counts",
    )
    args = parser.parse_args()

    people = load(args.attendees)
    meetings = sorted({n for p in people.values() for n in p["meetings"]})
    if not meetings:
        sys.exit(f"error: no attendee rows found in {args.attendees}")
    last = meetings[-1]
    if args.since > last:
        sys.exit(f"error: --since {args.since} is after the newest meeting ({last})")

    gaps = [n for n in range(meetings[0], last + 1) if n not in meetings]
    window = [n for n in meetings if n >= args.since]
    print(f"data: NANOG {meetings[0]}-{last}, {len(people)} people")
    if gaps:
        print(f"warning: no attendee data for NANOG {', '.join(map(str, gaps))}")
        print("  people whose first meeting is missing will look newer than they are")
    print(f"window: NANOG {args.since}-{last} ({len(window)} meetings)")

    # everyone who came to at least one meeting in the window
    rows = []
    for p in people.values():
        since = sorted(n for n in p["meetings"] if n >= args.since)
        if not since:
            continue
        first = min(p["meetings"])
        if first < args.veteran_before:
            group = "veteran"
        elif first >= args.since:
            group = "newcomer"
        else:
            group = "between"
        rows.append(
            {
                "name": p["name"],
                "org": p["org"],
                "first": first,
                "group": group,
                "since": len(since),
                "total": len(p["meetings"]),
                "last": since[-1],
            }
        )

    by_group = defaultdict(list)
    for r in rows:
        by_group[r["group"]].append(r)
    vets, newbies, between = (
        by_group["veteran"],
        by_group["newcomer"],
        by_group["between"],
    )

    print(f"\nattendees at NANOG {args.since}-{last}: {len(rows)}")
    summary = [(f"before {args.veteran_before}", vets)]
    if args.veteran_before < args.since:
        summary.append((f"{args.veteran_before}-{args.since - 1}", between))
    summary.append((f"{args.since} or later", newbies))
    for label, group in summary:
        print(
            f"  first attended {label:<12} {len(group):>6} {pct(len(group), len(rows))}"
        )

    # --- veterans
    print(f"\n=== veterans: first attended before NANOG {args.veteran_before} ===")
    print_distribution(
        f"meetings attended since NANOG {args.since}",
        [r["since"] for r in vets],
        SINCE_BUCKETS,
    )
    print_distribution(
        "meetings attended in total", [r["total"] for r in vets], TOTAL_BUCKETS
    )
    print_crosstab(
        "since vs. total",
        [(r["since"], r["total"]) for r in vets],
        SINCE_BUCKETS,
        TOTAL_BUCKETS,
        f"meetings since {args.since}",
        "meetings in total",
    )
    decades = Counter(r["first"] // 10 * 10 for r in vets)
    print("\nwhen veterans first attended")
    for d in sorted(decades):
        lo = max(d, meetings[0])
        hi = min(d + 9, args.veteran_before - 1)
        print(f"  NANOG {lo}-{hi}: {decades[d]:>5}")

    print(f"\nmost meetings in total (top 15 of {len(vets)})")
    for r in sorted(vets, key=lambda r: (-r["total"], -r["since"], r["name"]))[:15]:
        counts = f"{r['total']:>3} total, {r['since']:>2} since {args.since}"
        print(f"  {counts}, first {r['first']:>2}  {r['name']} ({r['org']})")

    # --- newcomers
    print(f"\n=== newcomers: first attended NANOG {args.since} or later ===")
    print_distribution(
        f"meetings attended (all since NANOG {args.since})",
        [r["since"] for r in newbies],
        NEWCOMER_BUCKETS,
    )

    # one column per meeting count below --regular, then one for regulars
    count_cols = list(range(1, args.regular))
    labels = [str(k) for k in count_cols] + [f"{args.regular}+"]
    print(f"\nby first meeting (regular = {args.regular}+ meetings, first included)")
    print(
        f"  {'first':>5} {'later':>5} {'people':>6} "
        + " ".join(f"{label:>5}" for label in labels)
        + f" {'regular':>8}"
    )
    total = Counter()
    settled = Counter()
    for n in window:
        group = [r for r in newbies if r["first"] == n]
        if not group:
            continue
        c = Counter(min(r["since"], args.regular) for r in group)
        later = sum(1 for m in window if m > n)
        reg = c[args.regular]
        cells = " ".join(f"{c[k]:>5}" for k in count_cols + [args.regular])
        print(f"  {n:>5} {later:>5} {len(group):>6} {cells} {pct(reg, len(group)):>8}")
        total["n"] += len(group)
        total["reg"] += reg
        if later >= args.mature:
            settled["n"] += len(group)
            settled["reg"] += reg

    print(
        f"\n  all newcomers: {total['reg']} of {total['n']} became regulars "
        f"{pct(total['reg'], total['n'])}"
    )
    print(
        f"  settled ({args.mature}+ later meetings): "
        f"{settled['reg']} of {settled['n']} {pct(settled['reg'], settled['n'])}"
    )
    print("  recent groups haven't had time to come back, so use the settled rate")

    if args.people_csv:
        fields = ["name", "org", "group", "first", "since", "total", "last"]
        with open(args.people_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in sorted(rows, key=lambda r: (r["first"], r["name"].lower())):
                w.writerow(r)
        print(f"\nwrote {len(rows)} attendees to {args.people_csv}")


if __name__ == "__main__":
    main()
