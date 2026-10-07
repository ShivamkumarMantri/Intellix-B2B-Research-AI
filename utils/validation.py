import re
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import pandas as pd
from typing import Tuple, Dict, Any, List

CORE_QUALITY_FIELDS = [
    'Company Name',
    'Industry',
    'Location',
    'Website',
    'LinkedIn URL',
    'Company Description',
    'Decision Maker',
    'Decision Maker Role',
    'Source URL'
]


def _safe_str(v) -> str:
    if v is None or pd.isna(v):
        return ''
    s = str(v).strip()
    return '' if s.lower() in {'nan', 'none', 'null', 'undefined'} else s


# ---------------------------------------------------------------------------
# 1. Company Name Normalization & Deduplication Key
# ---------------------------------------------------------------------------
def normalize_company_name(name: str) -> str:
    """Clean company name by removing web title noise, excessive spaces, and formatting."""
    s = _safe_str(name)
    if not s or s.lower() == 'unknown':
        return 'Unknown'

    for sep in [' | ', ' - ', ' — ', ' – ', ': ']:
        if sep in s:
            parts = s.split(sep)
            if len(parts[0].strip()) >= 2:
                s = parts[0].strip()
                break

    s = re.sub(r'\b(Official Website|Home|Overview|Login|Portal|Careers)\b', '', s, flags=re.IGNORECASE).strip()
    s = re.sub(r'\s+', ' ', s).strip()
    return s if s else 'Unknown'


def company_dedupe_key(name: str) -> str:
    """Generate a canonical key for duplicate company detection ignoring case, symbols, and legal suffixes."""
    s = normalize_company_name(name).lower()
    s = re.sub(r'[^\w\s]', '', s)
    legal_suffixes = [
        r'\bpvt\s+ltd\b', r'\bltd\b', r'\binc\b', r'\bllc\b', r'\bcorp\b',
        r'\bcorporation\b', r'\btechnologies\b', r'\btechnology\b', r'\bsolutions\b',
        r'\blabs\b', r'\bsystems\b', r'\bgroup\b', r'\bco\b'
    ]
    for suf in legal_suffixes:
        s = re.sub(suf, '', s).strip()
    s = re.sub(r'\s+', ' ', s).strip()
    return s if s else normalize_company_name(name).lower()


# ---------------------------------------------------------------------------
# 2. URL Normalization & Validation
# ---------------------------------------------------------------------------
def is_valid_url(v: str) -> bool:
    """Strictly validate whether a URL has a valid scheme, netloc, and plausible TLD."""
    s = _safe_str(v)
    if not s:
        return False
    try:
        p = urlparse(s)
        if p.scheme not in {'http', 'https'}:
            return False
        netloc = p.netloc.strip()
        if not netloc or '.' not in netloc:
            return False
        if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?::\d+)?$', netloc):
            return False
        return True
    except Exception:
        return False


def normalize_url(v: str) -> str:
    """Normalize website URL: add scheme if missing, lowercase domain, strip tracking query params, remove trailing slashes."""
    s = _safe_str(v)
    if not re.match(r'^[a-zA-Z]+://', s):
        candidate = 'https://' + s
        if not is_valid_url(candidate):
            return ''
        s = candidate
    elif not is_valid_url(s):
        return ''

    try:
        p = urlparse(s)
        if not p.netloc:
            return s

        netloc = p.netloc.lower()
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        if netloc.endswith(':80') and p.scheme == 'http':
            netloc = netloc[:-3]
        elif netloc.endswith(':443') and p.scheme == 'https':
            netloc = netloc[:-4]

        filtered_query = []
        if p.query:
            for k, val in parse_qsl(p.query):
                if not re.match(r'^(utm_|ref|gclid|fbclid|source|trk)', k, re.IGNORECASE):
                    filtered_query.append((k, val))

        new_query = urlencode(filtered_query)
        path = p.path.rstrip('/') if p.path != '/' else ''

        normalized = urlunparse((p.scheme, netloc, path, '', new_query, ''))
        return normalized
    except Exception:
        return s.rstrip('/')


# ---------------------------------------------------------------------------
# 3. LinkedIn URL Validation
# ---------------------------------------------------------------------------
def validate_linkedin_url(v: str) -> Tuple[bool, str]:
    """Validate and normalize LinkedIn company or profile URL. Returns (is_valid, normalized_url)."""
    s = _safe_str(v)
    if not s:
        return False, ''

    if not re.match(r'^[a-zA-Z]+://', s):
        s = 'https://' + s

    try:
        p = urlparse(s)
        domain = p.netloc.lower()
        if 'linkedin.com' not in domain:
            return False, ''

        clean_path = p.path.rstrip('/')
        if not re.match(r'^/(?:company|in|school)/[A-Za-z0-9_.-]+', clean_path):
            return False, ''

        normalized = f"https://linkedin.com{clean_path}"
        return True, normalized
    except Exception:
        return False, ''


# ---------------------------------------------------------------------------
# 4. Duplicate Company Detection & Cleaning Pipeline
# ---------------------------------------------------------------------------
def clean_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Sanitize records, normalize names & URLs, validate LinkedIn links, and resolve duplicates."""
    if df.empty:
        return df.copy(), {
            'total_raw_records': 0,
            'valid_records': 0,
            'duplicates_detected': 0,
            'duplicates_removed': 0,
            'incomplete_records': 0,
            'invalid_urls': 0,
            'average_confidence': 0.0,
            'data_completeness_pct': 0.0,
            'duplicates_details': []
        }

    raw_total = len(df)
    out = df.copy()

    for col in out.columns:
        if out[col].dtype == 'object':
            out[col] = out[col].apply(lambda x: re.sub(r'\s+', ' ', str(x)).strip() if pd.notna(x) else '')

    if 'Company Name' not in out.columns and 'Company' in out.columns:
        out['Company Name'] = out['Company']
    if 'Source URL' not in out.columns and 'Source' in out.columns:
        out['Source URL'] = out['Source']
    if 'LinkedIn URL' not in out.columns and 'LinkedIn' in out.columns:
        out['LinkedIn URL'] = out['LinkedIn']
    if 'Company Description' not in out.columns and 'Summary' in out.columns:
        out['Company Description'] = out['Summary']

    # Ensure all core fields exist to prevent KeyErrors on partial or corrupted input schemas
    for field in CORE_QUALITY_FIELDS:
        if field not in out.columns:
            out[field] = ''

    # 1. Company name normalization
    out['Company Name'] = out['Company Name'].apply(normalize_company_name)
    out['Company'] = out['Company Name']

    # 2. Website normalization and validation
    invalid_url_count = 0
    norm_websites = []
    for w in out['Website']:
        if _safe_str(w):
            if is_valid_url(w):
                norm_websites.append(normalize_url(w))
            else:
                invalid_url_count += 1
                norm_websites.append(w)
        else:
            norm_websites.append('')
    out['Website'] = norm_websites

    # 3. LinkedIn URL validation
    norm_linkedins = []
    for lk in out['LinkedIn URL']:
        if _safe_str(lk):
            is_valid, n_url = validate_linkedin_url(lk)
            if is_valid:
                norm_linkedins.append(n_url)
            else:
                invalid_url_count += 1
                norm_linkedins.append(lk)
        else:
            norm_linkedins.append('')
    out['LinkedIn URL'] = norm_linkedins
    out['LinkedIn'] = out['LinkedIn URL']

    # 4. Source URL normalization
    norm_sources = []
    for src in out['Source URL']:
        if _safe_str(src):
            if is_valid_url(src):
                norm_sources.append(normalize_url(src))
            else:
                invalid_url_count += 1
                norm_sources.append(src)
        else:
            norm_sources.append('')
    out['Source URL'] = norm_sources
    out['Source'] = out['Source URL']

    # 5. Duplicate Detection & Intelligent Deduplication
    out['_company_key'] = out['Company Name'].apply(company_dedupe_key)
    out['_domain_key'] = out['Website'].apply(lambda w: urlparse(w).netloc.replace('www.', '') if is_valid_url(w) else '')

    def record_richness(r: pd.Series) -> int:
        score = 0
        for f in CORE_QUALITY_FIELDS:
            if _safe_str(r.get(f)):
                score += 1
        return score

    out['_richness'] = out.apply(record_richness, axis=1)
    out = out.sort_values(by=['_richness'], ascending=False)

    seen_companies = set()
    seen_domains = set()
    unique_indices = []
    duplicate_records_log = []

    generic_domains = {'example.com', 'linkedin.com', 'twitter.com', 'facebook.com', 'instagram.com', 'github.com'}
    for idx, row in out.iterrows():
        ckey = row['_company_key']
        dkey = row['_domain_key']

        is_dup = False
        dup_reason = []

        if ckey and ckey != 'unknown' and ckey in seen_companies:
            is_dup = True
            dup_reason.append(f"Matching entity name: '{row['Company Name']}'")
        elif dkey and dkey not in generic_domains and dkey in seen_domains:
            is_dup = True
            dup_reason.append(f"Matching web domain: '{dkey}'")

        if is_dup:
            duplicate_records_log.append({
                'Company Name': row['Company Name'],
                'Reason': '; '.join(dup_reason),
                'Website': row.get('Website', '')
            })
        else:
            if ckey and ckey != 'unknown':
                seen_companies.add(ckey)
            if dkey and dkey not in generic_domains:
                seen_domains.add(dkey)
            unique_indices.append(idx)

    cleaned_df = out.loc[unique_indices].copy()
    cleaned_df = cleaned_df.drop(columns=['_company_key', '_domain_key', '_richness'], errors='ignore')
    cleaned_df = cleaned_df.reset_index(drop=True)

    duplicates_detected = raw_total - len(cleaned_df)

    stats = {
        'total_raw_records': raw_total,
        'valid_records': len(cleaned_df),
        'duplicates_detected': duplicates_detected,
        'duplicates_removed': duplicates_detected,
        'invalid_urls': invalid_url_count,
        'duplicates_details': duplicate_records_log
    }

    return cleaned_df, stats


# ---------------------------------------------------------------------------
# 5. Confidence Scoring & Data Completeness Percentage
# ---------------------------------------------------------------------------
def calculate_completeness(r: pd.Series) -> float:
    """Calculate data completeness percentage across core quality fields."""
    if not len(CORE_QUALITY_FIELDS):
        return 0.0
    populated_count = sum(1 for f in CORE_QUALITY_FIELDS if bool(_safe_str(r.get(f))))
    return round((populated_count / len(CORE_QUALITY_FIELDS)) * 100, 1)


def add_validation_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Evaluate transparent confidence score and data completeness % for each record."""
    if df.empty:
        return df.copy()

    out = df.copy()
    scores, levels, issues, completeness_pcts = [], [], [], []

    for _, r in out.iterrows():
        score = 0
        missing_fields = []
        verified_fields = []

        company = _safe_str(r.get('Company Name', r.get('Company', '')))
        website = _safe_str(r.get('Website', ''))
        linkedin = _safe_str(r.get('LinkedIn URL', r.get('LinkedIn', '')))
        description = _safe_str(r.get('Company Description', r.get('Summary', '')))
        source = _safe_str(r.get('Source URL', r.get('Source', '')))
        person = _safe_str(r.get('Decision Maker', r.get('Key Person', '')))
        role = _safe_str(r.get('Decision Maker Role', r.get('Role', '')))

        # 1. Company Name (+15)
        if company and company.lower() != 'unknown':
            score += 15
            verified_fields.append('Name')
        else:
            missing_fields.append('Company name unverified')

        # 2. Website (+20)
        if is_valid_url(website):
            score += 20
            verified_fields.append('Website')
        else:
            missing_fields.append('Website missing/invalid')

        # 3. Source URL (+20)
        if is_valid_url(source):
            score += 20
            verified_fields.append('Source Citation')
        else:
            missing_fields.append('Source citation missing')

        # 4. Description (+15)
        if description:
            score += 15
            verified_fields.append('Description')
        else:
            missing_fields.append('Description missing')

        # 5. LinkedIn (+15)
        is_lk, _ = validate_linkedin_url(linkedin)
        if is_lk:
            score += 15
            verified_fields.append('LinkedIn')
        else:
            missing_fields.append('LinkedIn profile unavailable')

        # 6. Public Decision Maker (+15)
        if person and role:
            score += 15
            verified_fields.append(f"Leader ({role})")
        elif person:
            score += 10
            verified_fields.append('Leader (Name only)')
            missing_fields.append('Leader role unspecified')
        else:
            missing_fields.append('Decision maker unavailable')

        final_score = min(score, 100)
        scores.append(final_score)
        levels.append('High' if final_score >= 80 else 'Medium' if final_score >= 60 else 'Low')
        issues.append('; '.join(missing_fields) if missing_fields else 'All public attributes verified')

        completeness = calculate_completeness(r)
        completeness_pcts.append(completeness)

    out['Confidence Score'] = scores
    out['Validation Score'] = scores  # Alias
    out['Confidence'] = levels
    out['Validation Notes'] = issues
    out['Data Completeness %'] = completeness_pcts
    return out


# ---------------------------------------------------------------------------
# 6. Deterministic, Transparent 0-100 Lead Scoring System
# ---------------------------------------------------------------------------
# Transparent 7-Factor Rubric Weights (Sums to exactly 100 pts)
LEAD_SCORE_WEIGHTS = {
    'industry_relevance': 25,
    'location_match': 20,
    'decision_maker': 15,
    'data_completeness': 15,
    'website_availability': 10,
    'research_confidence': 10,
    'linkedin_availability': 5,
}


def add_lead_score(
    df: pd.DataFrame,
    target_industry: str = '',
    target_location: str = '',
    keywords: str = '',
    target_company_type: str = ''
) -> pd.DataFrame:
    """Calculate deterministic, reproducible 0-100 Lead Score across 7 objective factors:
    1. Industry Relevance (Max 25 pts)
    2. Location Match (Max 20 pts)
    3. Decision-Maker Availability (Max 15 pts)
    4. Company Information Completeness (Max 15 pts)
    5. Website Availability (Max 10 pts)
    6. Research Confidence (Max 10 pts)
    7. LinkedIn Availability (Max 5 pts)

    Assigns Lead Category: High Potential (≥80), Medium Potential (60-79), Low Potential (<60)
    and generates a concise, deterministic explanation."""
    if df.empty:
        return df.copy()

    out = df.copy()
    scores, categories, explanations, factor_breakdowns = [], [], [], []

    ti = target_industry.lower().strip()
    tl = target_location.lower().strip()

    for _, r in out.iterrows():
        comp_name = _safe_str(r.get('Company Name', r.get('Company', '')))
        ind = _safe_str(r.get('Industry', '')).lower()
        loc = _safe_str(r.get('Location', '')).lower()
        desc = _safe_str(r.get('Company Description', '')).lower()
        summary = _safe_str(r.get('Research Summary', r.get('Summary', ''))).lower()
        web = _safe_str(r.get('Website', ''))
        lk = _safe_str(r.get('LinkedIn URL', r.get('LinkedIn', '')))
        person = _safe_str(r.get('Decision Maker', r.get('Key Person', '')))
        role = _safe_str(r.get('Decision Maker Role', r.get('Role', '')))

        text_corpus = f"{comp_name.lower()} {ind} {loc} {desc} {summary}"

        # -------------------------------------------------
        # Factor 1: Industry Relevance (Max 25 pts)
        # -------------------------------------------------
        f_industry = 0
        f_industry_note = ""
        if not ti:
            f_industry = 15
            f_industry_note = "Industry scope open (+15)"
        elif ti in ind or ti in text_corpus:
            f_industry = 25
            f_industry_note = f"Direct industry match ({target_industry}) (+25)"
        elif any(token in text_corpus for token in ti.split() if len(token) > 2):
            f_industry = 15
            f_industry_note = "Related domain overlap (+15)"
        else:
            f_industry = 5
            f_industry_note = "Broad commercial presence (+5)"

        # -------------------------------------------------
        # Factor 2: Location Match (Max 20 pts)
        # -------------------------------------------------
        f_location = 0
        f_location_note = ""
        if not tl:
            f_location = 15
            f_location_note = "Location scope open (+15)"
        elif tl in loc or tl in text_corpus:
            f_location = 20
            f_location_note = f"Target hub match ({target_location}) (+20)"
        elif any(part.strip() in text_corpus for part in tl.split(',') if len(part.strip()) > 2):
            f_location = 12
            f_location_note = "Regional geography fit (+12)"
        else:
            f_location = 0
            f_location_note = "Location unverified (+0)"

        # -------------------------------------------------
        # Factor 3: Decision-Maker Availability (Max 15 pts)
        # -------------------------------------------------
        f_leader = 0
        f_leader_note = ""
        if person and role:
            f_leader = 15
            f_leader_note = f"Leader found ({person}, {role}) (+15)"
        elif person:
            f_leader = 8
            f_leader_note = f"Contact name identified ({person}) (+8)"
        else:
            f_leader = 0
            f_leader_note = "Decision maker unavailable (+0)"

        # -------------------------------------------------
        # Factor 4: Company Information Completeness (Max 15 pts)
        # -------------------------------------------------
        comp_pct = float(r.get('Data Completeness %', 0) or 0)
        f_completeness = 0
        f_completeness_note = ""
        if comp_pct >= 88.0:
            f_completeness = 15
            f_completeness_note = f"High completeness ({int(comp_pct)}%) (+15)"
        elif comp_pct >= 70.0:
            f_completeness = 10
            f_completeness_note = f"Good completeness ({int(comp_pct)}%) (+10)"
        elif comp_pct >= 50.0:
            f_completeness = 6
            f_completeness_note = f"Moderate completeness ({int(comp_pct)}%) (+6)"
        else:
            f_completeness = 2
            f_completeness_note = f"Low completeness ({int(comp_pct)}%) (+2)"

        # -------------------------------------------------
        # Factor 5: Website Availability (Max 10 pts)
        # -------------------------------------------------
        f_web = 0
        f_web_note = ""
        if is_valid_url(web):
            f_web = 10
            f_web_note = "Verified website domain (+10)"
        else:
            f_web = 0
            f_web_note = "Website unavailable (+0)"

        # -------------------------------------------------
        # Factor 6: Research Confidence (Max 10 pts)
        # -------------------------------------------------
        conf_score = float(r.get('Confidence Score', r.get('Validation Score', 0)) or 0)
        f_confidence = 0
        f_confidence_note = ""
        if conf_score >= 80.0:
            f_confidence = 10
            f_confidence_note = f"High confidence ({int(conf_score)}%) (+10)"
        elif conf_score >= 60.0:
            f_confidence = 6
            f_confidence_note = f"Medium confidence ({int(conf_score)}%) (+6)"
        else:
            f_confidence = 2
            f_confidence_note = f"Low confidence ({int(conf_score)}%) (+2)"

        # -------------------------------------------------
        # Factor 7: LinkedIn Availability (Max 5 pts)
        # -------------------------------------------------
        f_linkedin = 0
        f_linkedin_note = ""
        is_lk, _ = validate_linkedin_url(lk)
        if is_lk:
            f_linkedin = 5
            f_linkedin_note = "Verified LinkedIn link (+5)"
        else:
            f_linkedin = 0
            f_linkedin_note = "LinkedIn unavailable (+0)"

        # -------------------------------------------------
        # Total Lead Score (0 - 100)
        # -------------------------------------------------
        total_score = f_industry + f_location + f_leader + f_completeness + f_web + f_confidence + f_linkedin
        total_score = min(max(int(total_score), 0), 100)

        # Lead Category Assignment
        if total_score >= 80:
            cat = "High Potential"
        elif total_score >= 60:
            cat = "Medium Potential"
        else:
            cat = "Low Potential"

        # Deterministic Short Explanation
        explanation_parts = [
            f_industry_note,
            f_location_note,
            f_leader_note,
            f_completeness_note
        ]
        explanation = f"{cat} ({total_score}/100): " + "; ".join(explanation_parts) + "."

        breakdown = {
            'Industry Relevance': f_industry,
            'Location Match': f_location,
            'Decision Maker': f_leader,
            'Data Completeness': f_completeness,
            'Website Availability': f_web,
            'Research Confidence': f_confidence,
            'LinkedIn Availability': f_linkedin
        }

        scores.append(total_score)
        categories.append(cat)
        explanations.append(explanation)
        factor_breakdowns.append(breakdown)

    out['Lead Score'] = scores
    out['Lead Category'] = categories
    out['Lead Score Reason'] = explanations
    out['Score Factors'] = factor_breakdowns
    return out
