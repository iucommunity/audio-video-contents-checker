"""Generate PDF and CSV reports from check results."""

import csv
import os
from datetime import datetime
from typing import List, Dict
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import config


class ReportGenerator:
    """Generate PDF and CSV reports."""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or config.REPORTS_DIR
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_csv(self, results: List[Dict], summary: Dict) -> str:
        """Generate CSV report."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(self.output_dir, f"content_check_report_{timestamp}.csv")
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Name', 'Type', 'URL', 'Status', 'Error Message', 'Check Time']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in results:
                writer.writerow({
                    'Name': result.get('name', ''),
                    'Type': result.get('type', ''),
                    'URL': result.get('url', ''),
                    'Status': result.get('status', ''),
                    'Error Message': result.get('error_message', ''),
                    'Check Time': result.get('check_time', '')
                })
        
        print(f"\nCSV report saved: {filename}")
        return filename
    
    def generate_pdf(self, results: List[Dict], summary: Dict) -> str:
        """Generate PDF report."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(self.output_dir, f"content_check_report_{timestamp}.pdf")
        
        doc = SimpleDocTemplate(filename, pagesize=letter)
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=1  # Center
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=20
        )
        
        # Title
        story.append(Paragraph("Content Check Report", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Summary
        story.append(Paragraph("Summary", heading_style))
        
        summary_data = [
            ['Total Items Checked', str(summary['total'])],
            ['Working', str(summary['working'])],
            ['Broken', str(summary['broken'])],
            ['Check Time', summary.get('check_time', 'N/A')]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Summary by type
        if summary.get('by_type'):
            story.append(Paragraph("Summary by Type", heading_style))
            
            type_data = [['Type', 'Total', 'Working', 'Broken']]
            for type_name, type_stats in summary['by_type'].items():
                type_data.append([
                    type_name.capitalize(),
                    str(type_stats['total']),
                    str(type_stats['working']),
                    str(type_stats['broken'])
                ])
            
            type_table = Table(type_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch])
            type_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
            ]))
            story.append(type_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Broken content (grouped by type)
        broken_results = [r for r in results if r.get('status') != 'working']
        if broken_results:
            story.append(PageBreak())
            story.append(Paragraph("Broken Content", heading_style))
            
            # Group broken by type
            broken_by_type = {}
            for result in broken_results:
                result_type = result.get('type', 'unknown')
                if result_type not in broken_by_type:
                    broken_by_type[result_type] = []
                broken_by_type[result_type].append(result)
            
            for type_name, type_results in broken_by_type.items():
                story.append(Paragraph(f"{type_name.capitalize()} ({len(type_results)} broken)", 
                                      styles['Heading3']))
                story.append(Spacer(1, 0.1*inch))
                
                # Create table for this type
                table_data = [['Name', 'URL', 'Error']]
                for result in type_results:
                    name = result.get('name', 'Unknown')[:50]  # Truncate long names
                    url = result.get('url', '')[:60]  # Truncate long URLs
                    error = result.get('error_message', 'N/A')[:80]  # Truncate long errors
                    table_data.append([name, url, error])
                
                # Calculate column widths
                table = Table(table_data, colWidths=[2*inch, 2.5*inch, 2.5*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff5f5')]),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('WORDWRAP', (0, 0), (-1, -1), True)
                ]))
                story.append(table)
                story.append(Spacer(1, 0.2*inch))
        
        # Working content (optional - can be commented out if too long)
        working_results = [r for r in results if r.get('status') == 'working']
        if working_results and len(working_results) <= 100:  # Only show if not too many
            story.append(PageBreak())
            story.append(Paragraph("Working Content", heading_style))
            
            # Group working by type
            working_by_type = {}
            for result in working_results:
                result_type = result.get('type', 'unknown')
                if result_type not in working_by_type:
                    working_by_type[result_type] = []
                working_by_type[result_type].append(result)
            
            for type_name, type_results in working_by_type.items():
                story.append(Paragraph(f"{type_name.capitalize()} ({len(type_results)} working)", 
                                      styles['Heading3']))
                story.append(Spacer(1, 0.1*inch))
                
                table_data = [['Name', 'URL']]
                for result in type_results:
                    name = result.get('name', 'Unknown')[:50]
                    url = result.get('url', '')[:80]
                    table_data.append([name, url])
                
                table = Table(table_data, colWidths=[3*inch, 4*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fff4')])
                ]))
                story.append(table)
                story.append(Spacer(1, 0.2*inch))
        
        # Build PDF
        doc.build(story)
        print(f"PDF report saved: {filename}")
        return filename
    
    def generate_reports(self, results: List[Dict], summary: Dict, output_format: str = "both"):
        """
        Generate reports in specified format(s).
        
        Args:
            results: List of check results
            summary: Summary statistics
            output_format: 'pdf', 'csv', or 'both'
        """
        generated_files = []
        
        if output_format in ['csv', 'both']:
            csv_file = self.generate_csv(results, summary)
            generated_files.append(csv_file)
        
        if output_format in ['pdf', 'both']:
            pdf_file = self.generate_pdf(results, summary)
            generated_files.append(pdf_file)
        
        return generated_files
