import os
import sys
import unittest
import pandas as pd
from datetime import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath("."))

from utils.research import demo_dataset, run_web_research, _domain, _company_from_title, _extract_leadership_from_snippet
from utils.validation import (
    clean_dataframe,
    add_validation_scores,
    add_lead_score,
    normalize_company_name,
    company_dedupe_key,
    normalize_url,
    validate_linkedin_url,
    calculate_completeness,
    CORE_QUALITY_FIELDS,
    LEAD_SCORE_WEIGHTS
)
from utils.exporter import to_excel_bytes
from utils.ai import (
    generate_company_summary,
    classify_industry,
    analyze_business_relevance,
    explain_lead_quality,
    extract_key_information,
    generate_research_insights,
    summarize_record,
    classify_record,
    get_llm_config,
    call_openai_compatible
)


class TestProductionReadiness(unittest.TestCase):

    def test_01_demo_dataset_structure(self):
        """Test demo dataset integrity and labeling."""
        raw = demo_dataset()
        self.assertFalse(raw.empty, "Demo dataset should not be empty")
        self.assertEqual(len(raw), 25, "Demo dataset must have exactly 25 records")
        self.assertTrue('Data Source' in raw.columns)
        self.assertTrue(all(raw['Data Source'] == '[DEMO DATA]'), "All demo records must be labeled [DEMO DATA]")
        for req in ['Company Name', 'Industry', 'Location', 'Website', 'Source URL']:
            self.assertTrue(req in raw.columns, f"Required column {req} missing in demo dataset")

    def test_02_data_cleaning_and_deduplication(self):
        """Test data cleaning, duplicate pruning, and normalization."""
        raw = demo_dataset()
        clean, stats = clean_dataframe(raw)
        self.assertEqual(stats['total_raw_records'], 25)
        self.assertEqual(stats['duplicates_detected'], 3)
        self.assertEqual(stats['duplicates_removed'], 3)
        self.assertEqual(len(clean), 22)
        self.assertTrue(all(clean['Company Name'] != ''))

        # Check normalization edge cases
        self.assertEqual(normalize_company_name("Acme Corp | Leading B2B Platform"), "Acme Corp")
        self.assertEqual(normalize_company_name("   "), "Unknown")
        self.assertEqual(normalize_company_name(None), "Unknown")

        # Dedupe key (legal suffixes like Technologies, LLC, Inc are pruned to identify true duplicates)
        self.assertEqual(company_dedupe_key("NovaByte AI Inc."), "novabyte ai")
        self.assertEqual(company_dedupe_key("DataOrbit Technologies, LLC"), "dataorbit")

        # URL normalization
        self.assertEqual(normalize_url("HTTP://Example.COM/Path/?b=2&a=1#fragment"), "http://example.com/Path?b=2&a=1")
        self.assertEqual(normalize_url("not a url"), "")
        self.assertEqual(normalize_url(""), "")

        # LinkedIn validation
        valid, lk_clean = validate_linkedin_url("https://www.linkedin.com/company/salesforce?trk=feed")
        self.assertTrue(valid)
        self.assertNotIn("trk=feed", lk_clean)

        invalid_lk, _ = validate_linkedin_url("https://twitter.com/salesforce")
        self.assertFalse(invalid_lk)

    def test_03_validation_scores_and_completeness(self):
        """Test completeness calculation and confidence scores."""
        raw = demo_dataset()
        clean, _ = clean_dataframe(raw)
        scored = add_validation_scores(clean)

        self.assertTrue('Data Completeness %' in scored.columns)
        self.assertTrue('Confidence Score' in scored.columns)
        self.assertTrue('Confidence' in scored.columns)

        for val in scored['Data Completeness %']:
            self.assertGreaterEqual(val, 0.0)
            self.assertLessEqual(val, 100.0)

        for val in scored['Confidence Score']:
            self.assertGreaterEqual(val, 0.0)
            self.assertLessEqual(val, 100.0)

        # Empty record completeness
        empty_comp = calculate_completeness(pd.Series({}))
        self.assertEqual(empty_comp, 0.0)

    def test_04_lead_scoring_reproducibility(self):
        """Test deterministic lead scoring and category assignment."""
        raw = demo_dataset()
        clean, _ = clean_dataframe(raw)
        scored = add_validation_scores(clean)
        leads = add_lead_score(
            scored,
            target_industry="Artificial Intelligence",
            target_location="Mumbai",
            keywords="automation",
            target_company_type="B2B SaaS / Product"
        )

        self.assertTrue('Lead Score' in leads.columns)
        self.assertTrue('Lead Category' in leads.columns)
        self.assertTrue('Lead Score Reason' in leads.columns)
        self.assertTrue('Score Factors' in leads.columns)

        for _, row in leads.iterrows():
            sc = row['Lead Score']
            cat = row['Lead Category']
            exp = row['Lead Score Reason']
            self.assertGreaterEqual(sc, 0)
            self.assertLessEqual(sc, 100)
            if sc >= 80:
                self.assertEqual(cat, 'High Potential')
            elif sc >= 60:
                self.assertEqual(cat, 'Medium Potential')
            else:
                self.assertEqual(cat, 'Low Potential')
            self.assertTrue(len(exp) > 0, "Lead Score explanation should not be empty")

        # Determinism test: running twice produces identical scores
        leads_second = add_lead_score(
            scored,
            target_industry="Artificial Intelligence",
            target_location="Mumbai",
            keywords="automation",
            target_company_type="B2B SaaS / Product"
        )
        self.assertTrue(leads['Lead Score'].equals(leads_second['Lead Score']))
        self.assertTrue(leads['Lead Category'].equals(leads_second['Lead Category']))

    def test_05_excel_export_and_csv_export(self):
        """Test 4-sheet Excel generation and CSV generation."""
        raw = demo_dataset()
        clean, stats = clean_dataframe(raw)
        scored = add_validation_scores(clean)
        leads = add_lead_score(scored, target_industry="Artificial Intelligence", target_location="Mumbai")

        summary = {
            'Query': 'Artificial Intelligence in Mumbai',
            'Target Industry': 'Artificial Intelligence',
            'Target Location': 'Mumbai',
            'Generated At': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Total Raw Records Ingested': stats['total_raw_records'],
            'Valid Unique Companies': len(leads),
        }

        # Excel Export
        excel_bytes = to_excel_bytes(leads, summary=summary, raw_df=raw, stats=stats)
        self.assertIsInstance(excel_bytes, bytes)
        self.assertGreater(len(excel_bytes), 5000)

        # CSV Export
        csv_bytes = leads.to_csv(index=False).encode('utf-8')
        self.assertIsInstance(csv_bytes, bytes)
        self.assertGreater(len(csv_bytes), 500)

        # Edge cases: Empty dataframe export
        empty_excel = to_excel_bytes(pd.DataFrame(), summary=summary, raw_df=pd.DataFrame(), stats={})
        self.assertIsInstance(empty_excel, bytes)

    def test_06_ai_demo_mode_fallbacks(self):
        """Test AI synthesizers in Demo Mode (when no API key is provided)."""
        record = {
            'Company Name': 'NovaByte AI',
            'Industry': 'Artificial Intelligence',
            'Location': 'Mumbai, Maharashtra',
            'Website': 'https://novabyte.ai',
            'LinkedIn URL': 'https://linkedin.com/company/novabyte-ai',
            'Company Description': 'Enterprise machine learning workflows and automated business intelligence systems.',
            'Decision Maker': 'Aarav Shah',
            'Decision Maker Role': 'Founder'
        }

        # 1. Company summary
        summary = generate_company_summary(record, api_key="")
        self.assertIn("NovaByte AI", summary)
        self.assertIn("Aarav Shah", summary)

        # 2. Industry classification
        ind_res = classify_industry(record, api_key="")
        self.assertIn('primary_industry', ind_res)
        self.assertIn('confidence', ind_res)

        # 3. Business relevance analysis
        rel_res = analyze_business_relevance(
            record,
            target_industry="Artificial Intelligence",
            target_location="Mumbai",
            keywords="automation",
            company_type="B2B SaaS / Product",
            api_key=""
        )
        self.assertIn('relevance_score', rel_res)
        self.assertIn('relevance_tier', rel_res)

        # 4. Lead quality explanation
        qual_res = explain_lead_quality(record, lead_score=88, lead_category="High Potential", api_key="")
        self.assertIn('quality_rating', qual_res)
        self.assertIn('strengths', qual_res)

        # 5. Key information extraction
        ext_res = extract_key_information(record, api_key="")
        self.assertIn('executive_leadership', ext_res)

        # 6. Research insights
        mock_leads = pd.DataFrame([record])
        mock_leads['Lead Score'] = 88
        mock_leads['Lead Category'] = 'High Potential'
        mock_leads['Data Completeness %'] = 90.0
        insights = generate_research_insights(mock_leads, api_key="")
        self.assertIn('executive_takeaway', insights)
        self.assertIn('outreach_recommendations', insights)

    def test_07_ai_error_handling_invalid_api_keys(self):
        """Test that invalid LLM API key fails gracefully without crashing the app."""
        record = {'Company Name': 'Test Corp', 'Industry': 'SaaS'}
        # Should gracefully fallback to demo synthesizer when network fails or key is invalid
        summary = generate_company_summary(record, api_key="sk-invalid-nonexistent-key-12345")
        self.assertTrue(len(summary) > 0, "Should gracefully return fallback summary on API error")

    def test_08_live_research_error_handling(self):
        """Test live web research error handling when key is missing or invalid."""
        # Missing key should raise ValueError
        with self.assertRaises(ValueError):
            run_web_research("AI companies in Mumbai", api_key="")

        # None key should raise ValueError
        with self.assertRaises(ValueError):
            run_web_research("AI companies in Mumbai", api_key=None)

    def test_09_invalid_and_empty_inputs(self):
        """Test pipeline behavior with empty or corrupted inputs."""
        empty_df = pd.DataFrame()
        clean, stats = clean_dataframe(empty_df)
        self.assertTrue(clean.empty)
        self.assertEqual(stats['total_raw_records'], 0)

        scored = add_validation_scores(clean)
        self.assertTrue(scored.empty)

        leads = add_lead_score(scored, target_industry="", target_location="")
        self.assertTrue(leads.empty)

        # Corrupted records (all nulls)
        corrupted_df = pd.DataFrame([
            {'Company Name': None, 'Website': None, 'Location': None},
            {'Company Name': 'NaN', 'Website': 'null', 'Location': 'undefined'}
        ])
        clean_corr, stats_corr = clean_dataframe(corrupted_df)
        scored_corr = add_validation_scores(clean_corr)
        leads_corr = add_lead_score(scored_corr)
        self.assertEqual(len(leads_corr), 2)
        # Check scores handle completely empty records cleanly without throwing ZeroDivisionError or TypeError
        for sc in leads_corr['Lead Score']:
            self.assertGreaterEqual(sc, 0)
            self.assertLessEqual(sc, 100)


if __name__ == '__main__':
    unittest.main()
