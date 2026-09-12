"""Build an independent PIT Nifty 200 membership history from NSE press releases.

Reads : data/reference/nse_index_pr/ind_prs*.pdf (+ OCR text for the one
        scanned file) and today's anchor list ind_nifty200list_*.csv.
Writes: data/isd/n200_membership.duckdb
        - n200_events     : every parsed (effective_date, index, action, company, symbol)
        - n200_membership : symbol intervals [valid_from, valid_to)
        - n200_audit      : count checks + break records

Method: backward walk from today's official 200 list through reverse
dated official changes; forward replay validates count==200 throughout.
Symbol labels are as-printed at the time (correct PIT behaviour).
"""
import csv
import glob
import io
import os
import re
import sys
import contextlib
from datetime import date

import pypdf
import duckdb

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
PR_DIR = os.path.join(ROOT, 'data', 'reference', 'nse_index_pr')
OUT_DB = os.path.join(ROOT, 'data', 'isd', 'n200_membership.duckdb')
# ind_prs23082021.pdf is a scanned image — pypdf extracts no text from it, so
# this transcript is the SOLE source of the 2021-09-30 Nifty 200 review (6 out,
# 6 in). It lives beside the PDFs with a manifest row carrying both sha256s;
# it previously pointed at a file in %TEMP%, which made the build reproducible
# on exactly one machine until the next temp clean, and losing it would have
# dropped a *balanced* 6/6 rebalance that no count gate can see.
OCR_FALLBACK = {
    'ind_prs23082021.pdf': 'ind_prs23082021.ocr.txt',
}

RENAME_PAIRS = [
    # (old label, new label); effective dates loaded authoritatively from
    # equity_bhavcopy.duckdb:symbol_changes (NSE symbol-change records).
    # Companies never left the index across these renames.
    ('NIITTECH', 'COFORGE'),
    ('ADANIGAS', 'ATGL'),
    ('ZOMATO', 'ETERNAL'),
    ('MCDOWELL-N', 'UNITDSPR'),
    ('IDFCBANK', 'IDFCFIRSTB'),
    ('RNAM', 'NAM-INDIA'),
    ('LTI', 'LTIM'),
    ('LTIM', 'LTM'),
    ('SKSMICRO', 'BHARATFIN'),
    ('MADRASCEM', 'RAMCOCEM'),
    ('INFOTECENT', 'CYIENT'),
    ('L&TFH', 'LTF'),
    ('GMRINFRA', 'GMRAIRPORT'),
    ('ADANITRANS', 'ADANIENSOL'),
    ('IBVENTURES', 'DHANI'),
    ('INFRATEL', 'INDUSTOWER'),
    # surfaced by the NIFTY 100 / Midcap 100 union gate: these two are touched
    # by events in those streams under their old labels while the N200 chain
    # carries only the modern one, so the two reconstructions disagreed on a
    # name that never left the index
    ('CADILAHC', 'ZYDUSLIFE'),
    ('SRTRANSFIN', 'SHRIRAMFIN'),
    # Names that no event ever touched under their modern label, so the
    # backward walk carried today's ticker all the way to LAUNCH_DATE and the
    # table asserted membership years before that ticker existed. Each pair is
    # a real NSE symbol-change record; SESAGOA->SSLT->VEDL is a two-step chain
    # and era_chain() splits it into all three segments.
    ('HEROHONDA', 'HEROMOTOCO'),
    ('ISPATIND', 'JSWISPAT'),
    ('COREPROTEC', 'COREEDUTEC'),
    ('PIPAVAVYD', 'PIPAVAVDOC'),
    ('MUNDRAPORT', 'ADANIPORTS'),
    ('DEWANHOUS', 'DHFL'),
    ('PIRHEALTH', 'PEL'),
    ('PANTALOONR', 'FRL'),
    ('UNIPHOS', 'UPL'),
    ('SESAGOA', 'SSLT'),
    ('SSLT', 'VEDL'),
    ('TATAGLOBAL', 'TATACONSUM'),
    ('TATAMOTORS', 'TMPV'),
]


def load_rename_dates():
    """{old: (new, effective_date)} sourced from symbol_changes; asserts all."""
    db = os.path.join(ROOT, 'data', 'market_data', 'equity_bhavcopy.duckdb')
    con = duckdb.connect(db, read_only=True)
    out = {}
    missing = []
    for old, new in RENAME_PAIRS:
        row = con.execute(
            'select effective_dt from symbol_changes '
            'where old_symbol=? and new_symbol=? order by effective_dt limit 1',
            [old, new]).fetchone()
        if row is None:
            missing.append((old, new))
        else:
            out[old] = (new, str(row[0]))
    con.close()
    if missing:
        raise SystemExit(f'rename pairs missing from symbol_changes: {missing}')
    return out


def canonical_label(sym, rename_dates):
    seen = set()
    while sym in rename_dates and sym not in seen:
        seen.add(sym)
        sym = rename_dates[sym][0]
    return sym


def era_chain(sym, rename_dates):
    """Full label timeline for a canonical symbol: [(label, start, end)]."""
    fwd = {}
    for old, (new, _d) in rename_dates.items():
        fwd.setdefault(new, []).append(old)
    # walk back from canonical through predecessors (single-chain assumed)
    tail = []
    cur = sym
    while True:
        olds = [o for o, (n, _d) in rename_dates.items() if n == cur]
        if len(olds) != 1:
            break
        old = olds[0]
        tail.append((old, rename_dates[old][1]))
        cur = old
    tail.reverse()
    # tail = [(oldest..immediate predecessor, date when IT ended)]
    segs, prev_end = [], None
    chain_labels = [t[0] for t in tail] + [sym]
    bounds = [t[1] for t in tail] + [None]
    for lab, bgn, end in zip(chain_labels,
                             [None] + bounds[:-1], bounds):
        segs.append((lab, bgn, end))
    return segs

# March-2020 COVID episode: reviews scheduled w.e.f. 2020-03-27 were deferred
# (Mar 23 + Mar 25 PRs) then declared NULL AND VOID (May 13 PR,
# ind_prs13052020.pdf) except NIFTY 50 / Nifty Bank, which had already
# rebalanced Mar 19. Review re-run w.e.f. 2020-06-26.
#
# Keyed on the effective date, not on a file list. The May-13 PR voids the
# releases *dated* Feb 18, Mar 12 and Mar 19; a filename-keyed set previously
# named ind_prs16032020 (Mar 16) instead of ind_prs19032020 (Mar 19), which
# left the Mar-19 announcement live. Only four files carry 2020-03-27 rows and
# all four are inside the deferred tranche, so the date is the exact and
# unambiguous key: nothing took effect on 2020-03-27 but the already-executed
# NIFTY 50 / Bank rebalance.
VOID_COVID_DATE = '2020-03-27'

ANCHOR_DATE = '2026-09-11'  # anchor CSV as-of (last close before Sat 09-12)

COMPANY_ALIASES = {
    # symbol never printed in PR; verified NSE symbol of the named company
    'PATNI COMPUTER SYSTEM': 'PATNI',
}

# Symbol printed in a press release that is not the NSE ticker. Not a rename
# (symbol_changes has no such record), so it cannot go in RENAME_PAIRS: the
# 2014 release prints 'MCDOWELL' for United Spirits Ltd., whose ticker was
# MCDOWELL-N throughout. Surfaced by the union gate, which saw the NIFTY 100
# stream carrying MCDOWELL while the N200 chain carried UNITDSPR.
SYMBOL_ALIASES = {
    'MCDOWELL': 'MCDOWELL-N',
}

# ---------------------------------------------------------------- text extract
# IISL-era PDFs insert stray spaces inside words ('effectiv e', 'c hanges').
BROKEN_WORDS = (('effectiv e', 'effective'), ('c hanges', 'changes'),
                ('ex cluded', 'excluded'), ('in cluded', 'included'),
                ('ef fective', 'effective'), ('ex clusion', 'exclusion'))


def clean_text(text):
    for bad, good in BROKEN_WORDS:
        text = text.replace(bad, good)
    # OCR / wrapped numbered index headers: '10)\nNIFTY 200' -> one line
    text = re.sub(
        r'(?m)^(\s*\(?\d{1,2}\)?)\s*\n\s*(?=(?:S&P\s+)?(?:CNX|NIFTY|Nifty|LIX))',
        r'\1 ', text)
    return text


def pdf_text(path):
    with contextlib.redirect_stderr(io.StringIO()):
        r = pypdf.PdfReader(path)
        return clean_text('\n'.join((p.extract_text() or '')
                                    for p in r.pages))


def ocr_pages_text(name):
    """OCR fallback file stores '===== PAGE i =====' chunks of line-per-row text."""
    path = os.path.join(PR_DIR, name)
    if not os.path.exists(path):
        raise SystemExit(f'OCR transcript missing: {path}')
    raw = open(path, encoding='utf-8').read()
    chunks = raw.split('===== PAGE ')
    lines = []
    for ch in chunks[1:]:
        body = ch.split('\n', 1)[1] if '\n' in ch else ''
        lines.append(body)
    return '\n'.join(lines)


# ---------------------------------------------------------------- date parsing
MONTHS = ('January|February|March|April|May|June|July|August|September|'
          'October|November|December')


TITLE_DATES = None


def listing_title(fname):
    """Official archive listing title for a PR file (carries w.e.f. dates)."""
    global TITLE_DATES
    if TITLE_DATES is None:
        TITLE_DATES = {}
        mp = os.path.join(PR_DIR, 'manifest.csv')
        if os.path.exists(mp):
            with open(mp, encoding='utf-8') as f:
                for r in csv.DictReader(f):
                    TITLE_DATES[r['url'].rsplit('/', 1)[-1]] = r['title']
    return TITLE_DATES.get(fname, '')


DATE_TRIPLE = r'((?:%s)\s+\d{1,2},?\s*\d{4})' % MONTHS


EFF_PATS = [
    r'[Ee]\s*ffectiv\s*e\s+from\s*' + DATE_TRIPLE,
    r'become\s+e\s*ffectiv\s*e\s+from\s*' + DATE_TRIPLE,
    r'w\s*\.\s*e\s*\.\s*f\s*\.?\s*' + DATE_TRIPLE,
    r'with effect from\s*' + DATE_TRIPLE,
]


def first_eff_date(text):
    for p in EFF_PATS:
        m = re.search(p, text)
        if m:
            d = parse_day(m.group(1))
            if d:
                return d
    return None


def parse_effective(text, fname=''):
    d = first_eff_date(text)
    if d:
        return d, 'header'
    # fallback: official archive listing title carries w.e.f. dates
    title = listing_title(fname)
    if title:
        ms = re.findall(r'w\.e\.f\.?\s*' + DATE_TRIPLE, title)
        days = [x for x in (parse_day(x) for x in ms) if x]
        if days:
            tag = 'listing_title' if len(days) == 1 else \
                'listing_title_first_of_%d' % len(days)
            return sorted(days)[0], tag
    return None, None


def parse_day(s):
    m = re.search(r'(%s)\s+(\d{1,2}),?\s*(\d{4})' % MONTHS, s)
    if not m:
        return None
    try:
        from datetime import datetime
        return datetime.strptime(
            f'{m.group(1)} {m.group(2)} {m.group(3)}',
            '%B %d %Y').date().isoformat()
    except ValueError:
        return None


def parse_announced(text, fname):
    m = re.search(r'Date:\s*((?:%s)\s+\d{1,2},?\s*\d{4})' % MONTHS, text)
    if m:
        d = parse_day(m.group(1))
        if d:
            return d, 'pr_date_line'
    m = re.search(r'Mumbai,?\s*((?:%s)\s+\d{1,2},?\s*\d{4})' % MONTHS, text)
    if m:
        d = parse_day(m.group(1))
        if d:
            return d, 'mumbai_line'
    m = re.search(r'ind_prs(\d{2})(\d{2})(\d{4})', fname)
    if m:
        return f'{m.group(3)}-{m.group(2)}-{m.group(1)}', 'filename_fallback'
    return None, None


# ---------------------------------------------------------------- index sections
SEC_PAT = re.compile(
    r'(?m)^\s*\(?(?:\d{1,2}|[A-Za-z])\)?[.\)]\s+((?:S&P\s+)?(?:CNX|NIFTY|Nifty|LIX)(?=[\s0-9])[^\n]{0,70})\s*$')
# lettered subsection headers: 'B. Replacements in Nifty SME Emerge index:'
REVHEAD_PAT = re.compile(
    r'(?m)^\s*\(?[A-Za-z0-9]{1,2}\)?[.\)]\s+Replacements in\s+'
    r'((?:S&P\s+)?(?:CNX|NIFTY|Nifty|LIX)(?=[\s0-9])[^\n:]{0,60}?)\s*'
    r'(?:index)?\s*:?\s*$')


SINGLE_PAT = re.compile(
    r'in (?:this regard in )?((?:S&P\s+)?CNX [A-Za-z0-9 &\'.\-]*?[Ii]ndex|'
    r'NIFTY [A-Za-z0-9 &\'.\-]*?[Ii]ndex)', re.I)
# restated fragment headers without numbers: 'CNX Nifty Junior Index'
RESTATED_PAT = re.compile(
    r'(?m)^\s*((?:S&P\s+)?(?:CNX|NIFTY|Nifty|LIX)(?=[\s0-9])[A-Za-z0-9 &\'.\-]{0,60}?Index\.?)\s*$')


def norm_index(raw):
    u = re.sub(r'\s+', ' ', raw).strip().upper()
    strat = ('EQUAL WEIGHT', 'MOMENTUM', 'ALPHA', 'BETA', 'VOLATILITY',
             'QUALITY', 'VALUE', 'DIVIDEND', 'GROWTH', 'LIQUID 15',
             'LIQUIDITY', 'ARBITRAGE', 'MULTICAP', '50:25:25', 'LARGEMIDSMALL',
             'EQUAL', 'TOTAL MARKET', 'MIDSMALLCAP', 'SHARIAH', 'SME',
             'EMERGE', 'IPO', 'ESG', 'ENHANCED', 'LEADERS', 'SELECT',
             'FLEXICAP', 'MULTIFACTOR', 'FACTOR', 'LOW', 'HIGH', '50:30:20')
    if any(s in u for s in strat):
        return u
    if 'MIDCAP 100' in u:
        if 'FULL' in u or 'FREE FLOAT' in u or 'FREEFLOAT' in u:
            return u
        return 'NIFTY MIDCAP 100'
    if 'CNX 200' in u or 'NIFTY 200' in u or 'NIFTY200' in u:
        return 'NIFTY 200'
    if 'CNX 100' in u or 'NIFTY 100' in u or 'NIFTY100' in u:
        return 'NIFTY 100'
    if 'CNX 500' in u or 'NIFTY 500' in u or 'NIFTY500' in u:
        return 'NIFTY 500'
    if 'NIFTY JUNIOR' in u or 'NEXT 50' in u:
        return 'NIFTY NEXT 50'
    if re.match(r"^(S&P\s+)?CNX NIFTY( |$)", u) or re.search(
            r'\bNIFTY 50\b(?!0)', u):
        return 'NIFTY 50'
    return u


def sections_of(text):
    heads = [(m.group(1).strip(), m.start(), m.end())
             for m in SEC_PAT.finditer(text)]
    heads += [(m.group(1).strip(), m.start(), m.end())
              for m in REVHEAD_PAT.finditer(text)]
    heads += [(m.group(1).strip(), m.start(), m.end())
              for m in RESTATED_PAT.finditer(text)
              if len(m.group(1).strip()) <= 60]
    # dedup overlapping matches, sort by position
    seen_pos, uniq = set(), []
    for name, s, e in sorted(heads, key=lambda x: x[1]):
        if s in seen_pos:
            continue
        seen_pos.add(s)
        uniq.append((name, s, e))
    heads = uniq
    if not heads:
        m = SINGLE_PAT.search(text)
        if m:
            return [(m.group(1).strip(), text)]
        return []
    out = []
    for i, (name, _s, e) in enumerate(heads):
        hi = heads[i + 1][1] if i + 1 < len(heads) else len(text)
        out.append((name, text[e:hi]))
    return out


# ---------------------------------------------------------------- row parsing
SYM_PAT = re.compile(r'^[A-Z0-9][A-Z0-9&\-\.\']{1,14}$')
SKIP_PAT = re.compile(
    r'^(Sr\.?\s*No\.?|Company Name|Scrip Name|Symbol|The following|Note\b|'
    r'Place\b|Date\b|IISL|INDIA INDEX|PRESS RELEASE|Mumbai|A joint venture|'
    r'The Index Maintenance|various indices|periodic review|'
    r'above replacements|below|applicable|All the constituents|'
    r'Constituents of|pursuant|derived|which are|NSE Indices|'
    r'ensures accuracy|professional advice|reference purpose|'
    r'For detailed|methodology document|www\.|email|Tel|Fax|Contact|'
    r'On account of|securities\.?$|'
    r'(Sr|No|Scrip|Name|Symbol|being)\.?$|'
    r'^No\.\s*(Company|Scrip)|'
    r'No (change|inclusion) is being|'
    r'A joint venture|Securities of|National Stock Exchange w|to SEBI\b|'
    r'delisting pursuant|pursuant to|suspended|will be suspended|'
    r'Regulations,|on account of|w\.e\.f\.)',
    re.I)


TAIL_PAT = re.compile(
    r'\s*The following (companies|company|scrips?|scrip)\b.*$'
    r'|\s*The above.*$'
    r'|\s*Sr\.?\s*No\.?.*$'
    r'|\s*Company Name.*$'
    r'|\s*Scrip Name.*$'
    r'|\s*Symbol\s*$'
    r'|\s*No change is being made.*$'
    r'|\s*No inclusion is being made.*$'
    r'|\s*About National Stock Exchange.*$'
    r'|\s*About NSE Indices.*$'
    r'|\s*For more information.*$'
    r'|\s*Press contact.*$', re.I | re.S)

# wrapped-fragment lines end mid-phrase (dangling preposition/auxiliary):
# never a complete company row
DANGLING_PAT = re.compile(
    r'\b(of|of:|and|the|in|for|to|from|as|is|are|was|be|been|a|an|on|'
    r'with|by|at|its|this|that|these|those|which|who|or|if|than|such|'
    r'not|only|own|same|can|will|just|should|now|has|have|had|were)\s*[:;]?\s*$',
    re.I)

SUFFIX_PAT = re.compile(r'(LTD\.?|LIMITED|CO\.?|COMPANY)$', re.I)


def split_actions(sec_text):
    """Return (excluded_rows, included_rows) for one index section.

    Unified line state machine: handles numbered tables (with wrapped
    continuations), symbol-less left columns of two-column layouts, and
    bare company/symbol pairs (right-column fragments, OCR text).
    """
    excl_rows, incl_rows = [], []
    for a, co, sy, _num in scan_section(sec_text):
        if a == 'exclude':
            excl_rows.append((co, sy))
        elif a == 'include':
            incl_rows.append((co, sy))
    return excl_rows, incl_rows


def scan_lines(sec_text):
    """Yield (action, company, symbol|None, numbered) in document order."""
    out = []
    state = None
    pending = None

    def flush_pending():
        nonlocal pending
        if pending is not None:
            if not is_junk_line(pending) and 'following' not in \
                    pending.lower():
                out.append((state, pending, None, False))
            pending = None


OCR_JUNK_PAT = re.compile(
    r'^(NSE|India@|A guiding light|shining bright|Sr\.?\s*No\.?|'
    r'Company Name|Scrip Name|Symbol|The following|being excluded:?|'
    r'being included:?|Note\b|Place\b|'
    r'Date\b|NSE Indices|indices under|and hybrid indices|\(?Page \d+\)?)$',
    re.I)

LONE_SYM_PAT = re.compile(r'^[A-Z][A-Z0-9&\-\.\']{1,14}$')
LONE_NUM_PAT = re.compile(r'^\(?\d{1,3}\)?$')
NUMROW_PAT = re.compile(r'^(\d{1,3})\s+(.*)$')
PAIR_PAT = re.compile(r'^(.+?)\s+([A-Z][A-Z0-9&\-\.\']{2,15})\s*$')
EXTRA_JUNK_PAT = re.compile(
    r'^(NSE|India@|A guiding light|shining bright|\(?Page \d+\)?)$', re.I)


# A line opening with a footnote marker annotates the row above ('* Excluded
# on account of inclusion in Nifty 100', '# On account of proposed scheme of
# arrangement') and is never a data row. The continuation state machine
# otherwise glues it onto that row and peels its last token as the symbol, so
# 'Nifty Midcap 150' yielded the symbol '150'. A release can carry two markers
# in one table, so both are matched.
FOOTNOTE_PAT = re.compile(r'^\s*[*#]\s*[A-Za-z]')


def is_junk_line(ln):
    return bool(SKIP_PAT.match(ln) or EXTRA_JUNK_PAT.match(ln)
                or FOOTNOTE_PAT.match(ln))


def parse_row_text(s):
    """Parse 'Company ... SYM' remainder into (company, symbol|None)."""
    body = TAIL_PAT.sub('', s).strip(' -–—')
    body = re.sub(r'\s+On account of.*$', '', body).strip(' -–—')
    # Footnote glued onto the same extracted line as the row it annotates
    # ('Tata Power Co. Ltd.* TATAPOWER *Excluded on account of exclusion from
    # Nifty Midcap 150'): the trailing peel then takes '150' as the symbol.
    # Strip from the footnote marker; a bare '*' on the company is dropped
    # by the token filter below.
    body = re.sub(r'\s\*[A-Z][a-z].*$', '', body).strip(' -–—')
    toks = [t for t in body.split(' ') if t != '*']
    # Peel trailing ALL-CAPS fragments into the symbol (extraction
    # splits e.g. ADANIPORTS -> 'ADANIPOR TS'). At most 2 fragments
    # with joined length <= 12 (longest real symbols are ~10 chars),
    # which also blocks qualifier words ('DVR' + 'TATAMTRDVR').
    sym = None
    frags = []
    while toks and re.match(r'^[A-Z0-9&\-\.\']+$', toks[-1]) \
            and len(frags) < 2:
        rest = toks[:-1]
        if not rest:
            break
        head = ' '.join(rest)
        if not (re.search(r'[a-z]', head) or SUFFIX_PAT.search(head)):
            break
        frag = toks.pop()
        if len(frag + ''.join(frags)) > 12:
            toks.append(frag)
            break
        frags.insert(0, frag)
    if frags:
        sym = ''.join(frags)
    company = ' '.join(toks).strip(' -–—')
    if not company and sym:
        company = sym  # bare-symbol row (e.g. legacy 'IFCI')
    return company, sym


GLUE_SUFFIX_PAT = re.compile(
    r'(LTD\.?|LIMITED|CO\.?|COMPANY|CORP\.?|INC\.?|PLC|BANK|FINANCE|'
    r'INDUSTRIES|MOTORS|CEMENTS?|STEELS?|PHARMA|LABS\.?|FOODS?|MILLS?|'
    r'TYRES?|PAPER|SUGARS?|HOTELS?|POWER|ENERGY|GAS|OIL|PORTS?|MEDIA|'
    r'METALS?|MINES?|TEXTILES?|REALTY|RETAIL|FASHIONS?|RESORTS?|'
    r'BREWERIES|BEVERAGES|CHEMICALS?|FERTILISERS?|FERTILIZERS?)$', re.I)


def scan_section(sec_text):
    """Line state machine over one index section.

    Returns [(action, company, symbol|None, numbered)] covering both
    numbered tables (possibly symbol-less left columns of two-column
    layouts) and bare company/symbol pairs (right-column fragments).
    """
    rows = []
    state = None
    pending = None  # company line awaiting its symbol (bare-pair layouts)
    marker_buf = ''  # accumulates action markers split across lines
    seen_marker = False  # any action marker (worded or resolved) in section

    def flush_pending():
        nonlocal pending
        if pending is not None:
            if not is_junk_line(pending) and 'following' not in \
                    pending.lower():
                rows.append((state, pending, None, False))
            pending = None

    lines = sec_text.split('\n')
    i, n = 0, len(lines)
    while i < n:
        ln = re.sub(r'\s+', ' ', lines[i]).strip(' -–—')
        i += 1
        if not ln:
            continue
        low = ln.lower()
        # action markers may split across lines ('... company is' / 'being');
        # a wordless marker resolves positionally (NSE lists excludes first)
        if low == 'being' or re.match(
                r'^the following (company|companies) (is|are)(\s+being)?$',
                low):
            marker_buf = (marker_buf + ' ' + ln).strip()
            low = marker_buf.lower()
        else:
            if marker_buf:
                ml = ln.lower()
                if ml.startswith('excluded'):
                    state, seen_marker = 'exclude', True
                elif ml.startswith('included'):
                    state, seen_marker = 'include', True
                else:
                    # abandoned wordless marker: NSE lists excludes first
                    state = 'include' if seen_marker else 'exclude'
                    seen_marker = True
                flush_pending()
                marker_buf = ''
                if ml.startswith('excluded') or ml.startswith('included'):
                    continue
            # fall through to normal processing of ln
        if 'being excluded' in low:
            flush_pending()
            state = 'exclude'
            seen_marker = True
            marker_buf = ''
            continue
        if 'being included' in low:
            flush_pending()
            state = 'include'
            seen_marker = True
            marker_buf = ''
            continue
        if marker_buf:
            continue  # incomplete marker fragment; wait for its rest
        if state is None:
            continue
        if is_junk_line(ln) or LONE_NUM_PAT.match(ln):
            continue
        m = NUMROW_PAT.match(ln)
        if m:
            flush_pending()
            # gather wrapped continuation lines (not symbols/pairs/headers)
            body = m.group(2)
            while i < n:
                nx = re.sub(r'\s+', ' ', lines[i]).strip(' -–—')
                if not nx or 'being excluded' in nx.lower() or \
                        'being included' in nx.lower() or \
                        nx.lower() == 'being' or re.match(
                            r'^the following (company|companies) (is|are)'
                            r'(\s+being)?$', nx.lower()):
                    break
                if NUMROW_PAT.match(nx) or is_junk_line(nx) or \
                        LONE_NUM_PAT.match(nx):
                    break
                if LONE_SYM_PAT.match(nx):
                    # the row's own symbol wrapped onto the next line
                    # (dominant in 2011-2013 PRs) — but only when the
                    # body has no symbol yet; else it starts a bare row
                    _c0, _s0 = parse_row_text(body)
                    if _s0 is None:
                        body += ' ' + nx
                        i += 1
                        continue
                    break
                pm2 = PAIR_PAT.match(nx)
                if pm2:
                    # glue only a short corporate-suffix wrap (e.g.
                    # 'Corporation Ltd. IRCTC') onto a still-symbol-less
                    # body; anything else starts a new bare row below
                    _co_test, _sy_test = parse_row_text(body)
                    w = pm2.group(1).split(' ')
                    if _sy_test is None and len(w) <= 2 and \
                            GLUE_SUFFIX_PAT.search(pm2.group(1)):
                        body += ' ' + nx
                        i += 1
                        continue
                    break
                if NUMROW_PAT.match(nx) or LONE_SYM_PAT.match(nx) or \
                        is_junk_line(nx) or LONE_NUM_PAT.match(nx):
                    break
                pm2 = PAIR_PAT.match(nx)
                if pm2:
                    # glue only a short corporate-suffix wrap (e.g.
                    # 'Corporation Ltd. IRCTC') onto a still-symbol-less
                    # body; anything else starts a new bare row below
                    _co_test, _sy_test = parse_row_text(body)
                    w = pm2.group(1).split(' ')
                    if _sy_test is None and len(w) <= 2 and \
                            GLUE_SUFFIX_PAT.search(pm2.group(1)):
                        body += ' ' + nx
                        i += 1
                        continue
                    break
                body += ' ' + nx
                i += 1
            co, sy = parse_row_text(body)
            if co and not SKIP_PAT.match(co) and not DANGLING_PAT.search(co):
                rows.append((state, co, sy, True))
            continue
        if LONE_SYM_PAT.match(ln):
            if pending is not None:
                rows.append((state, pending, ln, False))
                pending = None
            else:
                pending = ln
            continue
        pm = PAIR_PAT.match(ln)
        if pm:
            # single-line 'Company ... SYM' (also split-symbol wraps like
            # 'ADANIPOR TS'): reuse the greedy row parser
            flush_pending()
            co, sy = parse_row_text(ln)
            if co and not SKIP_PAT.match(co):
                rows.append((state, co, sy, False))
            continue
        # plain company line: may pair with a following symbol line
        if pending is not None and re.match(r'^[A-Z][A-Z0-9&\-\.\']+$',
                                            pending) \
                and ' ' not in pending:
            rows.append((state, ln, pending, False))
            pending = None
        else:
            flush_pending()
            pending = ln
    flush_pending()
    out = []
    for a, c, s, num in rows:
        if SKIP_PAT.match(c) or OCR_JUNK_PAT.match(c) or \
                'following' in c.lower() or DANGLING_PAT.search(c):
            continue
        out.append((a, c, s, num))
    return out


# ------------------------------------------- inverted-format blocks (index-per-row)
# e.g. ind_prs23082024_1.pdf: one company excluded from a LIST of indices
# ('... (Symbol: TATAMTRDVR) shall be excluded from the following indices:'
#  followed by numbered index names).
INVERTED_PAT = re.compile(
    r'shall be (excluded|included)(?: from| in) the following indices', re.I)
INVERTED_SYM_PAT = re.compile(r'\(Symbol:\s*([A-Z0-9&\-\.\']+)\)')
INVERTED_ROW_PAT = re.compile(r'(?m)^\s*(\d{1,3})\s+([^\n]{2,70})\s*$')


def parse_inverted(text, fname, eff, eff_src, ann, ann_src):
    """Return (events, consumed_spans) for inverted-format blocks."""
    events, spans = [], []
    for m in INVERTED_PAT.finditer(text):
        action = 'exclude' if m.group(1).lower() == 'excluded' else 'include'
        pre = text[max(0, m.start() - 900):m.start()]
        sm = INVERTED_SYM_PAT.search(pre)
        if not sm:
            continue
        sym = sm.group(1)
        co = re.sub(r'\s+', ' ', pre[:sm.start()]).strip(' -–—,.')
        # company is the tail phrase before '(Symbol: ...)'; drop preamble
        co = re.split(r'[.;]\s*(?=[A-Z])', co)[-1].strip(' ,')
        # numbered index list after the marker
        tail = text[m.end():]
        idx_names, end_off = [], 0
        for rm in INVERTED_ROW_PAT.finditer(tail):
            if rm.start() - end_off > 120 and end_off:
                break
            idx_names.append(rm.group(2).strip())
            end_off = rm.end()
        if not idx_names:
            continue
        spans.append((m.start(), m.end() + end_off))
        for seq, raw_idx in enumerate(idx_names):
            idx = norm_index(raw_idx)
            events.append((fname, ann, ann_src, eff, eff_src, raw_idx, idx,
                           action, seq, co, sym, 'parsed'))
    return events, spans


# ------------------------------------------------------- revocation-format PRs
# e.g. ind_prs25092024.pdf: table (Sr.No, Index, Security, Symbol, Remarks)
# with Remarks in {Exclusion, Exclusion revoked, Inclusion revoked}.
# Revoked rows are NO-OPs; they cancel same-symbol events from the PR named
# via 'read in consonance with the press release issued on <date>'.
REVOC_VOCAB = [
    'Nifty MidSmall IT & Telecom', 'Nifty500 Multicap Infrastructure 50:30:20',
    'Nifty MidSmallcap 400', 'Nifty LargeMidcap 250', 'Nifty Smallcap 250',
    'Nifty Smallcap 100', 'Nifty Midcap 150', 'Nifty Midcap Select',
    'Nifty Midcap 100', 'Nifty Midcap 50', 'Nifty Total Market',
    'Nifty India Digital', 'Nifty Rural', 'Nifty 500', 'Nifty 200',
    'Nifty 100', 'Nifty 50',
]
TRIPLE_PAT = re.compile(
    r'(.+?)\s+([A-Z][A-Z0-9&\-\.\']{2,15})\s+'
    r'((?:Exclusion|Inclusion)(?: revoked)?)(?=\s|$)')


def is_revocation_format(text):
    low = text.lower()
    return 'revocation of exclusion' in low or 'exclusion revoked' in low


def parse_revocation(text, fname, eff, eff_src, ann, ann_src):
    flat = re.sub(r'\s+', ' ', text)
    tgt = None
    m = re.search(r'press release issued on\s*((?:%s)\s+\d{1,2},?\s*\d{4})'
                  % MONTHS, flat)
    if m:
        tgt = parse_day(m.group(1))
    events, directives = [], []
    parts = re.split(r'(?m)^\s*(\d{1,3})\s+', text)
    seq = 0
    for j in range(1, len(parts), 2):
        chunk = re.sub(r'\s+', ' ', parts[j + 1]).strip()
        idx_at = -1
        idx_name = None
        for vocab in sorted(REVOC_VOCAB, key=len, reverse=True):
            k = chunk.find(vocab)
            if k >= 0 and (idx_at < 0 or k < idx_at):
                idx_at, idx_name = k, vocab
        if idx_name is None:
            continue
        rest = chunk[idx_at + len(idx_name):]
        for tm in TRIPLE_PAT.finditer(rest):
            company = tm.group(1).strip(' -–—#')
            sym = tm.group(2)
            rem = tm.group(3)
            if SKIP_PAT.match(company) or len(company) < 3:
                continue
            idx = norm_index(idx_name)
            if rem == 'Exclusion':
                events.append((fname, ann, ann_src, eff, eff_src, idx_name,
                               idx, 'exclude', seq, company, sym, 'parsed'))
            elif rem == 'Exclusion revoked':
                events.append((fname, ann, ann_src, eff, eff_src, idx_name,
                               idx, 'revoked_exclude', seq, company, sym,
                               'revocation_note'))
                directives.append((tgt, idx, sym, 'exclude'))
            elif rem == 'Inclusion revoked':
                events.append((fname, ann, ann_src, eff, eff_src, idx_name,
                               idx, 'revoked_include', seq, company, sym,
                               'revocation_note'))
                directives.append((tgt, idx, sym, 'include'))
            elif rem == 'Inclusion':
                events.append((fname, ann, ann_src, eff, eff_src, idx_name,
                               idx, 'include', seq, company, sym, 'parsed'))
            seq += 1
    return events, directives


# NSE sometimes states a Nifty 200 / LargeMidcap 250 change as a prose
# super-set clause instead of a table: "NIFTY 200, being a super-set of NIFTY
# 100 and NIFTY Midcap 100, PVR Limited will be included in NIFTY 200 index
# upon its proposed inclusion in NIFTY Midcap 100 index." The table scanner
# sees nothing there, so the directive was absent from the event stream
# altogether — and a missing include paired with a missing exclude is invisible
# to the backward walk (which records contradictions only) and to the count
# gate (which bounds the net, not the gross, error).
SUPERSET_PAT = re.compile(
    r'([A-Z][A-Za-z0-9&\'.\- ]{2,60}?)\s+will\s+(?:also\s+)?be\s+'
    r'(includ|exclud)ed\s+in\s+(?:S&P\s+)?(?:CNX|NIFTY|Nifty)[^.,]{0,60}?'
    r'index\s+upon\s+its\s+proposed\s+(?:in|ex)clusion\s+in')


def norm_company(c):
    c = c.upper()
    c = re.sub(r'\s+', ' ', c)
    c = re.sub(r'\b(LTD\.?|LIMITED|CO\.?|COMPANY|\(INDIA\)|INDIA LTD\.?)\b', '', c)
    return re.sub(r'[^A-Z0-9& ]', '', c).strip()


def parse_file(path, fallback_text=None):
    fname = os.path.basename(path)
    text = fallback_text if fallback_text is not None else pdf_text(path)
    eff, eff_src = parse_effective(text, fname)
    ann, ann_src = parse_announced(text, fname)
    if is_revocation_format(text):
        return parse_revocation(text, fname, eff, eff_src, ann, ann_src)
    inv_events, spans = parse_inverted(text, fname, eff, eff_src, ann,
                                       ann_src)
    if spans:
        # strip consumed inverted blocks so section parsing sees only
        # the standard company-row tables (e.g. Part B Shariah tables)
        cuts = sorted(spans)
        pieces, pos = [], 0
        for s, e in cuts:
            pieces.append(text[pos:s])
            pos = e
        pieces.append(text[pos:])
        text = '\n'.join(pieces)
    events = list(inv_events)
    for raw_idx, sec_text in sections_of(text):
        idx = norm_index(raw_idx)
        sec_eff = first_eff_date(sec_text)
        if sec_eff and sec_eff != eff:
            eff_use, eff_src_use = sec_eff, 'section'
        else:
            eff_use, eff_src_use = eff, eff_src
        excl, incl = split_actions(sec_text)
        for m in SUPERSET_PAT.finditer(sec_text):
            (incl if m.group(2) == 'includ' else excl).append(
                (m.group(1).strip(), None))
        for seq, (co, sy) in enumerate(excl):
            events.append((fname, ann, ann_src, eff_use, eff_src_use, raw_idx,
                           idx, 'exclude', seq, co, sy))
        for seq, (co, sy) in enumerate(incl):
            events.append((fname, ann, ann_src, eff_use, eff_src_use, raw_idx,
                           idx, 'include', seq, co, sy))
    return events, []


def main():
    files = sorted(glob.glob(os.path.join(PR_DIR, 'ind_prs*.pdf')))
    print('pdfs:', len(files), flush=True)
    all_events, all_directives = [], []
    for f in files:
        fn = os.path.basename(f)
        fb = None
        if fn in OCR_FALLBACK:
            fb = ocr_pages_text(OCR_FALLBACK[fn])
        evs, dirs = parse_file(f, fb)
        all_events.extend(evs)
        all_directives.extend((fn,) + d for d in dirs)
    print('raw events:', len(all_events),
          'revocation directives:', len(all_directives), flush=True)

    # symbol resolution pass for symbol=None via same-company events,
    # then reverse symbol->company map (lone-symbol fragments), then
    # verified company aliases (symbol never printed in any PR)
    known = {}
    known_sym = {}
    known_nospace = {}
    for e in all_events:
        co, sy = e[9], e[10]
        if sy:
            known.setdefault(norm_company(co), set()).add(sy)
            known_sym.setdefault(sy, set()).add(co)
            known_nospace.setdefault(
                re.sub(r'[^A-Z0-9&]', '', norm_company(co)), set()).add(sy)
    fixed, events = 0, []
    for e in all_events:
        co, sy = e[9], e[10]
        status = 'parsed'
        if not sy:
            cands = known.get(norm_company(co), set())
            if not cands:
                cands = known_nospace.get(
                    re.sub(r'[^A-Z0-9&]', '', norm_company(co)), set())
            if len(cands) == 1:
                sy, status = next(iter(cands)), 'resolved_company'
            elif re.match(r'^[A-Z][A-Z0-9&\-\.\']+$', co.strip()) \
                    and ' ' not in co.strip() \
                    and co.strip() in known_sym:
                # lone all-caps token from a fragment: it IS the symbol
                tok = co.strip()
                co = sorted(known_sym[tok])[0]
                sy, status = tok, 'resolved_symbol'
            elif norm_company(co) in COMPANY_ALIASES:
                sy, status = COMPANY_ALIASES[norm_company(co)], \
                    'resolved_alias'
            else:
                status = 'missing_symbol'
        if sy in SYMBOL_ALIASES:
            sy, status = SYMBOL_ALIASES[sy], 'resolved_alias'
        events.append([e[0], e[1], e[2], e[3], e[4], e[5], e[6], e[7], e[8],
                       co, sy, status])
        if status.startswith('resolved'):
            fixed += 1
    print('resolved missing symbols:', fixed, flush=True)

    # dedup identical rows within a file/index/action; then subsume
    # symbol-less rows covered by a same-company row WITH a symbol
    seen, deduped = set(), []
    for e in events:
        key = (e[0], e[6], e[7], norm_company(e[9]), e[10])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(e)
    print('deduped events:', len(deduped), flush=True)
    covered = set()
    for e in deduped:
        if e[10] and e[11] not in ('superseded', 'duplicate', 'void_covid'):
            covered.add((e[0], e[6], e[7], norm_company(e[9])))
    n_sub = 0
    kept = []
    for e in deduped:
        if not e[10] and (e[0], e[6], e[7], norm_company(e[9])) in covered:
            n_sub += 1
            continue
        kept.append(e)
    deduped = kept
    print('subsumed symbol-less rows:', n_sub, flush=True)

    # March-2020 COVID void (see VOID_COVID_DATE): every row effective exactly
    # 2020-03-27 except NIFTY 50 / Nifty Bank, which rebalanced Mar 19.
    n_void = 0
    for e in deduped:
        if str(e[3]) == VOID_COVID_DATE \
                and e[6] != 'NIFTY 50' and 'BANK' not in e[6]:
            e[11] = 'void_covid'
            n_void += 1
    print('void_covid:', n_void, flush=True)

    # revocation supersedes: cancel matching events in the referenced PR
    n_sup, n_dup = 0, 0
    for src_fn, tgt_ann, idx, sym, cancelled in all_directives:
        if tgt_ann is None:
            print('  WARN no target PR date for revocation in', src_fn,
                  flush=True)
            continue
        for e in deduped:
            if e[11] in ('superseded', 'duplicate', 'void_covid'):
                continue
            if e[0] == src_fn or e[6] != idx or e[10] != sym \
                    or e[7] != cancelled or str(e[1]) != tgt_ann:
                continue
            e[11] = 'superseded'
            n_sup += 1
    # cross-file duplicates: same (index, action, symbol, effective date)
    # announced twice (revocation PRs restate some rows)
    first = {}
    for e in deduped:
        if e[7] not in ('exclude', 'include') or e[11] in (
                'superseded', 'duplicate', 'void_covid') \
                or not e[3] or not e[10]:
            continue
        key = (e[6], e[7], e[10], str(e[3]))
        if key in first:
            e[11] = 'duplicate'
            n_dup += 1
        else:
            first[key] = e[0]
    print('superseded:', n_sup, 'cross-file duplicates:', n_dup, flush=True)

    os.makedirs(os.path.dirname(OUT_DB), exist_ok=True)
    if os.path.exists(OUT_DB):
        os.remove(OUT_DB)
    con = duckdb.connect(OUT_DB)
    con.execute(
        'create table n200_events (pr_file VARCHAR, announcement_date DATE, '
        'ann_src VARCHAR, effective_date DATE, eff_src VARCHAR, '
        'index_raw VARCHAR, index_norm VARCHAR, action VARCHAR, seq INTEGER, '
        'company VARCHAR, symbol VARCHAR, symbol_status VARCHAR)')
    con.executemany('insert into n200_events values (?,?,?,?,?,?,?,?,?,?,?,?)',
                    deduped)
    # summary
    for row in con.execute(
            "select index_norm, action, count(*) from n200_events "
            "where index_norm in ('NIFTY 200','NIFTY 100','NIFTY 500',"
            "'NIFTY MIDCAP 100') group by 1,2 order by 1,2").fetchall():
        print(' ', row, flush=True)
    print('no-effective-date N200 events:',
          con.execute("select count(*) from n200_events where "
                      "index_norm='NIFTY 200' and effective_date is null").fetchone()[0],
          flush=True)
    print('missing-symbol N200 events:',
          con.execute("select count(*) from n200_events where "
                      "index_norm='NIFTY 200' and symbol is null").fetchone()[0],
          flush=True)

    build_chain(con, deduped)
    con.close()
    print('wrote', OUT_DB, flush=True)


LAUNCH_DATE = '2011-07-19'  # CNX 200 launch (ind_prs18072011.pdf)


def load_anchor():
    """Today's official Nifty 200 list -> {symbol: company}."""
    cands = sorted(glob.glob(os.path.join(PR_DIR, 'ind_nifty200list_*.csv')))
    if not cands:
        raise SystemExit('anchor CSV missing')
    anchor = {}
    with open(cands[-1], encoding='utf-8') as f:
        for r in csv.DictReader(f):
            sym = (r.get('Symbol') or '').strip().upper()
            if sym:
                anchor[sym] = (r.get('Company Name') or '').strip()
    return anchor


GATE_START = '2018-06-29'  # first NIFTY MIDCAP 100 event under the stable label


def load_list_csv(pattern):
    cands = sorted(glob.glob(os.path.join(PR_DIR, pattern)))
    if not cands:
        raise SystemExit(f'anchor CSV missing: {pattern}')
    with open(cands[-1], encoding='utf-8') as f:
        return {(r.get('Symbol') or '').strip().upper()
                for r in csv.DictReader(f) if (r.get('Symbol') or '').strip()}


def stream_events(deduped, index_norm):
    evs = [e for e in deduped
           if e[6] == index_norm and e[7] in ('exclude', 'include')
           and e[11] not in ('superseded', 'duplicate', 'void_covid')
           and e[3] and e[10] and str(e[3]) <= ANCHOR_DATE]
    evs.sort(key=lambda e: (str(e[3]), str(e[1]), e[0], e[8]))
    return evs


def walk_stream(anchor, evs, canon):
    """Backward walk to the launch state, then forward replay.

    Returns (launch_state, [(date, set_after_that_date)], breaks).
    """
    state = set(canon(s) for s in anchor)
    by_date = {}
    for e in evs:
        by_date.setdefault(str(e[3]), []).append(e)
    breaks = []
    for d in sorted(by_date, reverse=True):
        for e in reversed(by_date[d]):
            sym = canon(e[10])
            if e[7] == 'include':
                if sym not in state:
                    breaks.append((d, 'reverse-include-absent', sym))
                else:
                    state.discard(sym)
            else:
                if sym in state:
                    breaks.append((d, 'reverse-exclude-present', sym))
                else:
                    state.add(sym)
    launch, cur, snaps = frozenset(state), set(state), []
    for d in sorted(by_date):
        for e in by_date[d]:
            sym = canon(e[10])
            if e[7] == 'include':
                cur.add(sym)
            else:
                cur.discard(sym)
        snaps.append((d, frozenset(cur)))
    return launch, snaps, breaks


def as_of(launch, snaps, d):
    cur = launch
    for dt, s in snaps:
        if dt > d:
            break
        cur = s
    return cur


def pre_listing_gate(con):
    """Flag intervals that assert membership before the security first traded.

    A name that no event ever touches is carried silently back to LAUNCH_DATE
    by the backward walk — no break fires, and the count gate sees only the net
    imbalance. Two causes: a rename the label chain does not cover (fixable, and
    RENAME_PAIRS now covers the ones the corpus contains), and a genuine phantom
    whose entry appears in no press release (not fixable from the sources).
    Reported per name so the second kind is visible instead of implicit.
    """
    db = os.path.join(ROOT, 'data', 'market_data', 'equity_bhavcopy.duckdb')
    con.execute(f"attach '{db}' as eq (read_only)")
    rows = con.execute(
        'select m.symbol, m.valid_from, f.ft from n200_membership m '
        'left join (select symbol, min(trade_date) ft from eq.equity_bhavcopy '
        'group by 1) f on f.symbol = m.symbol '
        'where f.ft is null or f.ft > m.valid_from + INTERVAL 5 DAY '
        'order by f.ft - m.valid_from desc').fetchall()
    con.execute('detach eq')
    print('pre-listing intervals:', len(rows), flush=True)
    for s, vf, ft in rows:
        print(f'  PRELIST {s} from {vf}, first trade {ft}', flush=True)
    return [('pre_listing_intervals', str(len(rows)))] + \
           [('pre_listing', f'{s}|{vf}|{ft}') for s, vf, ft in rows]


def union_gate(con, deduped, canon):
    """Independent reconstruction: NIFTY 200 = NIFTY 100 + NIFTY Midcap 100.

    NSE states the rule in the press releases themselves ("NIFTY 200, being a
    super-set of NIFTY 100 and NIFTY Midcap 100"), and today's three official
    lists satisfy it exactly: 100 + 100, disjoint, union == the 200.

    This is the only check in the build that can see a MISSING inclusion paired
    with a MISSING exclusion. The backward walk records contradictions only, so
    a name touched by no event is silently carried back to LAUNCH_DATE; the
    count gate bounds the net error, so a symmetric pair of dropped events
    leaves it reading 200. Rebuilding the index from two independent event
    streams has neither blind spot.

    Scoped to GATE_START onward: before 2018-06-29 the midcap stream is spread
    across five renamed labels (CNX Midcap, Nifty Free Float Midcap 100, Nifty
    Full Midcap 100, ...) and reconstructing it is a separate problem.
    """
    n100_evs = stream_events(deduped, 'NIFTY 100')
    m100_evs = stream_events(deduped, 'NIFTY MIDCAP 100')
    n100_l, n100_s, n100_b = walk_stream(
        load_list_csv('ind_nifty100list_*.csv'), n100_evs, canon)
    m100_l, m100_s, m100_b = walk_stream(
        load_list_csv('ind_niftymidcap100list_*.csv'), m100_evs, canon)
    print('union gate: N100 events', len(n100_evs), 'breaks', len(n100_b),
          '| Midcap100 events', len(m100_evs), 'breaks', len(m100_b),
          flush=True)

    dates = sorted({d for d, _ in n100_s} | {d for d, _ in m100_s}
                   | {str(r[0]) for r in con.execute(
                       'select distinct valid_from from n200_membership')
                      .fetchall()})
    dates = [d for d in dates if GATE_START <= d <= ANCHOR_DATE]
    audit, n_bad = [], 0
    for d in dates:
        want = as_of(n100_l, n100_s, d) | as_of(m100_l, m100_s, d)
        got = {canon(r[0]) for r in con.execute(
            'select symbol from n200_membership where valid_from<=? '
            'and (valid_to is null or valid_to>?)', [d, d]).fetchall()}
        extra, missing = sorted(got - want), sorted(want - got)
        if extra or missing:
            n_bad += 1
            audit.append(('union_mismatch',
                          f'{d}|extra={",".join(extra)}|'
                          f'missing={",".join(missing)}'))
    print(f'union gate: {len(dates)} dates checked, {n_bad} mismatched',
          flush=True)
    for _, det in audit[:20]:
        print('  UNION', det, flush=True)
    return [('union_gate_start', GATE_START),
            ('union_gate_dates', str(len(dates))),
            ('union_gate_mismatch_dates', str(n_bad)),
            ('union_gate_n100_breaks', str(len(n100_b))),
            ('union_gate_m100_breaks', str(len(m100_b)))] + audit


def build_chain(con, deduped):
    anchor = load_anchor()
    print('anchor members:', len(anchor), flush=True)
    rename_dates = load_rename_dates()
    print('rename pairs loaded:', len(rename_dates), flush=True)
    canon = lambda s: canonical_label(s, rename_dates)

    future = [e for e in deduped
              if e[6] == 'NIFTY 200' and e[7] in ('exclude', 'include')
              and e[11] not in ('superseded', 'duplicate', 'void_covid')
              and e[3] and e[10] and str(e[3]) > ANCHOR_DATE]
    print('future-effective N200 events (announced, not yet effective):',
          len(future), flush=True)
    for e in future:
        print('  FUTURE', e[3], e[7], e[10], e[9][:40], e[0], flush=True)
    evs = [e for e in deduped
           if e[6] == 'NIFTY 200' and e[7] in ('exclude', 'include')
           and e[11] not in ('superseded', 'duplicate', 'void_covid')
           and e[3] and e[10] and str(e[3]) <= ANCHOR_DATE]
    evs.sort(key=lambda e: (str(e[3]), str(e[1]), e[0], e[8]))
    print('chain events:', len(evs), flush=True)
    # Documented manual exit: ABIRLANUVO delisted Jul-2017 (trading suspended
    # w.e.f. 2017-07-05 per NSE circular CML35172 dtd 2017-07-04). No IISL
    # exclusion PR exists anywhere in the 228-file press-release archive
    # (verified by full-text search for NUVO/ABIRLANUVO). A delisted stock
    # cannot be an index member, so the interval closes at suspension;
    # flagged explicitly rather than silently extended.
    evs.append(['MANUAL:CML35172', '2017-07-04', 'nse_circular', '2017-07-05',
                'delisting_suspension', '', 'NIFTY 200', 'exclude', 0,
                'Aditya Birla Nuvo Ltd.', 'ABIRLANUVO', 'manual_delisting'])
    evs.sort(key=lambda e: (str(e[3]), str(e[1]), e[0], e[8]))
    print('chain events (with manual delisting exit):', len(evs), flush=True)
    # the manual exit is part of the official record: persist it in events
    deduped.append(['MANUAL:CML35172', '2017-07-04', 'nse_circular',
                    '2017-07-05', 'delisting_suspension', '', 'NIFTY 200',
                    'exclude', 0, 'Aditya Birla Nuvo Ltd.', 'ABIRLANUVO',
                    'manual_delisting'])
    con.executemany('insert into n200_events values (?,?,?,?,?,?,?,?,?,?,?,?)',
                    [deduped[-1]])

    # backward walk from today on canonical (rename-merged) keys
    state = set(canon(s) for s in anchor)
    breaks = []
    by_date = {}
    for e in evs:
        by_date.setdefault(str(e[3]), []).append(e)
    for d in sorted(by_date, reverse=True):
        for e in reversed(by_date[d]):
            sym = canon(e[10])
            if e[7] == 'include':
                if sym not in state:
                    breaks.append((d, 'reverse-include-absent', sym,
                                   e[9], e[0]))
                else:
                    state.discard(sym)
            else:
                if sym in state:
                    breaks.append((d, 'reverse-exclude-present', sym,
                                   e[9], e[0]))
                else:
                    state.add(sym)
    n_backward = len(breaks)
    print('backward breaks:', n_backward, flush=True)
    for b in breaks[:40]:
        print('  BREAK', b, flush=True)

    # forward replay from earliest state
    fwd = set(state)
    canon_intervals, open_from = [], {}
    for s in sorted(state):
        open_from[s] = LAUNCH_DATE
    for d in sorted(by_date):
        for e in by_date[d]:
            sym = canon(e[10])
            if e[7] == 'include':
                if sym in fwd:
                    breaks.append((d, 'forward-include-present', sym,
                                   e[9], e[0]))
                else:
                    fwd.add(sym)
                    open_from[sym] = d
            else:
                if sym not in fwd:
                    breaks.append((d, 'forward-exclude-absent', sym,
                                   e[9], e[0]))
                else:
                    fwd.discard(sym)
                    canon_intervals.append((sym, open_from.pop(sym), d))
    for s in sorted(fwd):
        canon_intervals.append((s, open_from[s], None))
    # per-date member counts from the event flow (renames don't move these).
    # The launch state is the first entry: it is a member count like any other,
    # and leaving it out meant LAUNCH_DATE -> the first event date was the one
    # span the count gate never evaluated.
    counts, run = [(LAUNCH_DATE, len(state))], len(state)
    for d in sorted(by_date):
        day = by_date[d]
        run += sum(1 for e in day if e[7] == 'include') - \
            sum(1 for e in day if e[7] == 'exclude')
        counts.append((d, run))
    bad = [(d, n) for d, n in counts if n != 200]
    print('forward count violations (!=200):', len(bad), flush=True)
    for d, n in bad[:30]:
        print('  COUNT', d, n, flush=True)
    print('launch-era members:', len(state), flush=True)
    # Terminal check: the forward-open set must equal the anchor exactly.
    # This is an IDENTITY, not evidence. The forward replay is the exact
    # inverse composition of the backward walk over the same ordered event
    # list, so whenever backward_breaks == 0 it must return the anchor —
    # delete an entire press release and it still passes, because the launch
    # state simply shifts to absorb it. Keep it as a self-consistency assertion
    # on the two walks; for evidence that the event stream is complete, see
    # union_gate().
    anchor_canon = set(canon(s) for s in anchor)
    terminal_extra = sorted(fwd - anchor_canon)
    terminal_missing = sorted(anchor_canon - fwd)
    print('terminal EXTRA (in walk, not anchor):', len(terminal_extra),
          terminal_extra[:20], flush=True)
    print('terminal MISSING (in anchor, not walk):', len(terminal_missing),
          terminal_missing[:20], flush=True)
    # era-correct labels: split canonical intervals at rename dates
    intervals = []
    for sym, vf, vt in canon_intervals:
        for lab, bgn, end in era_chain(sym, rename_dates):
            lo = vf if bgn is None or vf >= bgn else bgn
            if vt is None:
                hi = end
            elif end is None:
                hi = vt
            else:
                hi = min(vt, end)
            if hi is None or lo < hi:
                intervals.append((lab, lo, hi))

    con.execute(
        'create table n200_membership (symbol VARCHAR, company VARCHAR, '
        'valid_from DATE, valid_to DATE)')
    names = {}
    for e in evs:
        names.setdefault(e[10], e[9])
    names.update(anchor)
    con.executemany(
        'insert into n200_membership values (?,?,?,?)',
        [(s, names.get(s, ''), vf, vt) for s, vf, vt in intervals])
    con.execute(
        'create table n200_audit (check_name VARCHAR, detail VARCHAR)')
    audit = [('anchor_count', str(len(anchor))),
             ('chain_events', str(len(evs))),
             ('backward_breaks', str(n_backward)),
             ('forward_breaks', str(len(breaks) - n_backward)),
             ('forward_violations', str(len(bad))),
             ('launch_count', str(len(state))),
             ('terminal_extra', '|'.join(terminal_extra)),
             ('terminal_missing', '|'.join(terminal_missing)),
             ('terminal_is_identity',
              'yes - inverse of the backward walk when backward_breaks=0; '
              'carries no information about source completeness, see '
              'union_gate_*'),
             ('intervals', str(len(intervals)))]
    for d, k, s, c, f in breaks:
        audit.append(('break', f'{d}|{k}|{s}|{c}|{f}'))
    for d, n in bad:
        audit.append(('count', f'{d}|{n}'))
    con.executemany('insert into n200_audit values (?,?)', audit)
    print('intervals:', len(intervals), flush=True)
    con.executemany('insert into n200_audit values (?,?)',
                    union_gate(con, deduped, canon))
    con.executemany('insert into n200_audit values (?,?)',
                    pre_listing_gate(con))


if __name__ == '__main__':
    main()
