import os
import re
from urllib.parse import urlparse
import pandas as pd
from typing import Tuple

try:
    from tavily import TavilyClient
except Exception:
    TavilyClient = None


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace('www.', '')
    except Exception:
        return ''


def _company_from_title(title: str, url: str) -> str:
    title = (title or '').strip()
    for sep in [' | ', ' - ', ' — ', ' – ', ': ']:
        if sep in title:
            title = title.split(sep)[0].strip()
            break
    if 2 <= len(title) <= 80:
        return title
    dom = _domain(url).split('.')[0]
    return dom.replace('-', ' ').title() if dom else 'Unknown'


def _extract_leadership_from_snippet(text: str) -> Tuple[str, str]:
    """Extract public leadership mentions only if explicitly stated in public evidence.
    Never fabricates missing information. Returns ('', '') if unmentioned."""
    if not text:
        return '', ''

    m = re.search(r'\b(?:founded by|co-founded by|led by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', text)
    if m:
        candidate = m.group(1).strip()
        if candidate.lower() not in {'the company', 'our team', 'industry leaders'}:
            return candidate, 'Founder'

    m = re.search(r'\b(CEO|CTO|COO|Managing Director|Director|VP Engineering)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', text)
    if m:
        role = m.group(1).strip()
        candidate = m.group(2).strip()
        if candidate.lower() not in {'the company', 'our team'}:
            return candidate, role

    m = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}),?\s+(?:is the\s+)?(Founder|Co-Founder|CEO|CTO|Managing Director|Director)\b', text)
    if m:
        candidate = m.group(1).strip()
        role = m.group(2).strip()
        return candidate, role

    return '', ''


def run_web_research(
    query: str,
    max_results: int = 15,
    api_key: str | None = None,
    target_industry: str = "",
    target_location: str = "",
    target_company_type: str = ""
) -> pd.DataFrame:
    """Run live web research with Tavily against public business sources.
    Extracts structured company fields without fabricating missing information."""
    api_key = (api_key or os.getenv('TAVILY_API_KEY') or '').strip()
    if not api_key:
        raise ValueError('TAVILY_API_KEY is required for live web research.')
    if TavilyClient is None:
        raise RuntimeError('tavily-python is not installed.')

    client = TavilyClient(api_key=api_key)
    response = client.search(
        query=query,
        search_depth='advanced',
        max_results=max_results,
        include_answer=False
    )

    columns = [
        'Data Source',
        'Company Name',
        'Industry',
        'Location',
        'Website',
        'LinkedIn URL',
        'Company Description',
        'Decision Maker',
        'Decision Maker Role',
        'Source URL',
        'Research Summary',
        # Aliases
        'Company',
        'LinkedIn',
        'Key Person',
        'Role',
        'Summary',
        'Source',
        'Source Domain',
        'Search Score'
    ]

    rows = []
    for item in response.get('results', []):
        url = item.get('url', '')
        content = re.sub(r'\s+', ' ', item.get('content', '') or '').strip()
        title = item.get('title', '') or ''
        raw_score = item.get('score')
        score_val = float(raw_score) if raw_score is not None else 0.0

        company_name = _company_from_title(title, url)
        domain_name = _domain(url)

        linkedin_url = url if 'linkedin.com' in url.lower() else ''
        if not linkedin_url and 'linkedin.com' in content.lower():
            lm = re.search(r'https?://[a-z]{2,3}\.linkedin\.com/(?:company|in)/[A-Za-z0-9_-]+', content)
            if lm:
                linkedin_url = lm.group(0)

        website = '' if 'linkedin.com' in url.lower() else url
        person, role = _extract_leadership_from_snippet(content)

        loc = target_location if target_location and target_location.lower() in content.lower() else ''
        ind = target_industry if target_industry and target_industry.lower() in content.lower() else ''
        description = content[:400] if content else ''
        summary = content[:700] if content else ''

        rows.append({
            'Data Source': 'Live Web Research',
            'Company Name': company_name,
            'Industry': ind,
            'Location': loc,
            'Website': website,
            'LinkedIn URL': linkedin_url,
            'Company Description': description,
            'Decision Maker': person,
            'Decision Maker Role': role,
            'Source URL': url,
            'Research Summary': summary,
            'Company': company_name,
            'LinkedIn': linkedin_url,
            'Key Person': person,
            'Role': role,
            'Summary': summary,
            'Source': url,
            'Source Domain': domain_name,
            'Search Score': round(score_val * 100, 1),
        })

    return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(columns=columns)


def demo_dataset() -> pd.DataFrame:
    """Pre-validated 25-record curated B2B dataset clearly labeled as [DEMO DATA].
    Spans multiple verticals, locations, data completeness levels, and deliberate duplicate records
    to thoroughly demonstrate data cleaning, deduplication, scoring, and multi-sheet exports."""
    raw_records = [
        # 1. AI - Mumbai (Complete)
        ('NovaByte AI', 'Artificial Intelligence', 'Mumbai, Maharashtra', 'https://novabyte.ai', 'https://linkedin.com/company/novabyte-ai', 'Enterprise machine learning workflows and automated business intelligence systems for SMEs.', 'Aarav Shah', 'Founder', 92.0),
        # 2. FinTech - Navi Mumbai (No LinkedIn)
        ('FinEdge Labs', 'FinTech', 'Navi Mumbai, Maharashtra', 'https://finedgelabs.io', '', 'Builds financial workflow software, automated reconciliation, and compliance reporting engines.', 'Riya Mehta', 'CTO', 85.0),
        # 3. SaaS - Pune (No Decision Maker)
        ('CloudMosaic', 'B2B SaaS', 'Pune, Maharashtra', 'https://cloudmosaic.app', 'https://linkedin.com/company/cloudmosaic', 'Cloud productivity and asynchronous team communication software designed for distributed engineering teams.', '', '', 78.0),
        # 4. Market Research - Mumbai (Complete)
        ('MarketPulse Systems', 'Market Research', 'Mumbai, Maharashtra', 'https://marketpulse.co', 'https://linkedin.com/company/marketpulse-systems', 'Strategic market intelligence, buyer intent telemetry, and syndicated B2B survey data.', 'Kabir Rao', 'Director', 80.0),
        # 5. Data Analytics - Navi Mumbai (No Decision Maker)
        ('DataOrbit Technologies', 'Data Analytics', 'Navi Mumbai, Maharashtra', 'https://dataorbit.io', 'https://linkedin.com/company/dataorbit', 'Data engineering consultancy specializing in automated lakehouse architecture and predictive KPI dashboards.', '', '', 88.0),
        # 6. HealthTech - Bengaluru (Complete)
        ('HealthBridge Informatics', 'HealthTech', 'Bengaluru, Karnataka', 'https://healthbridge.in', 'https://linkedin.com/company/healthbridge-informatics', 'Clinical data interoperability platform and electronic medical records workflow automation.', 'Dr. Ananya Sen', 'Chief Medical Officer', 94.0),
        # 7. CyberSecurity - Bengaluru (Complete)
        ('CyberShield Defense', 'CyberSecurity', 'Bengaluru, Karnataka', 'https://cybershield.tech', 'https://linkedin.com/company/cybershield-defense', 'Automated cloud security posture management and penetration testing suite for enterprise SaaS.', 'Vikram Malhotra', 'Head of Security', 90.0),
        # 8. Supply Chain - Chennai (Complete)
        ('LogiChain Global', 'Supply Chain Tech', 'Chennai, Tamil Nadu', 'https://logichain.net', 'https://linkedin.com/company/logichain-global', 'Real-time multi-modal freight visibility and warehouse optimization platform for exporters.', 'Karthik Raman', 'VP Logistics', 82.0),
        # 9. EdTech - Delhi NCR (No LinkedIn)
        ('EdVantage Learning', 'EdTech', 'Delhi NCR, Gurgaon', 'https://edvantage.edu.in', '', 'AI-driven upskilling and corporate learning management systems for workforce reskilling.', 'Meera Joshi', 'Co-Founder', 79.0),
        # 10. HR Tech - Hyderabad (Complete)
        ('TalentPulse AI', 'Artificial Intelligence', 'Hyderabad, Telangana', 'https://talentpulse.ai', 'https://linkedin.com/company/talentpulse-ai', 'Autonomous recruiting intelligence that parses technical resumes and matches candidate profiles.', 'Rohan Das', 'CEO', 87.0),
        # 11. CleanTech - Pune (No Decision Maker)
        ('GreenGrid Energy', 'CleanTech', 'Pune, Maharashtra', 'https://greengrid.energy', 'https://linkedin.com/company/greengrid-energy', 'Industrial smart meter telemetry and carbon accounting software for sustainable manufacturing.', '', '', 76.0),
        # 12. Retail Analytics - Mumbai (Complete)
        ('RetailSense Analytics', 'Data Analytics', 'Mumbai, Maharashtra', 'https://retailsense.ai', 'https://linkedin.com/company/retailsense', 'Computer vision and foot-traffic analytics software for brick-and-mortar retail operators.', 'Pooja Singhania', 'Founder', 86.0),
        # 13. DevTools - Bengaluru (Complete)
        ('DevSphere Technologies', 'B2B SaaS', 'Bengaluru, Karnataka', 'https://devsphere.dev', 'https://linkedin.com/company/devsphere-tech', 'Continuous integration telemetry and developer velocity optimization dashboards for engineering leads.', 'Sameer Kulkarni', 'VP Engineering', 91.0),
        # 14. Procurement - Chennai (No Decision Maker, No LinkedIn)
        ('AutoProcure Systems', 'B2B SaaS', 'Chennai, Tamil Nadu', 'https://autoprocure.biz', '', 'Vendor lifecycle management and automated purchase-order approval workflows for enterprises.', '', '', 72.0),
        # 15. RegTech - Singapore (Complete)
        ('SecureVault Compliance', 'FinTech', 'Singapore', 'https://securevault.sg', 'https://linkedin.com/company/securevault-compliance', 'Anti-money laundering screening and regulatory compliance reporting software for Southeast Asia.', 'Tan Wei Ling', 'Managing Director', 89.0),
        # 16. Logistics - Hyderabad (Complete)
        ('OmniFlow Logistics', 'Supply Chain Tech', 'Hyderabad, Telangana', 'https://omniflow.io', 'https://linkedin.com/company/omniflow-logistics', 'Predictive fleet route optimization and last-mile delivery tracking software.', 'Arjun Nambiar', 'COO', 84.0),
        # 17. BioTech - Bengaluru (No Decision Maker)
        ('BioNexus Research', 'HealthTech', 'Bengaluru, Karnataka', 'https://bionexus.bio', 'https://linkedin.com/company/bionexus-research', 'Bioinformatics pipelines and genomic sequence indexing algorithms for pharmaceutical labs.', '', '', 81.0),
        # 18. AdTech - Delhi NCR (Complete)
        ('CloudSurge Media', 'B2B SaaS', 'Delhi NCR, Noida', 'https://cloudsurge.agency', 'https://linkedin.com/company/cloudsurge-media', 'Programmatic B2B account-based advertising engine with real-time buyer intent telemetry.', 'Neha Kapoor', 'CEO', 83.0),
        # 19. DeepTech - San Francisco (Complete)
        ('TensorLogic AI', 'Artificial Intelligence', 'San Francisco, CA', 'https://tensorlogic.ai', 'https://linkedin.com/company/tensorlogic-ai', 'Distributed model training infrastructure and parameter quantization tools for large language models.', 'Alex Rivera', 'Lead AI Scientist', 95.0),
        # 20. Enterprise BI - London (Complete)
        ('ApexMetrics Enterprise', 'Data Analytics', 'London, UK', 'https://apexmetrics.co.uk', 'https://linkedin.com/company/apexmetrics', 'Executive business intelligence dashboards and cross-departmental KPI benchmarking software.', 'James Sterling', 'Managing Partner', 88.0),
        # 21. GenAI - Bengaluru (Complete)
        ('Synthetix Labs', 'Artificial Intelligence', 'Bengaluru, Karnataka', 'https://synthetix.ai', 'https://linkedin.com/company/synthetix-labs', 'Enterprise synthetic data generation and privacy-preserving model fine-tuning platform.', 'Siddharth Verma', 'Founder', 93.0),
        # 22. Freight - Mumbai (No Decision Maker)
        ('FreightVelocity', 'Supply Chain Tech', 'Mumbai, Maharashtra', 'https://freightvelocity.in', 'https://linkedin.com/company/freightvelocity', 'Digital customs clearing and freight forwarding documentation workflows for ocean cargo.', '', '', 77.0),
        # --- DELIBERATE DUPLICATE RECORDS FOR SANITIZATION TESTING ---
        # 23. Duplicate of #1: Exact same name and domain
        ('NovaByte AI', 'Artificial Intelligence', 'Mumbai, Maharashtra', 'https://novabyte.ai', 'https://linkedin.com/company/novabyte-ai', 'Duplicate demo record for testing pipeline deduplication and data sanitization algorithms.', 'Aarav Shah', 'Founder', 91.0),
        # 24. Duplicate of #5: Tests corporate suffix canonical matching (DataOrbit Technologies Inc. vs DataOrbit Technologies)
        ('DataOrbit Technologies Inc.', 'Data Analytics', 'Navi Mumbai, Maharashtra', 'https://dataorbit.io', 'https://linkedin.com/company/dataorbit', 'Duplicate test entry testing corporate suffix stripping (Inc.) in deduplication.', '', '', 87.0),
        # 25. Duplicate of #7: Exact same name and domain
        ('CyberShield Defense', 'CyberSecurity', 'Bengaluru, Karnataka', 'https://cybershield.tech', '', 'Duplicate test entry for verifying duplicate company pruning.', 'Vikram Malhotra', 'Head of Security', 89.0),
    ]

    rows = []
    for (name, ind, loc, web, lk, desc, leader, role, score) in raw_records:
        domain = _domain(web)
        slug = name.lower().replace(' ', '-').replace('.', '')
        source_url = f"https://b2b-archive.org/demo-eval/{slug}"

        rows.append({
            'Data Source': '[DEMO DATA]',
            'Company Name': name,
            'Industry': ind,
            'Location': loc,
            'Website': web,
            'LinkedIn URL': lk,
            'Company Description': desc,
            'Decision Maker': leader,
            'Decision Maker Role': role,
            'Source URL': source_url,
            'Research Summary': f"{name} is an active B2B commercial organization operating in {ind} based in {loc}. {desc}",
            # Aliases for backwards compatibility
            'Company': name,
            'LinkedIn': lk,
            'Key Person': leader,
            'Role': role,
            'Summary': desc,
            'Source': source_url,
            'Source Domain': domain,
            'Search Score': score
        })

    return pd.DataFrame(rows)
