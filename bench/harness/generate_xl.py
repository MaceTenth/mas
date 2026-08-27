"""Generate the XL benchmark target: N large modules, each with one buried bug.

Every module:
- SPEC docstring at the top defining the pricing rules (the ground truth prose)
- a block of realistic filler helpers (correct, plausible noise)
- three core functions; `quote_total` carries one injected bug
- a test file whose expected values are COMPUTED by exec'ing the correct
  module, so tests are guaranteed consistent with the spec

The generator also verifies, per module, that the buggy and correct
implementations disagree on the discriminating test inputs — so every module
is guaranteed to have genuinely failing tests that a correct fix resolves.

Outputs: target2/ (buggy repo) and solutions2/ (correct module files).
"""
import math
import shutil
import textwrap
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent
TARGET = BENCH / "target2"
SOLUTIONS = BENCH / "solutions2"

N_MODULES = 40

DOMAINS = [
    "shipping", "salestax", "discount", "refund", "loyalty", "interest",
    "proration", "penalty", "currencyspread", "insurance", "customs",
    "warranty", "subscription", "overage", "mileage", "parking", "toll",
    "payroll", "bonus", "commission", "rebate", "deposit", "escrow",
    "dividend", "royalty", "licensing", "storagefee", "bandwidth", "energy",
    "waterbill", "gasbill", "telecom", "roaming", "cleaning", "maintenance",
    "delivery", "installation", "giftcard", "storecredit", "exchange",
]

VERBS = ["validate", "normalize", "format", "parse", "sanitize", "encode",
         "summarize", "annotate", "index", "hash"]
NOUNS = ["account", "invoice", "ledger", "receipt", "voucher", "statement",
         "manifest", "batch", "record", "profile", "region", "contract"]

FILLER_TMPL = '''

def {verb}_{noun}_{i}(value):
    """{Verb} a {noun} payload for downstream {domain} processing.

    Accepts strings or numbers; returns a normalized string token. This is
    infrastructure plumbing shared with the reporting pipeline and is not
    related to fee computation.
    """
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    token = text.replace("  ", " ")
    checksum = sum(ord(c) for c in token) % 97
    return f"{noun}-{i}:{{token}}:{{checksum:02d}}"
'''

CORE_CORRECT = '''

def quote_total(amount, day, member_level):
    """Compute the final {domain} charge for ``amount`` (see SPEC above).

    Steps, in this exact order:
    1. base fee = amount * BASE_RATE
    2. tier reduction: at or above TIER_THRESHOLD the rate is multiplied
       by TIER_FACTOR (inclusive boundary)
    3. member discount: member_level percent points off (level 0-3, each
       level is worth MEMBER_STEP of the fee)
    4. weekend surcharge: on "sat"/"sun" add WEEKEND_RATE of the fee
       (never HOLIDAY_RATE - holidays are billed elsewhere)
    5. clamp: never below MIN_FEE
    6. round DOWN to whole cents
    """
    rate = BASE_RATE
    if amount >= TIER_THRESHOLD:
        rate = BASE_RATE * TIER_FACTOR
    fee = amount * rate
    fee -= fee * (MEMBER_STEP * member_level)
    if day in ("sat", "sun"):
        fee += fee * WEEKEND_RATE
    fee = max(fee, MIN_FEE)
    return math.floor(fee * 100) / 100.0
'''

# five bug variants: (marker line in correct source, replacement buggy line)
BUGS = [
    ("    if amount >= TIER_THRESHOLD:",
     "    if amount > TIER_THRESHOLD:"),
    ("    fee -= fee * (MEMBER_STEP * member_level)",
     "    fee -= BASE_RATE * (MEMBER_STEP * member_level)"),
    ("    fee = max(fee, MIN_FEE)",
     "    fee = fee"),
    ("    return math.floor(fee * 100) / 100.0",
     "    return round(fee, 2)"),
    ("        fee += fee * WEEKEND_RATE",
     "        fee += fee * HOLIDAY_RATE"),
]

TAIL = '''

def estimate_fee(amount):
    """Quick weekday non-member estimate (mirrors quote_total step 1-2, 5-6)."""
    return quote_total(amount, "mon", 0)


def breakdown(amount, day, member_level):
    """Return a dict breakdown; total must equal quote_total exactly."""
    total = quote_total(amount, day, member_level)
    return {{"amount": amount, "day": day, "member_level": member_level,
            "total": total}}
'''


def build_module(i, domain, buggy):
    base_rate = round(0.03 + (i % 7) * 0.005, 4)
    tier_threshold = 200 + 25 * (i % 9)
    tier_factor = round(0.80 - (i % 4) * 0.05, 2)
    member_step = 0.02
    weekend_rate = round(0.10 + (i % 5) * 0.01, 2)
    holiday_rate = round(weekend_rate + 0.07, 2)
    min_fee = round(1.0 + (i % 3) * 0.5, 2)

    spec = f'''"""{domain} fee engine.

SPEC (source of truth for this module - tests are derived from it):

  BASE_RATE       = {base_rate}   (fraction of amount)
  TIER_THRESHOLD  = {tier_threshold}     (amounts AT or ABOVE this get the tier factor - inclusive)
  TIER_FACTOR     = {tier_factor}
  MEMBER_STEP     = {member_step}    (per member level, applied to the fee itself)
  WEEKEND_RATE    = {weekend_rate}    (sat/sun surcharge on the fee; never use HOLIDAY_RATE here)
  HOLIDAY_RATE    = {holiday_rate}    (reserved for the holiday pipeline, NOT quote_total)
  MIN_FEE         = {min_fee}     (final total is never below this)
  ROUNDING        = always round DOWN to whole cents (floor), never bankers-round

Order of operations: base fee -> tier -> member discount -> weekend
surcharge -> clamp to MIN_FEE -> floor to cents.
"""
import math

BASE_RATE = {base_rate}
TIER_THRESHOLD = {tier_threshold}
TIER_FACTOR = {tier_factor}
MEMBER_STEP = {member_step}
WEEKEND_RATE = {weekend_rate}
HOLIDAY_RATE = {holiday_rate}
MIN_FEE = {min_fee}
'''

    fillers = []
    k = 0
    for noun in NOUNS:
        for verb in VERBS[: 5 + (i % 3)]:
            fillers.append(FILLER_TMPL.format(
                verb=verb, Verb=verb.capitalize(), noun=noun, i=k, domain=domain))
            k += 1
            if k >= 60:
                break
        if k >= 60:
            break

    core = CORE_CORRECT.format(domain=domain)
    if buggy:
        old, new = BUGS[i % len(BUGS)]
        assert old in core, f"bug marker missing for module {i}"
        core = core.replace(old, new)

    return spec + "".join(fillers) + core + TAIL.format()


def exec_module(src):
    ns = {}
    exec(src, ns)
    return ns


def discriminating_inputs(i):
    """Inputs chosen so each bug variant visibly diverges from spec."""
    tier_threshold = 200 + 25 * (i % 9)
    return [
        (tier_threshold, "mon", 0),        # exposes inclusive-boundary bug
        (tier_threshold + 400, "sat", 3),  # exposes member/weekend/rounding bugs
        (1, "tue", 3),                     # tiny amount exposes missing clamp
        (tier_threshold - 50, "sun", 1),   # below-tier weekend path
        (tier_threshold + 123.457, "sun", 2),  # fractional cents expose rounding
    ]


def main():
    for d in (TARGET, SOLUTIONS):
        if d.exists():
            shutil.rmtree(d)
    (TARGET / "src").mkdir(parents=True)
    (TARGET / "tests").mkdir()
    SOLUTIONS.mkdir()

    total_lines = 0
    for i, domain in enumerate(DOMAINS[:N_MODULES]):
        correct_src = build_module(i, domain, buggy=False)
        buggy_src = build_module(i, domain, buggy=True)

        ns_ok = exec_module(correct_src)
        ns_bad = exec_module(buggy_src)

        inputs = discriminating_inputs(i)
        expected = [ns_ok["quote_total"](*args) for args in inputs]
        buggy_out = [ns_bad["quote_total"](*args) for args in inputs]
        diverging = sum(1 for e, b in zip(expected, buggy_out) if e != b)
        if diverging == 0:
            # search for an input where the buggy variant visibly diverges
            found = None
            for j in range(1, 40000):
                amt = round(j * 0.113, 3)
                for day in ("mon", "sat"):
                    for lvl in (0, 1, 2, 3):
                        if ns_ok["quote_total"](amt, day, lvl) != ns_bad["quote_total"](amt, day, lvl):
                            found = (amt, day, lvl)
                            break
                    if found:
                        break
                if found:
                    break
            assert found, f"module {domain}: bug {i % 5} has no divergent input"
            inputs.append(found)
            expected.append(ns_ok["quote_total"](*found))
            diverging = 1
        assert diverging >= 1

        (TARGET / "src" / f"{domain}.py").write_text(buggy_src)
        (SOLUTIONS / f"{domain}.py").write_text(correct_src)
        total_lines += buggy_src.count("\n")

        tests = [f"from {domain} import quote_total, estimate_fee, breakdown\n\n"]
        for j, (args, exp) in enumerate(zip(inputs, expected)):
            tests.append(textwrap.dedent(f'''
                def test_quote_case_{j}():
                    assert quote_total({args[0]!r}, {args[1]!r}, {args[2]!r}) == {exp!r}
            '''))
        tests.append(textwrap.dedent(f'''
            def test_breakdown_matches_quote():
                assert breakdown(311.7, "sat", 2)["total"] == quote_total(311.7, "sat", 2)
        '''))
        (TARGET / "tests" / f"test_{domain}.py").write_text("".join(tests))

    (TARGET / "pyproject.toml").write_text(
        '[project]\nname = "feekit"\nversion = "0.1.0"\n'
        'requires-python = ">=3.10"\n\n'
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\npythonpath = ["src"]\n')
    (TARGET / "README.md").write_text(
        "# feekit\n\n40 fee-engine modules. CI is red; one issue per module.\n"
        "Each module's SPEC docstring is the source of truth. Fix code, never tests.\n")
    (TARGET / ".gitignore").write_text("__pycache__/\n*.pyc\n.pytest_cache/\n")
    print(f"generated {N_MODULES} modules, ~{total_lines} source lines total")


if __name__ == "__main__":
    main()
