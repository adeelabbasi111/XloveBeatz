"""
XLoveBeatz Beat License Generator
Automated license document generation for Basic and Premium beat licenses (PDF Output)
"""
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import Image
from datetime import datetime
from reportlab.platypus import Table, TableStyle, Image
from reportlab.lib import colors
from typing import Dict, List
import os

class BeatLicenseGenerator:
    """Generate XLoveBeatz beat licenses automatically as PDFs"""

    def __init__(self):
        self.licensor_name = "Mandraj Joshi"
        self.licensor_stage_name = "XLoveBeatz"
        self.licensor_location = "Mumbai, India"

        # Initialize ReportLab styles
        self.styles = getSampleStyleSheet()
        self.heading_style = ParagraphStyle(
            name='CenterHeading',
            parent=self.styles['Normal'],
            fontSize=14,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=12
        )
        self.normal_style = ParagraphStyle(
            name='NormalCustom',
            parent=self.styles['Normal'],
            fontSize=11,
            fontName='Helvetica',
            leading=14,
            spaceAfter=6
        )

    def _create_heading(self, story: List, text: str):
        """Add a bold centered heading to the document story"""
        story.append(Paragraph(text, self.heading_style))

    def _create_section(self, story: List, number: int, title: str, content: str):
        """Add a numbered section with title and content"""
        # Replace newlines with HTML <br/> tags for ReportLab compatibility
        safe_content = content.replace('\n', '<br/>')
        formatted_text = f"<b>{number}. {title}</b><br/>{safe_content}"
        story.append(Paragraph(formatted_text, self.normal_style))

    def _add_bullet_points(self, story: List, points: list):
        """Add bullet points to document"""
        items = [ListItem(Paragraph(point, self.normal_style)) for point in points]
        bullet_list = ListFlowable(
            items,
            bulletType='bullet',
            leftIndent=20,
            spaceBefore=6,
            spaceAfter=6
        )
        story.append(bullet_list)

    def _add_signature_block(self, story: List, role: str, name: str = ""):
        """Add signature block for licensor or licensee"""
        story.append(Spacer(1, 0.25 * inch))
        story.append(Paragraph(f"<b>{role}</b>", self.normal_style))
        if name:
            story.append(Paragraph(name, self.normal_style))
        if role == "Licensor":
            sig_image = Image(
                "../static/images/signature.png",
                width=0.8 * inch,
                height=0.5 * inch
            )

            signature_table = Table([
                ["Signature:", sig_image]
            ], colWidths=[0.8 * inch, 1 * inch],
            hAlign='LEFT')

            signature_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(signature_table)
        story.append(Spacer(1, 0.15 * inch))  # gap before Date
        story.append(Paragraph(f"\nDate: {datetime.today().strftime('%d-%B-%Y')}", self.normal_style))
        story.append(Spacer(1, 0.25 * inch))

    def generate_basic_license(self, license_data: Dict) -> List:
        """
        Generate a Basic Beat License document story (flowables)

        Args:
            license_data: Dictionary with keys:
                - licensee_legal_name: str
                - artist_stage_name: str
                - beat_name: str
                - effective_date: str (format: DD-MM-YYYY)

        Returns:
            List of ReportLab flowables (the document "story")
        """
        story = []

        # Title
        self._create_heading(story, "XLoveBeatz – Non-Exclusive Basic Beat License Agreement")

        # Header info
        header_info = [
            f"Effective Date: {license_data['effective_date']}",
            f"Licensee Legal Name: {license_data['licensee_legal_name']}",
            f"Beat Name: {license_data['beat_name']}",
            f"License Fee Paid: {license_data['beat_price']} INR"
        ]

        if license_data.get('artist_stage_name'):
            header_info.insert(
                2,
                f"Stage/Artist Name: {license_data['artist_stage_name']}"
            )
        for info in header_info:
            story.append(Paragraph(info, self.normal_style))

        story.append(Spacer(1, 0.2 * inch))

        # Section 1: Parties
        self._create_section(story, 1, "Parties",
            f"This Non-Exclusive Basic License Agreement (\"Agreement\") is entered into between:\n\n"
            f"Licensor:\n"
            f"{self.licensor_name}, professionally known as {self.licensor_stage_name}, {self.licensor_location}.\n\n"
            f"and\n\n"
            f"Licensee:\n"
            f"The individual or entity identified above who has legally purchased the licensed beat."
        )

        # Section 2: Licensed Beat
        self._create_section(story, 2, "Licensed Beat",
            "This Agreement applies solely to the beat identified above (\"Beat\"). The Beat remains the exclusive "
            "intellectual property of the Licensor at all times."
        )

        # Section 3: Grant of License
        self._create_section(story, 3, "Grant of License",
            "Upon receipt of full payment, the Licensor grants the Licensee a non-exclusive, non-transferable, "
            "revocable license to:"
        )
        self._add_bullet_points(story, [
            "Record vocals and create original songs using the Beat",
            "Distribute and monetize those songs on digital streaming platforms",
            "Upload songs to streaming and social media platforms",
            "Perform the songs live",
            "Use the Beat in one (1) monetized music video"
        ])

        # Section 4: Usage Limits
        story.append(Spacer(1, 0.1 * inch))
        self._create_section(story, 4, "Usage Limits", "")
        self._add_bullet_points(story, [
            "Up to 1,000,000 total audio streams across all streaming platforms combined",
            "One (1) monetized music video with up to 1,000,000 total video views",
            "Up to 10,000 copies of recordings created using the Beat (physical and digital combined)"
        ])
        story.append(Paragraph("If any usage limit is exceeded, the Licensee must obtain an upgraded license before further commercial exploitation.", self.normal_style))

        # Section 5: Credit Requirement
        self._create_section(story, 5, "Credit Requirement",
            "\"Produced by XLoveBeatz\" should be credited wherever reasonably possible."
        )

        # Section 6: Ownership
        self._create_section(story, 6, "Ownership",
            "The Beat, instrumental composition, arrangement, and underlying sound recording remain the sole "
            "property of the Licensor. The Licensee acquires only the limited usage rights expressly granted herein."
        )

        # Section 7: Content ID Policy
        self._create_section(story, 7, "Content ID Policy",
            "The Licensor shall not register the Beat with YouTube Content ID during the term of this license. "
            "The Licensee may not independently register the Beat or derivative versions with Content ID or "
            "similar rights management systems."
        )

        # Section 8: Restrictions
        self._create_section(story, 8, "Restrictions", "The Licensee shall not:")
        self._add_bullet_points(story, [
            "Resell, sublicense, lease, transfer, or distribute the Beat by itself",
            "Upload the Beat without vocals or significant original artistic contribution",
            "Claim ownership of the Beat",
            "Use it in TV, films, games, advertisements, or synchronization projects without written permission",
            "Register the Beat as exclusive property"
        ])

        # Section 9: Term
        self._create_section(story, 9, "Term",
            "This license shall remain valid for five (5) years from the Effective Date."
        )

        # Section 10: Termination
        self._create_section(story, 10, "Termination",
            "Any violation automatically terminates all rights granted to the Licensee."
        )

        # Section 11: Limitation of Liability
        self._create_section(story, 11, "Limitation of Liability",
            "The Licensor shall not be liable for indirect, incidental, special, or consequential damages arising "
            "from use of the Beat."
        )

        # Section 12: Governing Law
        self._create_section(story, 12, "Governing Law",
            "Governed by the laws of India. Any dispute shall be subject to the exclusive jurisdiction of the "
            "courts located in Mumbai, Maharashtra, India."
        )

        story.append(Spacer(1, 0.3 * inch))

        # Signature blocks
        self._add_signature_block(story, "Licensor", f"{self.licensor_name} ({self.licensor_stage_name})")
        self._add_signature_block(story, "Licensee", license_data['licensee_legal_name'])

        return story

    def generate_premium_license(self, license_data: Dict) -> List:
        """
        Generate a Premium Beat License document story (flowables)
        """
        story = []

        # Title
        self._create_heading(story, "XLoveBeatz – Non-Exclusive Premium Beat License Agreement")

        # Header info
        header_info = [
            f"Effective Date: {license_data['effective_date']}",
            f"Licensee Legal Name: {license_data['licensee_legal_name']}",
            f"Beat Name: {license_data['beat_name']}",
            f"License Fee Paid: {license_data['beat_price']} INR"
        ]

        if license_data.get('artist_stage_name'):
            header_info.insert(
                2,
                f"Stage/Artist Name: {license_data['artist_stage_name']}"
            )
        for info in header_info:
            story.append(Paragraph(info, self.normal_style))

        story.append(Spacer(1, 0.2 * inch))

        # Section 1: Parties
        self._create_section(story, 1, "Parties",
            f"This Non-Exclusive Premium License Agreement (\"Agreement\") is entered into between "
            f"{self.licensor_name}, professionally known as {self.licensor_stage_name} (\"Licensor\"), "
            f"and the purchaser identified above (\"Licensee\")."
        )

        # Section 2: Licensed Beat
        self._create_section(story, 2, "Licensed Beat",
            "This Agreement applies solely to the Beat identified above. The Beat remains the exclusive "
            "intellectual property of the Licensor at all times."
        )

        # Section 3: Grant of License
        self._create_section(story, 3, "Grant of License",
            "Upon receipt of full payment, the Licensee may:"
        )
        self._add_bullet_points(story, [
            "Record vocals, create songs, distribute and monetize those songs on digital streaming platforms",
            "Upload them to social media platforms",
            "Perform them live",
            "Use the Beat in one (1) monetized music video"
        ])

        # Section 4: Usage Limits
        story.append(Spacer(1, 0.1 * inch))
        self._create_section(story, 4, "Usage Limits", "")
        self._add_bullet_points(story, [
            "Up to 1,000,000 total audio streams across all streaming platforms combined",
            "One (1) monetized music video with up to 1,000,000 total video views",
            "Up to 10,000 copies of recordings created using the Beat (physical and digital combined)"
        ])

        # Section 5: Credit Requirement
        self._create_section(story, 5, "Credit Requirement",
            "Credit should be given as: \"Produced by XLoveBeatz\" wherever reasonably possible."
        )

        # Section 6: Ownership
        self._create_section(story, 6, "Ownership",
            "The Beat, composition, arrangement, and underlying sound recording remain the sole property of "
            "the Licensor. Only usage rights are granted."
        )

        # Section 7: Content ID Policy
        self._create_section(story, 7, "Content ID Policy",
            "The Licensor shall not register the Beat with YouTube Content ID during the term of this license. "
            "The Licensee may not register the Beat or derivative versions with Content ID or similar "
            "rights-management systems."
        )

        # Section 8: Restrictions
        self._create_section(story, 8, "Restrictions",
            "The Licensee shall not resell, sublicense, transfer, distribute, or claim ownership of the Beat, "
            "nor use it in films, TV, games, advertisements, or synchronization projects without written permission."
        )

        # Section 9: Term
        self._create_section(story, 9, "Term",
            "This license shall remain valid for seven (7) years from the Effective Date stated above."
        )

        # Section 10: Termination
        self._create_section(story, 10, "Termination",
            "Any violation of this Agreement shall automatically terminate all rights granted to the Licensee."
        )

        # Section 11: Limitation of Liability
        self._create_section(story, 11, "Limitation of Liability",
            "The Licensor shall not be liable for any indirect, incidental, special, or consequential damages "
            "arising from the use of the Beat."
        )

        # Section 12: Governing Law
        self._create_section(story, 12, "Governing Law",
            "This Agreement shall be governed by the laws of India and subject to the exclusive jurisdiction of "
            "the courts located in Mumbai, Maharashtra, India."
        )

        story.append(Spacer(1, 0.3 * inch))

        # Signature blocks
        self._add_signature_block(story, "Licensor", f"{self.licensor_name} ({self.licensor_stage_name})")
        self._add_signature_block(story, "Licensee", license_data['licensee_legal_name'])

        return story

    def save_license(self, story: List, filename: str, output_dir: str = "./data"):
        """
        Save the generated license story as a PDF document

        Args:
            story: List of ReportLab flowables
            filename: Output filename (without extension)
            output_dir: Directory to save the file

        Returns:
            Full path to saved PDF file
        """
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        file_path = os.path.join(output_dir, f"{filename}.pdf")

        # Build the PDF
        doc = SimpleDocTemplate(
            file_path,
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )
        doc.build(story)
        return file_path


# ============================================================================
# USAGE EXAMPLES
# ============================================================================
def example_usage():
    """Example of how to use the license generator"""
    generator = BeatLicenseGenerator()

    # Example 1: Generate Basic License
    basic_license_data = {
        'licensee_legal_name': 'Ahmed Khan',
        'artist_stage_name': 'Striker Productions',
        'beat_name': 'Midnight Vibes',
        'effective_date': '11-06-2026',
        'beat_price':'999'
    }

    basic_story = generator.generate_basic_license(basic_license_data)
    basic_path = generator.save_license(basic_story, "Ahmed_Khan_Basic_License")
    print(f"✓ Basic license generated: {basic_path}")

    # Example 2: Generate Premium License
    premium_license_data = {
        'licensee_legal_name': 'Zara Studios',
        'artist_stage_name': 'Beat Masters',
        'beat_name': 'Future Shock',
        'effective_date': '11-06-2026'
    }

    premium_story = generator.generate_premium_license(premium_license_data)
    premium_path = generator.save_license(premium_story, "Zara_Studios_Premium_License")
    print(f"✓ Premium license generated: {premium_path}")


# ============================================================================
# BATCH PROCESSING FUNCTION
# ============================================================================
def generate_bulk_licenses(licenses_data: list, output_dir: str = "./licenses"):
    """
    Generate multiple licenses at once
    """
    generator = BeatLicenseGenerator()
    created_files = []

    for idx, license_info in enumerate(licenses_data, 1):
        license_type = license_info['license_type'].lower()
        artist_name = license_info['artist_stage_name'].replace(' ', '_')
        filename = f"{idx}_{artist_name}_{license_type.upper()}_License"

        try:
            if license_type == 'basic':
                story = generator.generate_basic_license(license_info)
            elif license_type == 'premium':
                story = generator.generate_premium_license(license_info)
            else:
                print(f"⚠ Skipping: Unknown license type '{license_type}'")
                continue

            file_path = generator.save_license(story, filename, output_dir)
            created_files.append(file_path)
            print(f"✓ Generated: {filename}.pdf")

        except Exception as e:
            print(f"✗ Error generating {filename}: {str(e)}")

    return created_files


if __name__ == "__main__":
    # Run examples
    generator = BeatLicenseGenerator()

    # Example 1: Generate Basic License
    basic_license_data = {
        'licensee_legal_name': 'Adeel Abbasi',
        'beat_name': 'Midnight Vibes',
        'effective_date': '11-06-2026',
        'beat_price': '1999'
    }

    basic_story = generator.generate_premium_license(basic_license_data)
    basic_path = generator.save_license(basic_story, f"{basic_license_data['licensee_legal_name']}_{basic_license_data['beat_name']}")
    print(f"✓ Basic license generated: {basic_path}")


