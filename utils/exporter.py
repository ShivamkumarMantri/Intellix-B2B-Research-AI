from io import BytesIO
from datetime import datetime
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def to_excel_bytes(
    df: pd.DataFrame,
    summary: dict | None = None,
    raw_df: pd.DataFrame | None = None,
    stats: dict | None = None
) -> bytes:
    """Generate a recruiter-ready, professional 4-sheet Excel report with styled headers,
    freeze panes, auto-fit column widths, conditional formatting, and clickable hyperlinks."""
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # -------------------------------------------------------------
    # Shared Style Definitions
    # -------------------------------------------------------------
    font_family = "Segoe UI"
    
    title_font = Font(name=font_family, size=15, bold=True, color="FFFFFF")
    subtitle_font = Font(name=font_family, size=10, italic=True, color="CBD5E1")
    section_font = Font(name=font_family, size=12, bold=True, color="1E293B")
    header_font = Font(name=font_family, size=10, bold=True, color="FFFFFF")
    cell_font = Font(name=font_family, size=9.5, color="1E293B")
    link_font = Font(name=font_family, size=9.5, color="2563EB", underline="single")
    muted_font = Font(name=font_family, size=9, color="64748B", italic=True)

    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid") # Dark Navy
    sub_header_fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid") # Slate
    banner_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid") # Deep Slate
    accent_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid") # Subtle gray
    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid") # Very light slate

    # Category Pill Fills
    high_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid") # Soft Green
    high_font = Font(name=font_family, size=9.5, bold=True, color="065F46")
    med_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid") # Soft Amber
    med_font = Font(name=font_family, size=9.5, bold=True, color="92400E")
    low_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid") # Soft Red
    low_font = Font(name=font_family, size=9.5, bold=True, color="991B1B")

    thin_border_side = Side(border_style="thin", color="CBD5E1")
    thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    header_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=Side(border_style="medium", color="0F172A"))

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=False)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=False)
    align_left_wrap = Alignment(horizontal="left", vertical="top", wrap_text=True)

    summary = summary or {}
    stats = stats or {}

    # -------------------------------------------------------------
    # SHEET 1: Research Results
    # -------------------------------------------------------------
    ws1 = wb.create_sheet(title="Research Results")
    ws1.views.sheetView[0].showGridLines = True

    display_cols = [
        'Data Source',
        'Company Name',
        'Lead Score',
        'Lead Category',
        'Confidence Score',
        'Data Completeness %',
        'Industry',
        'Location',
        'Website',
        'LinkedIn URL',
        'Decision Maker',
        'Decision Maker Role',
        'Source URL',
        'Lead Score Reason',
        'Company Description',
        'Research Summary'
    ]
    cols_to_use = [c for c in display_cols if c in df.columns]

    # Write Headers
    for col_idx, col_name in enumerate(cols_to_use, 1):
        cell = ws1.cell(row=1, column=col_idx, value=col_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center if col_name in ['Lead Score', 'Lead Category', 'Confidence Score', 'Data Completeness %', 'Data Source'] else align_left
        cell.border = header_border

    ws1.row_dimensions[1].height = 26

    # Write Data Rows
    for row_idx, (_, row) in enumerate(df.iterrows(), 2):
        is_zebra = (row_idx % 2 == 0)
        row_fill = zebra_fill if is_zebra else None

        for col_idx, col_name in enumerate(cols_to_use, 1):
            val = row.get(col_name, '')
            cell = ws1.cell(row=row_idx, column=col_idx)
            cell.border = thin_border
            if row_fill:
                cell.fill = row_fill

            # Format by column type
            if col_name == 'Lead Category':
                cell.value = str(val)
                cell.alignment = align_center
                if val == 'High Potential':
                    cell.fill = high_fill
                    cell.font = high_font
                elif val == 'Medium Potential':
                    cell.fill = med_fill
                    cell.font = med_font
                else:
                    cell.fill = low_fill
                    cell.font = low_font
            elif col_name in ['Lead Score', 'Confidence Score', 'Data Completeness %']:
                try:
                    cell.value = float(val) if val != '' else None
                    cell.number_format = '0' if col_name == 'Lead Score' else '0.0"%"'
                except Exception:
                    cell.value = str(val)
                cell.alignment = align_center
                cell.font = cell_font
            elif col_name in ['Website', 'LinkedIn URL', 'Source URL']:
                url_str = str(val).strip()
                if url_str and ('http' in url_str):
                    cell.value = url_str
                    cell.hyperlink = url_str
                    cell.font = link_font
                else:
                    cell.value = url_str if url_str else 'Unavailable'
                    cell.font = cell_font if url_str else muted_font
                cell.alignment = align_left
            elif col_name in ['Company Description', 'Research Summary', 'Lead Score Reason']:
                cell.value = str(val) if val else 'Unavailable'
                cell.font = cell_font if val else muted_font
                cell.alignment = align_left_wrap
            else:
                cell.value = str(val) if val else 'Unavailable'
                cell.font = cell_font if val else muted_font
                cell.alignment = align_left

        ws1.row_dimensions[row_idx].height = 20

    # Auto-filter and freeze pane
    if cols_to_use and len(df) > 0:
        last_col = get_column_letter(len(cols_to_use))
        ws1.auto_filter.ref = f"A1:{last_col}{len(df) + 1}"
    ws1.freeze_panes = "C2"  # Freeze headers and Company Name

    # Auto-adjust column widths
    for col_idx, col_name in enumerate(cols_to_use, 1):
        col_letter = get_column_letter(col_idx)
        if col_name in ['Company Description', 'Research Summary', 'Lead Score Reason']:
            ws1.column_dimensions[col_letter].width = 42
        elif col_name in ['Website', 'LinkedIn URL', 'Source URL']:
            ws1.column_dimensions[col_letter].width = 28
        elif col_name in ['Company Name', 'Decision Maker', 'Industry', 'Location']:
            ws1.column_dimensions[col_letter].width = 22
        elif col_name in ['Lead Score', 'Confidence Score', 'Data Completeness %', 'Lead Category']:
            ws1.column_dimensions[col_letter].width = 16
        else:
            ws1.column_dimensions[col_letter].width = 18

    # -------------------------------------------------------------
    # SHEET 2: Data Quality
    # -------------------------------------------------------------
    ws2 = wb.create_sheet(title="Data Quality")
    ws2.views.sheetView[0].showGridLines = True

    # Title Block
    ws2.merge_cells("A1:G1")
    title_cell = ws2.cell(row=1, column=1, value="🛡️ Enterprise B2B Data Quality & Hygiene Audit")
    title_cell.font = Font(name=font_family, size=13, bold=True, color="FFFFFF")
    title_cell.fill = banner_fill
    title_cell.alignment = align_left
    ws2.row_dimensions[1].height = 30

    # Section 1: KPI Metrics Table
    kpi_headers = ["Total Ingested Records", "Valid Unique Entities", "Duplicate Records Resolved", "Incomplete Records", "Invalid URLs Detected", "Avg Verification Confidence", "Avg Data Completeness %"]
    kpi_values = [
        stats.get('total_raw_records', len(raw_df) if raw_df is not None and not raw_df.empty else len(df)),
        len(df),
        stats.get('duplicates_detected', 0),
        int((df['Data Completeness %'] < 100.0).sum()) if 'Data Completeness %' in df.columns else 0,
        stats.get('invalid_urls', 0),
        f"{df['Confidence Score'].mean():.1f}%" if 'Confidence Score' in df.columns and len(df) > 0 else "0.0%",
        f"{df['Data Completeness %'].mean():.1f}%" if 'Data Completeness %' in df.columns and len(df) > 0 else "0.0%"
    ]

    for c_idx, (h, v) in enumerate(zip(kpi_headers, kpi_values), 1):
        h_cell = ws2.cell(row=3, column=c_idx, value=h)
        h_cell.font = Font(name=font_family, size=8.5, bold=True, color="475569")
        h_cell.fill = accent_fill
        h_cell.alignment = align_center
        h_cell.border = thin_border

        v_cell = ws2.cell(row=4, column=c_idx, value=v)
        v_cell.font = Font(name=font_family, size=13, bold=True, color="1E293B")
        v_cell.alignment = align_center
        v_cell.border = thin_border
        ws2.column_dimensions[get_column_letter(c_idx)].width = 24

    ws2.row_dimensions[3].height = 20
    ws2.row_dimensions[4].height = 26

    # Section 2: Detailed Audit Table
    ws2.cell(row=6, column=1, value="Record-by-Record Hygiene & Verification Log").font = section_font

    audit_headers = ["Company Name", "Data Completeness %", "Confidence Score", "Website Status", "LinkedIn Status", "Decision Maker Status", "Validation Notes", "Source Citation"]
    for c_idx, h in enumerate(audit_headers, 1):
        cell = ws2.cell(row=7, column=c_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center if c_idx in [2, 3] else align_left
        cell.border = header_border

    ws2.row_dimensions[7].height = 22

    for r_idx, (_, r) in enumerate(df.iterrows(), 8):
        c_name = r.get('Company Name', '')
        comp_pct = r.get('Data Completeness %', 0)
        conf_sc = r.get('Confidence Score', 0)
        web_val = "Verified" if r.get('Website') and 'http' in str(r.get('Website')) else "Missing/Invalid"
        lk_val = "Verified" if r.get('LinkedIn URL') and 'linkedin.com' in str(r.get('LinkedIn URL')) else "Unavailable"
        dm_val = f"Found ({r.get('Decision Maker Role', 'Lead')})" if r.get('Decision Maker') else "Unavailable"
        notes = r.get('Validation Notes', 'Verified')
        src = r.get('Source URL', '')

        row_vals = [c_name, comp_pct, conf_sc, web_val, lk_val, dm_val, notes, src]
        for c_idx, val in enumerate(row_vals, 1):
            cell = ws2.cell(row=r_idx, column=c_idx)
            cell.border = thin_border
            cell.font = cell_font
            if c_idx in [2, 3]:
                cell.value = float(val)
                cell.number_format = '0.0"%"'
                cell.alignment = align_center
            elif c_idx == 8 and 'http' in str(val):
                cell.value = str(val)
                cell.hyperlink = str(val)
                cell.font = link_font
                cell.alignment = align_left
            else:
                cell.value = str(val)
                cell.alignment = align_left

        ws2.row_dimensions[r_idx].height = 19

    ws2.column_dimensions['G'].width = 38
    ws2.column_dimensions['H'].width = 32

    # -------------------------------------------------------------
    # SHEET 3: Lead Scoring
    # -------------------------------------------------------------
    ws3 = wb.create_sheet(title="Lead Scoring")
    ws3.views.sheetView[0].showGridLines = True

    # Title Block
    ws3.merge_cells("A1:K1")
    t3 = ws3.cell(row=1, column=1, value="🎯 Transparent 0-100 Lead Scoring Model & Factor Allocations")
    t3.font = Font(name=font_family, size=13, bold=True, color="FFFFFF")
    t3.fill = banner_fill
    t3.alignment = align_left
    ws3.row_dimensions[1].height = 30

    # Section 1: Rubric Weights Table
    ws3.cell(row=3, column=1, value="Scoring Weights Rubric (100% Deterministic • Sum = 100 Pts)").font = section_font

    rubric_items = [
        ("1. Industry Relevance", "25 pts", "Direct vertical match (+25), domain overlap (+15), general (+5)"),
        ("2. Location Match", "20 pts", "Exact hub/city match (+20), regional state match (+12), unverified (+0)"),
        ("3. Decision Maker", "15 pts", "Named executive with role (+15), name only (+8), unavailable (+0)"),
        ("4. Data Completeness", "15 pts", "Completeness ≥88% (+15), ≥70% (+10), ≥50% (+6), low (+2)"),
        ("5. Website Availability", "10 pts", "Verified active domain (+10), missing/invalid (+0)"),
        ("6. Research Confidence", "10 pts", "High confidence tier (+10), medium (+6), low (+2)"),
        ("7. LinkedIn Availability", "5 pts", "Verified profile link (+5), unavailable (+0)")
    ]

    for idx, (factor, weight, desc) in enumerate(rubric_items, 4):
        ws3.cell(row=idx, column=1, value=factor).font = Font(name=font_family, size=9.5, bold=True, color="1E293B")
        w_cell = ws3.cell(row=idx, column=2, value=weight)
        w_cell.font = Font(name=font_family, size=9.5, bold=True, color="7C6CF2")
        w_cell.alignment = align_center
        ws3.cell(row=idx, column=3, value=desc).font = Font(name=font_family, size=9, color="64748B")
        for c in range(1, 4):
            ws3.cell(row=idx, column=c).border = thin_border
        ws3.row_dimensions[idx].height = 19

    ws3.column_dimensions['A'].width = 24
    ws3.column_dimensions['B'].width = 14
    ws3.column_dimensions['C'].width = 50

    # Section 2: Prospect Factor Breakdown Table
    ws3.cell(row=12, column=1, value="Prospect Scoring Breakdowns & Deterministic Explanations").font = section_font

    score_headers = [
        "Company Name", "Lead Score", "Lead Category", "Industry (25)", "Location (20)",
        "Decision Maker (15)", "Completeness (15)", "Website (10)", "Confidence (10)",
        "LinkedIn (5)", "Score Explanation"
    ]
    for c_idx, h in enumerate(score_headers, 1):
        cell = ws3.cell(row=13, column=c_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center if c_idx in range(2, 11) else align_left
        cell.border = header_border

    ws3.row_dimensions[13].height = 24

    for r_idx, (_, r) in enumerate(df.iterrows(), 14):
        c_name = r.get('Company Name', '')
        score = r.get('Lead Score', 0)
        cat = r.get('Lead Category', 'Medium Potential')
        factors = r.get('Score Factors', {})
        exp = r.get('Lead Score Reason', '')

        row_vals = [
            c_name, score, cat,
            factors.get('Industry Relevance', 0),
            factors.get('Location Match', 0),
            factors.get('Decision Maker', 0),
            factors.get('Data Completeness', 0),
            factors.get('Website Availability', 0),
            factors.get('Research Confidence', 0),
            factors.get('LinkedIn Availability', 0),
            exp
        ]

        for c_idx, val in enumerate(row_vals, 1):
            cell = ws3.cell(row=r_idx, column=c_idx)
            cell.border = thin_border

            if c_idx == 2:
                cell.value = int(val)
                cell.alignment = align_center
                cell.font = Font(name=font_family, size=10, bold=True)
            elif c_idx == 3:
                cell.value = str(val)
                cell.alignment = align_center
                if val == 'High Potential':
                    cell.fill = high_fill
                    cell.font = high_font
                elif val == 'Medium Potential':
                    cell.fill = med_fill
                    cell.font = med_font
                else:
                    cell.fill = low_fill
                    cell.font = low_font
            elif c_idx in range(4, 11):
                cell.value = int(val)
                cell.alignment = align_center
                cell.font = cell_font
            elif c_idx == 11:
                cell.value = str(val)
                cell.alignment = align_left_wrap
                cell.font = cell_font
            else:
                cell.value = str(val)
                cell.alignment = align_left
                cell.font = cell_font

        ws3.row_dimensions[r_idx].height = 20

    for col in ['D', 'E', 'F', 'G', 'H', 'I', 'J']:
        ws3.column_dimensions[col].width = 14
    ws3.column_dimensions['K'].width = 55
    ws3.freeze_panes = "D14"

    # -------------------------------------------------------------
    # SHEET 4: Research Summary
    # -------------------------------------------------------------
    ws4 = wb.create_sheet(title="Research Summary")
    ws4.views.sheetView[0].showGridLines = True

    # Title Banner
    ws4.merge_cells("A1:E1")
    t4 = ws4.cell(row=1, column=1, value="📊 AI B2B Web Research & Market Intelligence Executive Report")
    t4.font = title_font
    t4.fill = banner_fill
    t4.alignment = align_left
    ws4.row_dimensions[1].height = 34

    ws4.cell(row=2, column=1, value="Generated by Intellix B2B Research OS • Professional Recruiter-Ready Dataset").font = muted_font

    # Scope Summary Table
    ws4.cell(row=4, column=1, value="Research Parameters & Scope Manifest").font = section_font
    manifest_rows = [
        ("Search Query", summary.get('Query', 'N/A')),
        ("Target Industry", summary.get('Target Industry', 'Artificial Intelligence')),
        ("Target Location", summary.get('Target Location', 'Mumbai')),
        ("Target Company Type", summary.get('Target Company Type', 'B2B SaaS / Product')),
        ("Keywords / Signals", summary.get('Keywords', 'automation')),
        ("Generation Timestamp", summary.get('Generated At', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))),
        ("Dataset Classification", "DEMO DATASET [For Professional Portfolio & Evaluation Purposes]" if (('Data Source' in df.columns and len(df) > 0 and 'DEMO' in str(df['Data Source'].iloc[0]).upper()) or ('DEMO' in str(summary.get('Query', '')).upper())) else "Live Web Research Ingestion")
    ]

    for idx, (label, val) in enumerate(manifest_rows, 5):
        l_cell = ws4.cell(row=idx, column=1, value=label)
        l_cell.font = Font(name=font_family, size=9.5, bold=True, color="334155")
        l_cell.fill = accent_fill
        l_cell.border = thin_border

        ws4.merge_cells(f"B{idx}:E{idx}")
        v_cell = ws4.cell(row=idx, column=2, value=str(val))
        v_cell.font = Font(name=font_family, size=9.5, color="1E293B", bold=(label=="Dataset Classification"))
        v_cell.alignment = align_left
        for c in range(2, 6):
            ws4.cell(row=idx, column=c).border = thin_border
        ws4.row_dimensions[idx].height = 20

    # Executive Cohort Metrics
    ws4.cell(row=13, column=1, value="Executive Cohort Aggregates").font = section_font

    cohort_metrics = [
        ("Total Leads", len(df)),
        ("High Potential", int((df['Lead Category'] == 'High Potential').sum()) if 'Lead Category' in df.columns else 0),
        ("Medium Potential", int((df['Lead Category'] == 'Medium Potential').sum()) if 'Lead Category' in df.columns else 0),
        ("Low Potential", int((df['Lead Category'] == 'Low Potential').sum()) if 'Lead Category' in df.columns else 0),
        ("Avg Lead Fit", f"{df['Lead Score'].mean():.1f}/100" if 'Lead Score' in df.columns and len(df) > 0 else "0.0/100")
    ]

    for c_idx, (m_lbl, m_val) in enumerate(cohort_metrics, 1):
        lbl_c = ws4.cell(row=14, column=c_idx, value=m_lbl)
        lbl_c.font = Font(name=font_family, size=8.5, bold=True, color="475569")
        lbl_c.fill = accent_fill
        lbl_c.alignment = align_center
        lbl_c.border = thin_border

        val_c = ws4.cell(row=15, column=c_idx, value=str(m_val))
        val_c.font = Font(name=font_family, size=13, bold=True, color="7C6CF2" if m_lbl=="Avg Lead Fit" else "1E293B")
        val_c.alignment = align_center
        val_c.border = thin_border

    ws4.row_dimensions[14].height = 20
    ws4.row_dimensions[15].height = 28

    # Top 5 Opportunities Spotlight
    ws4.cell(row=17, column=1, value="⭐ Top Priority ICP Opportunities Spotlight").font = section_font

    top_cols = ["Rank", "Company Name", "Industry", "Location", "Lead Score", "Lead Category", "Decision Maker", "Source URL"]
    for c_idx, h in enumerate(top_cols, 1):
        cell = ws4.cell(row=18, column=c_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center if c_idx in [1, 5, 6] else align_left
        cell.border = header_border

    ws4.row_dimensions[18].height = 22

    top_5 = df.sort_values(by=['Lead Score'], ascending=False).head(5) if ('Lead Score' in df.columns and len(df) > 0) else pd.DataFrame()
    for r_idx, (_, r) in enumerate(top_5.iterrows(), 19):
        rank = f"#{r_idx - 18}"
        c_name = r.get('Company Name', '')
        ind = r.get('Industry', '')
        loc = r.get('Location', '')
        score = int(r.get('Lead Score', 0))
        cat = r.get('Lead Category', 'High Potential')
        dm = f"{r.get('Decision Maker')} ({r.get('Decision Maker Role')})" if r.get('Decision Maker') else "Unavailable"
        src = r.get('Source URL', '')

        for c_idx, val in enumerate([rank, c_name, ind, loc, score, cat, dm, src], 1):
            cell = ws4.cell(row=r_idx, column=c_idx)
            cell.border = thin_border
            if c_idx == 1:
                cell.value = str(val)
                cell.alignment = align_center
                cell.font = Font(name=font_family, size=9.5, bold=True, color="7C6CF2")
            elif c_idx == 5:
                cell.value = val
                cell.alignment = align_center
                cell.font = Font(name=font_family, size=10, bold=True)
            elif c_idx == 6:
                cell.value = str(val)
                cell.alignment = align_center
                cell.fill = high_fill if val == 'High Potential' else med_fill
                cell.font = high_font if val == 'High Potential' else med_font
            elif c_idx == 8 and 'http' in str(val):
                cell.value = str(val)
                cell.hyperlink = str(val)
                cell.font = link_font
                cell.alignment = align_left
            else:
                cell.value = str(val)
                cell.alignment = align_left
                cell.font = cell_font

        ws4.row_dimensions[r_idx].height = 20

    ws4.column_dimensions['A'].width = 24
    ws4.column_dimensions['B'].width = 24
    ws4.column_dimensions['C'].width = 22
    ws4.column_dimensions['D'].width = 20
    ws4.column_dimensions['E'].width = 16
    ws4.column_dimensions['F'].width = 18
    ws4.column_dimensions['G'].width = 26
    ws4.column_dimensions['H'].width = 30

    # Save to BytesIO
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
