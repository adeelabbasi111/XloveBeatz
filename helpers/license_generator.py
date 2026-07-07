"""
XLoveBeatz Beat License Generator
Automated license document generation for Basic, Premium, and Exclusive beat licenses (PDF Output)
"""
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable,
    ListItem, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import Image
from reportlab.lib import colors
from datetime import datetime
from typing import Dict, List, Optional
import os
import uuid


class BeatLicenseGenerator:
    """Generate XLoveBeatz beat licenses automatically as PDFs"""

    def __init__(self):
        # Licensor details
        self.licensor_name = "Mandraj Joshi"
        self.licensor_stage_name = "XLoveBeatz"
        self.licensor_location = "Mumbai, India"
        self.licensor_email = "xlovebeatz@gmail.com"
        self.licensor_whatsapp = "+91 83291 89796"
        self.licensor_website = "xlovebeats.com"

        # Initialize ReportLab styles
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """Set up all paragraph styles"""
        self.heading_style = ParagraphStyle(
            name='CenterHeading',
            parent=self.styles['Normal'],
            fontSize=14,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=6,
            textColor=colors.HexColor('#1a1a2e')
        )

        self.sub_heading_style = ParagraphStyle(
            name='SubHeading',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica',
            alignment=TA_CENTER,
            spaceAfter=16,
            textColor=colors.HexColor('#555555')
        )

        self.normal_style = ParagraphStyle(
            name='NormalCustom',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica',
            leading=14,
            spaceAfter=6,
            textColor=colors.HexColor('#333333')
        )

        self.small_style = ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Helvetica',
            leading=10,
            spaceAfter=4,
            textColor=colors.HexColor('#888888')
        )

        self.label_style = ParagraphStyle(
            name='Label',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Helvetica',
            textColor=colors.HexColor('#999999'),
            spaceAfter=2
        )

        self.value_style = ParagraphStyle(
            name='Value',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=6
        )

        self.footer_style = ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=7,
            fontName='Helvetica',
            alignment=TA_CENTER,
            textColor=colors.HexColor('#aaaaaa'),
            spaceBefore=8
        )

    # ──────────────────────────────────────────────────────────
    #  HELPER METHODS
    # ──────────────────────────────────────────────────────────

    def _generate_license_id(self) -> str:
        """Generate a unique license ID"""
        short_uuid = uuid.uuid4().hex[:8].upper()
        return f"XLB-{short_uuid}"

    def _create_heading(self, story: List, text: str):
        story.append(Paragraph(text, self.heading_style))

    def _create_sub_heading(self, story: List, text: str):
        story.append(Paragraph(text, self.sub_heading_style))

    def _create_section(self, story: List, number: int, title: str, content: str):
        safe_content = content.replace('\n', '<br/>')
        formatted_text = f"<b>{number}. {title}</b><br/>{safe_content}"
        story.append(Paragraph(formatted_text, self.normal_style))

    def _add_bullet_points(self, story: List, points: list):
        items = [ListItem(Paragraph(point, self.normal_style)) for point in points]
        bullet_list = ListFlowable(
            items,
            bulletType='bullet',
            leftIndent=20,
            spaceBefore=6,
            spaceAfter=6
        )
        story.append(bullet_list)

    def _add_divider(self, story: List):
        story.append(Spacer(1, 0.1 * inch))
        story.append(HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.HexColor('#dddddd'),
            spaceBefore=4,
            spaceAfter=8
        ))

    def _add_info_table(self, story: List, rows: list):
        """
        Add a clean info table. rows = [(label, value), ...]
        """
        table_data = []
        for label, value in rows:
            table_data.append([
                Paragraph(f"<font color='#888888' size='8'>{label}</font>", self.normal_style),
                Paragraph(f"<b>{value}</b>", self.normal_style),
            ])

        if not table_data:
            return

        t = Table(table_data, colWidths=[2.2 * inch, 4.3 * inch])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#eeeeee')),
        ]))
        story.append(t)

    def _add_signature_block(self, story: List, role: str, name: str = ""):
        story.append(Spacer(1, 0.25 * inch))
        story.append(Paragraph(f"<b>{role}</b>", self.normal_style))
        if name:
            story.append(Paragraph(name, self.normal_style))

        if role == "Licensor":
            sig_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'static', 'images', 'signature.png'
            )

            if os.path.exists(sig_path):
                sig_image = Image(sig_path, width=0.8 * inch, height=0.5 * inch)
                signature_table = Table(
                    [["Signature:", sig_image]],
                    colWidths=[0.8 * inch, 1 * inch],
                    hAlign='LEFT'
                )
                signature_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ]))
                story.append(signature_table)
            else:
                story.append(Paragraph("<i>Digitally signed</i>", self.normal_style))

        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(f"Date: {datetime.today().strftime('%d %B %Y')}", self.normal_style))
        story.append(Spacer(1, 0.15 * inch))

    # ──────────────────────────────────────────────────────────
    #  BASIC LICENSE
    # ──────────────────────────────────────────────────────────

    def generate_basic_license(self, license_data: Dict) -> List:
        story = []
        license_id = self._generate_license_id()

        # Title
        self._create_heading(story, "XLoveBeatz – Non-Exclusive Basic Beat License Agreement")
        self._create_sub_heading(story, f"License ID: {license_id}")

        self._add_divider(story)

        # License Details Table
        info_rows = [
            ("Effective Date", license_data.get('effective_date', '—')),
            ("License ID", license_id),
            ("Licensee Name", license_data.get('licensee_legal_name', '—')),
        ]
        if license_data.get('artist_stage_name'):
            info_rows.append(("Artist / Stage Name", license_data['artist_stage_name']))
        if license_data.get('buyer_email'):
            info_rows.append(("Email", license_data['buyer_email']))
        if license_data.get('order_id'):
            info_rows.append(("Order ID", f"#XLV-{license_data['order_id']}"))
        if license_data.get('transaction_id'):
            info_rows.append(("Transaction ID", license_data['transaction_id']))

        info_rows.append(("Beat Name", license_data.get('beat_name', '—')))
        info_rows.append(("License Type", "Basic (Non-Exclusive)"))
        info_rows.append(("License Fee Paid", f"₹{license_data.get('beat_price', '0')} INR"))

        self._add_info_table(story, info_rows)

        # Beat Specifications (if available)
        specs = []
        if license_data.get('bpm'):
            specs.append(("BPM", str(license_data['bpm'])))
        if license_data.get('musical_key'):
            specs.append(("Key", license_data['musical_key']))
        if license_data.get('genre'):
            specs.append(("Genre", license_data['genre']))
        if license_data.get('duration'):
            specs.append(("Duration", license_data['duration']))

        if specs:
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph("<b>Beat Specifications</b>", self.normal_style))
            self._add_info_table(story, specs)

        self._add_divider(story)

        # Section 1: Parties
        self._create_section(story, 1, "Parties",
            f"This Non-Exclusive Basic License Agreement (\"Agreement\") is entered into between:<br/><br/>"
            f"<b>Licensor:</b> {self.licensor_name}, professionally known as \"{self.licensor_stage_name}\", "
            f"located in {self.licensor_location}.<br/><br/>"
            f"<b>Licensee:</b> {license_data.get('licensee_legal_name', 'the purchaser')} "
            f"who has legally purchased the licensed beat."
        )

        # Section 2: Licensed Beat
        self._create_section(story, 2, "Licensed Beat",
            f"This Agreement applies solely to the beat titled \"{license_data.get('beat_name', '—')}\" (\"Beat\"). "
            "The Beat remains the exclusive intellectual property of the Licensor at all times."
        )

        # Section 3: Grant of License
        self._create_section(story, 3, "Grant of License",
            "Upon receipt of full payment, the Licensor grants the Licensee a non-exclusive, non-transferable, "
            "revocable license to:"
        )
        self._add_bullet_points(story, [
            "Record vocals and create original songs using the Beat",
            "Distribute and monetize those songs on all major digital streaming platforms (Spotify, Apple Music, YouTube Music, JioSaavn, etc.)",
            "Upload songs to social media and streaming platforms",
            "Perform the songs live at concerts, events, and streams",
            "Use the Beat in one (1) monetized music video"
        ])

        # Section 4: Usage Limits
        self._create_section(story, 4, "Usage Limits", "")
        self._add_bullet_points(story, [
            "Up to <b>1,000,000</b> total audio streams across all platforms combined",
            "One (1) monetized music video with up to <b>1,000,000</b> total video views",
            "Up to <b>10,000</b> copies of recordings (physical and digital combined)",
            "No radio broadcasting rights"
        ])
        story.append(Paragraph(
            "If any usage limit is exceeded, the Licensee must obtain an upgraded license (Premium or Exclusive) "
            "before further commercial exploitation.",
            self.normal_style
        ))

        # Section 5: Files Included
        self._create_section(story, 5, "Files Included with This License",
            "The following files are provided with the Basic License:"
        )
        self._add_bullet_points(story, [
            "MP3 file (tagged, high quality)",
            "WAV file (unmastered, 24-bit)"
        ])

        # Section 6: Credit Requirement
        self._create_section(story, 6, "Credit Requirement",
            "The Licensee must credit the producer in all distributed works as:<br/>"
            "<b>\"Produced by XLoveBeatz\"</b><br/>"
            "Credit should appear in the song title, description, or metadata wherever reasonably possible."
        )

        # Section 7: Ownership
        self._create_section(story, 7, "Ownership",
            "The Beat, instrumental composition, arrangement, melody, and underlying sound recording remain the sole "
            "and exclusive property of the Licensor. The Licensee acquires only the limited usage rights expressly "
            "granted in this Agreement. No transfer of copyright or ownership occurs."
        )

        # Section 8: Content ID Policy
        self._create_section(story, 8, "Content ID & Rights Management",
            "The Licensor shall not register the Beat with YouTube Content ID during the term of this license. "
            "The Licensee may <b>not</b> independently register the Beat or derivative versions with YouTube Content ID, "
            "or any similar rights management system (DistroKid, TuneCore, etc.) without prior written consent."
        )

        # Section 9: Restrictions
        self._create_section(story, 9, "Restrictions", "The Licensee shall <b>not</b>:")
        self._add_bullet_points(story, [
            "Resell, sublicense, lease, transfer, or distribute the Beat by itself (without vocals)",
            "Upload the Beat without vocals or significant original artistic contribution",
            "Claim ownership or authorship of the Beat",
            "Use the Beat in TV, films, games, advertisements, podcasts, or synchronization projects without written permission",
            "Register the Beat as exclusive property",
            "Sample, remix, or create derivative works for resale"
        ])

        # Section 10: Term
        self._create_section(story, 10, "Term",
            "This license shall remain valid for <b>five (5) years</b> from the Effective Date stated above. "
            "After expiration, the Licensee must renew the license or cease all commercial use."
        )

        # Section 11: Termination
        self._create_section(story, 11, "Termination",
            "Any violation of this Agreement shall automatically and immediately terminate all rights granted "
            "to the Licensee. Upon termination, the Licensee must cease all distribution and remove all content "
            "containing the Beat from all platforms within 7 days."
        )

        # Section 12: Refund Policy
        self._create_section(story, 12, "Refund Policy",
            "All sales are final. Due to the digital nature of the product, no refunds will be issued once the "
            "Beat files have been downloaded or accessed. If you experience technical issues, contact support."
        )

        # Section 13: Limitation of Liability
        self._create_section(story, 13, "Limitation of Liability",
            "The Licensor shall not be liable for indirect, incidental, special, or consequential damages arising "
            "from the use of the Beat. The Licensor's total liability shall not exceed the license fee paid."
        )

        # Section 14: Governing Law
        self._create_section(story, 14, "Governing Law",
            "This Agreement is governed by the laws of India. Any dispute shall be subject to the exclusive "
            "jurisdiction of the courts located in Mumbai, Maharashtra, India."
        )

        # Contact
        self._add_divider(story)
        story.append(Paragraph(
            f"<b>Contact the Licensor:</b><br/>"
            f"Email: {self.licensor_email} | WhatsApp: {self.licensor_whatsapp} | Web: {self.licensor_website}",
            self.small_style
        ))

        story.append(Spacer(1, 0.3 * inch))

        # Signatures
        self._add_signature_block(story, "Licensor", f"{self.licensor_name} ({self.licensor_stage_name})")
        self._add_signature_block(story, "Licensee", license_data.get('licensee_legal_name', ''))

        # Footer
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(
            f"This is an official license document generated by XLoveBeats ({self.licensor_website}). "
            f"License ID: {license_id}. Verify at {self.licensor_website}/verify/{license_id}",
            self.footer_style
        ))

        return story

    # ──────────────────────────────────────────────────────────
    #  PREMIUM LICENSE
    # ──────────────────────────────────────────────────────────

    def generate_premium_license(self, license_data: Dict) -> List:
        story = []
        license_id = self._generate_license_id()

        # Title
        self._create_heading(story, "XLoveBeatz – Non-Exclusive Premium Beat License Agreement")
        self._create_sub_heading(story, f"License ID: {license_id}")

        self._add_divider(story)

        # License Details Table
        info_rows = [
            ("Effective Date", license_data.get('effective_date', '—')),
            ("License ID", license_id),
            ("Licensee Name", license_data.get('licensee_legal_name', '—')),
        ]
        if license_data.get('artist_stage_name'):
            info_rows.append(("Artist / Stage Name", license_data['artist_stage_name']))
        if license_data.get('buyer_email'):
            info_rows.append(("Email", license_data['buyer_email']))
        if license_data.get('order_id'):
            info_rows.append(("Order ID", f"#XLV-{license_data['order_id']}"))
        if license_data.get('transaction_id'):
            info_rows.append(("Transaction ID", license_data['transaction_id']))

        info_rows.append(("Beat Name", license_data.get('beat_name', '—')))
        info_rows.append(("License Type", "Premium (Non-Exclusive)"))
        info_rows.append(("License Fee Paid", f"₹{license_data.get('beat_price', '0')} INR"))

        self._add_info_table(story, info_rows)

        # Beat Specifications
        specs = []
        if license_data.get('bpm'):
            specs.append(("BPM", str(license_data['bpm'])))
        if license_data.get('musical_key'):
            specs.append(("Key", license_data['musical_key']))
        if license_data.get('genre'):
            specs.append(("Genre", license_data['genre']))
        if license_data.get('duration'):
            specs.append(("Duration", license_data['duration']))

        if specs:
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph("<b>Beat Specifications</b>", self.normal_style))
            self._add_info_table(story, specs)

        self._add_divider(story)

        # Section 1: Parties
        self._create_section(story, 1, "Parties",
            f"This Non-Exclusive Premium License Agreement (\"Agreement\") is entered into between:<br/><br/>"
            f"<b>Licensor:</b> {self.licensor_name}, professionally known as \"{self.licensor_stage_name}\", "
            f"located in {self.licensor_location}.<br/><br/>"
            f"<b>Licensee:</b> {license_data.get('licensee_legal_name', 'the purchaser')} "
            f"who has legally purchased the licensed beat."
        )

        # Section 2: Licensed Beat
        self._create_section(story, 2, "Licensed Beat",
            f"This Agreement applies solely to the beat titled \"{license_data.get('beat_name', '—')}\" (\"Beat\"). "
            "The Beat remains the exclusive intellectual property of the Licensor at all times."
        )

        # Section 3: Grant of License
        self._create_section(story, 3, "Grant of License",
            "Upon receipt of full payment, the Licensee may:"
        )
        self._add_bullet_points(story, [
            "Record vocals, create songs, distribute and monetize on all major digital streaming platforms",
            "Upload songs to social media and streaming platforms (Spotify, Apple Music, YouTube Music, JioSaavn, etc.)",
            "Perform the songs live at concerts, events, and streams",
            "Use the Beat in up to <b>three (3)</b> monetized music videos",
            "Use the Beat in podcast episodes (non-exclusive)"
        ])

        # Section 4: Usage Limits
        self._create_section(story, 4, "Usage Limits", "")
        self._add_bullet_points(story, [
            "Up to <b>5,000,000</b> total audio streams across all platforms combined",
            "Up to <b>three (3)</b> monetized music videos with up to <b>5,000,000</b> total video views combined",
            "Up to <b>50,000</b> copies of recordings (physical and digital combined)",
            "Limited radio broadcasting rights (local/regional)"
        ])

        # Section 5: Files Included
        self._create_section(story, 5, "Files Included with This License",
            "The following files are provided with the Premium License:"
        )
        self._add_bullet_points(story, [
            "MP3 file (untagged, high quality)",
            "WAV file (mixed, 24-bit)",
            "Track stems / individual instrument tracks (if available)"
        ])

        # Section 6: Credit Requirement
        self._create_section(story, 6, "Credit Requirement",
            "The Licensee must credit the producer in all distributed works as:<br/>"
            "<b>\"Produced by XLoveBeatz\"</b><br/>"
            "Credit should appear in the song title, description, or metadata wherever reasonably possible."
        )

        # Section 7: Ownership
        self._create_section(story, 7, "Ownership",
            "The Beat, composition, arrangement, melody, and underlying sound recording remain the sole property of "
            "the Licensor. Only limited usage rights are granted. No transfer of copyright occurs."
        )

        # Section 8: Content ID
        self._create_section(story, 8, "Content ID & Rights Management",
            "The Licensor shall not register the Beat with YouTube Content ID during the term of this license. "
            "The Licensee may <b>not</b> register the Beat or derivative versions with Content ID or similar "
            "rights-management systems without prior written consent."
        )

        # Section 9: Restrictions
        self._create_section(story, 9, "Restrictions", "The Licensee shall <b>not</b>:")
        self._add_bullet_points(story, [
            "Resell, sublicense, transfer, distribute, or claim ownership of the Beat",
            "Use the Beat in films, TV, games, advertisements, or synchronization projects without written permission",
            "Upload the Beat without vocals or significant artistic contribution",
            "Sample or remix the Beat for resale to third parties"
        ])

        # Section 10: Term
        self._create_section(story, 10, "Term",
            "This license shall remain valid for <b>seven (7) years</b> from the Effective Date stated above."
        )

        # Section 11: Termination
        self._create_section(story, 11, "Termination",
            "Any violation automatically terminates all rights granted. The Licensee must cease distribution "
            "and remove all content containing the Beat within 7 days of termination."
        )

        # Section 12: Refund Policy
        self._create_section(story, 12, "Refund Policy",
            "All sales are final. Due to the digital nature of the product, no refunds will be issued once the "
            "Beat files have been downloaded or accessed."
        )

        # Section 13: Limitation of Liability
        self._create_section(story, 13, "Limitation of Liability",
            "The Licensor shall not be liable for any indirect, incidental, special, or consequential damages "
            "arising from the use of the Beat. Total liability shall not exceed the license fee paid."
        )

        # Section 14: Governing Law
        self._create_section(story, 14, "Governing Law",
            "Governed by the laws of India. Any dispute shall be subject to the exclusive jurisdiction of the "
            "courts located in Mumbai, Maharashtra, India."
        )

        # Contact
        self._add_divider(story)
        story.append(Paragraph(
            f"<b>Contact the Licensor:</b><br/>"
            f"Email: {self.licensor_email} | WhatsApp: {self.licensor_whatsapp} | Web: {self.licensor_website}",
            self.small_style
        ))

        story.append(Spacer(1, 0.3 * inch))

        # Signatures
        self._add_signature_block(story, "Licensor", f"{self.licensor_name} ({self.licensor_stage_name})")
        self._add_signature_block(story, "Licensee", license_data.get('licensee_legal_name', ''))

        # Footer
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(
            f"This is an official license document generated by XLoveBeats ({self.licensor_website}). "
            f"License ID: {license_id}. Verify at {self.licensor_website}/verify/{license_id}",
            self.footer_style
        ))

        return story

    # ──────────────────────────────────────────────────────────
    #  EXCLUSIVE LICENSE
    # ──────────────────────────────────────────────────────────

    def generate_exclusive_license(self, license_data: Dict) -> List:
        story = []
        license_id = self._generate_license_id()

        # Title
        self._create_heading(story, "XLoveBeatz – Exclusive Beat License Agreement")
        self._create_sub_heading(story, f"License ID: {license_id}")

        self._add_divider(story)

        # License Details Table
        info_rows = [
            ("Effective Date", license_data.get('effective_date', '—')),
            ("License ID", license_id),
            ("Licensee Name", license_data.get('licensee_legal_name', '—')),
        ]
        if license_data.get('artist_stage_name'):
            info_rows.append(("Artist / Stage Name", license_data['artist_stage_name']))
        if license_data.get('buyer_email'):
            info_rows.append(("Email", license_data['buyer_email']))
        if license_data.get('order_id'):
            info_rows.append(("Order ID", f"#XLV-{license_data['order_id']}"))
        if license_data.get('transaction_id'):
            info_rows.append(("Transaction ID", license_data['transaction_id']))

        info_rows.append(("Beat Name", license_data.get('beat_name', '—')))
        info_rows.append(("License Type", "Exclusive (Full Ownership)"))
        info_rows.append(("License Fee Paid", f"₹{license_data.get('beat_price', '0')} INR"))

        self._add_info_table(story, info_rows)

        # Beat Specifications
        specs = []
        if license_data.get('bpm'):
            specs.append(("BPM", str(license_data['bpm'])))
        if license_data.get('musical_key'):
            specs.append(("Key", license_data['musical_key']))
        if license_data.get('genre'):
            specs.append(("Genre", license_data['genre']))
        if license_data.get('duration'):
            specs.append(("Duration", license_data['duration']))

        if specs:
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph("<b>Beat Specifications</b>", self.normal_style))
            self._add_info_table(story, specs)

        self._add_divider(story)

        # Section 1: Parties
        self._create_section(story, 1, "Parties",
            f"This Exclusive License Agreement (\"Agreement\") is entered into between:<br/><br/>"
            f"<b>Licensor:</b> {self.licensor_name}, professionally known as \"{self.licensor_stage_name}\", "
            f"located in {self.licensor_location}.<br/><br/>"
            f"<b>Licensee:</b> {license_data.get('licensee_legal_name', 'the purchaser')} "
            f"who has purchased the exclusive rights to the licensed beat."
        )

        # Section 2: Grant of Exclusive Rights
        self._create_section(story, 2, "Grant of Exclusive Rights",
            "Upon receipt of full payment, the Licensor grants the Licensee <b>exclusive ownership</b> of the Beat, including:"
        )
        self._add_bullet_points(story, [
            "Full ownership of the master recording",
            "Unlimited streams, downloads, and sales",
            "Unlimited music videos",
            "Radio broadcasting rights (local and national)",
            "Synchronization rights (TV, film, games, ads, podcasts)",
            "Right to register with Content ID and all rights management systems",
            "Right to sublicense to other artists for recording purposes"
        ])

        # Section 3: Files Included
        self._create_section(story, 3, "Files Included",
            "The following files are provided with the Exclusive License:"
        )
        self._add_bullet_points(story, [
            "MP3 file (untagged, mastered)",
            "WAV file (mixed and mastered, 24-bit)",
            "Track stems / individual instrument tracks",
            "Project file (FL Studio / Ableton / Logic, if available)"
        ])

        # Section 4: Post-Sale Restrictions
        self._create_section(story, 4, "Post-Sale Restrictions on Licensor",
            "After selling the exclusive rights, the Licensor agrees to:"
        )
        self._add_bullet_points(story, [
            "Remove the Beat from all storefronts and beat stores within 48 hours",
            "Not sell, lease, or license the Beat to any other party",
            "Not distribute the Beat as a free download"
        ])

        # Section 5: Credit
        self._create_section(story, 5, "Credit Requirement",
            "The Licensee is encouraged (but not required) to credit:<br/>"
            "<b>\"Produced by XLoveBeatz\"</b>"
        )

        # Section 6: Ownership Transfer
        self._create_section(story, 6, "Ownership Transfer",
            "The Licensor transfers exclusive rights to the Beat's master recording to the Licensee. "
            "The Licensor retains the right to be credited as the original producer. "
            "The underlying composition copyright remains with the Licensor unless separately negotiated."
        )

        # Section 7: Term
        self._create_section(story, 7, "Term",
            "This exclusive license is <b>perpetual</b> (lifetime). No renewal required."
        )

        # Section 8: Refund Policy
        self._create_section(story, 8, "Refund Policy",
            "All sales are final. No refunds on exclusive purchases."
        )

        # Section 9: Governing Law
        self._create_section(story, 9, "Governing Law",
            "Governed by the laws of India. Disputes subject to courts in Mumbai, Maharashtra, India."
        )

        # Contact
        self._add_divider(story)
        story.append(Paragraph(
            f"<b>Contact the Licensor:</b><br/>"
            f"Email: {self.licensor_email} | WhatsApp: {self.licensor_whatsapp} | Web: {self.licensor_website}",
            self.small_style
        ))

        story.append(Spacer(1, 0.3 * inch))

        # Signatures
        self._add_signature_block(story, "Licensor", f"{self.licensor_name} ({self.licensor_stage_name})")
        self._add_signature_block(story, "Licensee", license_data.get('licensee_legal_name', ''))

        # Footer
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(
            f"This is an official license document generated by XLoveBeats ({self.licensor_website}). "
            f"License ID: {license_id}. Verify at {self.licantor_website}/verify/{license_id}",
            self.footer_style
        ))

        return story

    # ──────────────────────────────────────────────────────────
    #  SAVE LICENSE AS PDF
    # ──────────────────────────────────────────────────────────

    def save_license(self, story: List, filename: str, output_dir: str = "./data") -> str:
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, f"{filename}.pdf")

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