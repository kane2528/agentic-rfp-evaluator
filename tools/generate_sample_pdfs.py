"""Reproducibly generate four fictional 3-page RFP response PDFs."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parents[1] / "sample_rfps"

PROPOSALS = [
    {
        "slug": "apex_systems", "name": "Apex Systems", "tagline": "Secure architecture for a resilient procurement platform",
        "summary": "Apex proposes a modular cloud procurement platform with a well-defined API gateway, event-driven services, and isolated data domains. The design is technically detailed and security-forward. Delivery is planned over 24 weeks, and the fixed implementation price is the highest in this fictional competition.",
        "understanding": "The buyer needs a secure, scalable supplier and purchasing workflow that integrates with an existing ERP, supports auditable approvals, and provides role-based access across business units.",
        "solution": "Apex will deploy a containerized service tier behind a managed API gateway. The proposal names REST interfaces, an asynchronous event bus for status changes, a relational transaction store, and a separate analytics warehouse. Environments are separated for development, test, and production. The integration design includes versioned APIs and retry queues, though the buyer's legacy ERP connector is subject to discovery.",
        "timeline": "24 weeks: discovery and architecture (weeks 1-4); foundation and identity integration (5-9); procurement workflows and ERP adapter (10-16); security testing and migration rehearsal (17-21); acceptance and launch (22-24). The schedule is moderate and reserves three weeks for acceptance.",
        "team": "A delivery lead, solution architect, two backend engineers, integration engineer, QA lead, and fractional security specialist. Apex proposes a named delivery lead after contract signature; individual CVs are not included in this response.",
        "milestones": "M1 approved architecture; M2 identity and environments ready; M3 end-to-end ERP sandbox transaction; M4 penetration test closure; M5 buyer acceptance and production handover. A weekly steering review and fortnightly demonstrations are proposed.",
        "price": [["Work package", "Fee (fictional USD)"], ["Discovery and architecture", "$185,000"], ["Platform and integrations", "$520,000"], ["Security and launch", "$155,000"], ["Total fixed implementation", "$860,000"]],
        "assumptions": "Price assumes one ERP instance, up to three business units, buyer-provided test credentials, and standard weekday access to subject-matter experts. Hosting and third-party license fees are excluded. Change requests are time-and-materials at $210/hour after written approval.",
        "security": "Apex specifies TLS 1.2+ in transit, AES-256 at rest, managed key rotation, SSO using OIDC, least-privilege roles, immutable administrative audit events, and quarterly vulnerability scans. A third-party penetration test is included before launch. The response describes alignment with ISO 27001 control practices but does not claim a certification; a certificate was not supplied.",
        "compliance": "Data residency can be configured for the buyer's selected region. Retention and deletion rules will be mapped in discovery. The response does not provide a SOC 2 report or a formal privacy impact assessment.",
        "risks": "Legacy ERP data quality and connector behavior may affect schedule; the buyer must provide a sandbox by week 2. The fixed price excludes hosting and licenses. Apex proposes a joint risk register reviewed weekly and a rollback rehearsal before launch.",
        "support": "Thirty days of hypercare are included, with business-hours support and a one-hour response target for severity-one incidents. A 24/7 support tier is available under a separate annual service agreement. A named customer success manager is assigned at launch.",
        "experience": "Apex reports completing six procurement workflow programs in the past five years, including two ERP integrations for organizations with more than 2,000 users. Project descriptions are summarized; customer names are withheld in this fictional proposal.",
        "references": "Two reference calls can be arranged after shortlist selection. Contact details and signed permission letters are not included in this response.",
    },
    {
        "slug": "brightpath_tech", "name": "BrightPath Tech", "tagline": "A fast, affordable path to digital purchasing",
        "summary": "BrightPath offers a low-cost, rapid rollout using its configurable purchasing portal. The proposal emphasizes speed and standard features. It provides limited detail about compliance, technical integration, and the team's prior delivery history.",
        "understanding": "The buyer wants a simpler online request and approval process, with supplier records, purchase status visibility, and a connection to the current finance system.",
        "solution": "BrightPath proposes its hosted web portal with configurable forms, email notifications, and a CSV exchange with the finance system. A direct API connector may be added after technical discovery. The proposal does not include an integration sequence diagram or specific throughput targets.",
        "timeline": "10 weeks: kickoff and configuration (weeks 1-2); buyer review (3-4); data import and CSV setup (5-6); user training (7); pilot (8); launch (9); stabilization (10). The schedule is fast and depends on prompt buyer sign-off.",
        "team": "A project coordinator, configuration consultant, and shared test analyst. BrightPath expects the buyer's administrator to prepare user lists and validate migrated supplier data. Named staff biographies are not included.",
        "milestones": "M1 approved forms; M2 configured test site; M3 supplier import; M4 pilot sign-off; M5 launch. The proposal calls for two remote workshops and a weekly status email.",
        "price": [["Work package", "Fee (fictional USD)"], ["Portal setup", "$62,000"], ["Data import and training", "$21,000"], ["Launch support", "$12,000"], ["Total fixed implementation", "$95,000"]],
        "assumptions": "Price assumes standard portal configuration, one CSV import, up to 500 supplier records, and remote workshops. Custom APIs, data cleansing, and travel are excluded. Optional support after the first month costs $1,500 per month. Taxes and portal subscription renewal are not stated.",
        "security": "The vendor states that the portal uses encrypted web connections and individual user accounts. The response does not specify encryption at rest, key management, multi-factor authentication, audit log retention, incident response times, or independent security testing.",
        "compliance": "BrightPath says it will follow the buyer's security questionnaire process. No certification, audit report, data residency commitment, privacy control detail, or compliance mapping is included in the proposal.",
        "risks": "The ten-week schedule has little contingency. The CSV approach may require manual reconciliation, and compliance information is incomplete. BrightPath suggests a pilot with a small user group but does not include a formal rollback procedure.",
        "support": "Launch support is available by email during weekday business hours for 30 days. The response does not define severity levels or service-level response targets.",
        "experience": "BrightPath reports two small portal configuration projects completed during the past two years. The proposal does not provide user counts, project outcomes, or named references.",
        "references": "References are available on request, but no reference contacts or case studies are included.",
    },
    {
        "slug": "nexaworks", "name": "NexaWorks", "tagline": "A balanced delivery plan with sustained operational support",
        "summary": "NexaWorks presents a balanced, phased proposal with a strong implementation method and extensive post-launch support. The price is mid-range and assumptions are clearly itemized. Its technical design is credible, though some architecture decisions are deferred to discovery.",
        "understanding": "The program must replace email-based purchasing requests with a transparent workflow, retain audit history, integrate to the existing ERP, and support adoption across distributed teams.",
        "solution": "NexaWorks proposes a configurable procurement application with a documented REST integration layer, SSO, role-based approval paths, and a reporting dashboard. The team will validate interface contracts in a time-boxed discovery sprint. Data migration includes one mock run and one production rehearsal.",
        "timeline": "18 weeks with staged approvals: mobilization and discovery (weeks 1-3); configuration and integration (4-9); data rehearsal and security review (10-12); user acceptance and training (13-15); phased launch (16-17); handover (18). Two weeks of schedule contingency are explicitly reserved.",
        "team": "A named program manager, business analyst, integration architect, two configuration engineers, QA engineer, change lead, and support transition manager. Roles and estimated allocation are shown for each phase.",
        "milestones": "M1 requirements baseline; M2 interface contract signed; M3 configured solution and ERP sandbox test; M4 migration rehearsal; M5 user acceptance exit; M6 first business unit launch; M7 operational handover. Demonstrations occur every two weeks and acceptance criteria are recorded.",
        "price": [["Work package", "Fee (fictional USD)"], ["Discovery and design", "$118,000"], ["Configuration and integration", "$302,000"], ["Testing, training, launch", "$126,000"], ["Total fixed implementation", "$546,000"]],
        "assumptions": "Fixed fee covers one ERP tenant, up to four business units, 1,200 initial supplier records, remote delivery, and two migration rehearsals. Hosting is estimated at $4,800 per month but billed directly by the cloud provider. Work outside scope requires an agreed change order.",
        "security": "The proposal commits to TLS in transit, encryption at rest, MFA for administrators, SSO integration, least-privilege access, quarterly access reviews, centralized audit logs, and a documented incident escalation process. A penetration test is planned before launch; its report will be shared under NDA. The proposal does not claim external certification.",
        "compliance": "NexaWorks will map the buyer's control questionnaire during discovery and document data flows, retention, and deletion. Data residency will be selected with the buyer. No independent compliance certificate is attached.",
        "risks": "ERP interface access and buyer decision latency are schedule dependencies. NexaWorks proposes an interface spike in week 2, named buyer decision owners, a risk log with owners, and a launch readiness gate. A phased rollout reduces the effect of unresolved issues.",
        "support": "Ninety days of included hypercare with a 30-minute severity-one acknowledgement target, named service manager, weekly incident review, and monthly service reports. Optional ongoing support is $8,500 per month with 24/7 severity-one coverage and a 15-minute acknowledgement target.",
        "experience": "NexaWorks reports nine workflow implementations in the past four years, including three ERP-integrated programs between 800 and 3,000 users. Two anonymized case summaries include adoption measures and delivery outcomes.",
        "references": "Three reference interviews are offered after shortlist selection. Written reference letters are available under NDA; contacts are not embedded in the response.",
    },
    {
        "slug": "orbit_digital", "name": "Orbit Digital", "tagline": "Experienced transformation team for a dependable rollout",
        "summary": "Orbit Digital brings substantial delivery experience and strong customer references, with a mid-priced proposal. The delivery approach is practical, but the integration plan is high-level and several interface details are left for later discovery.",
        "understanding": "The buyer needs a consistent purchasing experience, visibility into approval status, and reliable exchange of approved transactions with the finance platform.",
        "solution": "Orbit proposes a managed procurement portal with configurable approval chains, reporting, and ERP connectivity. Integration will use the buyer's preferred method, such as API or secure file exchange, selected in discovery. Field mapping, retry behavior, and reconciliation details are not yet specified.",
        "timeline": "20 weeks: kickoff and interviews (weeks 1-3); configuration (4-8); integration discovery and build (6-13); testing (14-17); training and launch (18-19); handover (20). Integration tasks overlap configuration and are dependent on buyer access.",
        "team": "A senior program director, project manager, functional lead, integration consultant, two developers, and shared QA. Orbit has delivered similar programs with this team structure; named individual assignments are finalized after award.",
        "milestones": "M1 process design approval; M2 portal configured; M3 integration method agreed; M4 test transactions; M5 user acceptance; M6 launch. Monthly steering committee and weekly delivery working group are proposed.",
        "price": [["Work package", "Fee (fictional USD)"], ["Program and process design", "$120,000"], ["Portal configuration", "$214,000"], ["Integration and launch", "$236,000"], ["Total estimated implementation", "$570,000"]],
        "assumptions": "Estimate assumes one finance system, two interfaces, up to 1,000 suppliers, and standard remote access. Final fixed fee follows integration discovery. Hosting, data cleansing, and third-party licenses are excluded. Additional integrations are estimated at $35,000-$70,000 each.",
        "security": "Orbit describes encrypted communications, role-based access, SSO compatibility, security testing before launch, and a documented incident contact. Details for encryption at rest, MFA, audit log retention, and vulnerability remediation deadlines are not supplied.",
        "compliance": "Orbit will complete the buyer's questionnaire and can host in a selected region. No certification or independent audit report is included. Retention settings are available but the response does not define a proposed schedule.",
        "risks": "Integration scope remains vague until discovery and the price is an estimate rather than a fixed fee. Orbit proposes an early interface workshop and a change approval board, but no detailed fallback or rollback method is described.",
        "support": "Sixty days of post-launch support with a named service desk, weekday coverage, severity-based prioritization, and a four-hour initial response target for critical incidents. Extended coverage can be contracted separately.",
        "experience": "Orbit reports 14 comparable digital workflow deployments over seven years, including programs for organizations with more than 5,000 users. The proposal summarizes adoption and schedule outcomes and names three fictional reference organizations with permission for calls.",
        "references": "Three named fictional references are offered: Northstar Foods (2024), Meridian Transit (2023), and Cedarline Group (2022). Contact details are provided at shortlist stage in this synthetic proposal.",
    },
]


def generate_one(proposal: dict) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{proposal['slug']}.pdf"
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontSize=23, leading=28, textColor=colors.HexColor("#17324D"), alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle(name="SectionHeading", parent=styles["Heading2"], fontSize=12, leading=15, textColor=colors.HexColor("#0E7490"), spaceBefore=8, spaceAfter=4))
    styles.add(ParagraphStyle(name="BodyCompact", parent=styles["BodyText"], fontSize=9.2, leading=12.2, spaceAfter=5))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=.65*inch, leftMargin=.65*inch, topMargin=.62*inch, bottomMargin=.6*inch, title=f"{proposal['name']} Fictional RFP Response")
    story = [Paragraph("FICTIONAL PROCUREMENT RESPONSE", styles["Small"]), Spacer(1, 30), Paragraph(proposal["name"], styles["CoverTitle"]), Paragraph(proposal["tagline"], styles["Heading2"]), Spacer(1, 22), Paragraph("Prepared for: Synthetic Enterprise Procurement Program", styles["BodyText"]), Paragraph("Proposal ID: DEMO-2026-" + proposal["slug"].upper(), styles["BodyText"]), Paragraph("All organizations, amounts, references, and project details in this document are fictional and created for classroom demonstration.", styles["Small"]), Spacer(1, 16)]
    def section(title: str, text: str) -> None:
        story.extend([Paragraph(title, styles["SectionHeading"]), Paragraph(text, styles["BodyCompact"])])
    section("Executive Summary", proposal["summary"])
    section("Understanding of the Requirement", proposal["understanding"])
    section("Proposed Solution", proposal["solution"])
    section("Implementation Approach and Timeline", proposal["timeline"])
    section("Team Structure", proposal["team"])
    story.extend([PageBreak(), Paragraph(proposal["name"] + " | Delivery and Commercial Proposal", styles["Heading1"])])
    section("Milestones and Governance", proposal["milestones"])
    story.extend([Paragraph("Price Table (fictional USD)", styles["SectionHeading"]), Spacer(1, 3)])
    table = Table(proposal["price"], colWidths=[4.25*inch, 2.1*inch], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0,0),(-1,0), colors.HexColor("#17324D")), ("TEXTCOLOR", (0,0),(-1,0), colors.white), ("FONTNAME", (0,0),(-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0),(-1,-1), 9), ("GRID", (0,0),(-1,-1), .4, colors.HexColor("#CBD5E1")), ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white, colors.HexColor("#F1F5F9")]), ("ALIGN", (1,1),(1,-1), "RIGHT"), ("TOPPADDING", (0,0),(-1,-1), 7), ("BOTTOMPADDING", (0,0),(-1,-1), 7)]))
    story.extend([table, Spacer(1, 5)])
    section("Pricing Assumptions", proposal["assumptions"])
    section("Security Controls", proposal["security"])
    section("Compliance", proposal["compliance"])
    story.extend([PageBreak(), Paragraph(proposal["name"] + " | Assurance and Operations", styles["Heading1"])])
    section("Risk Controls", proposal["risks"])
    section("Support Model", proposal["support"])
    section("Relevant Experience", proposal["experience"])
    section("References", proposal["references"])
    section("Proposal Notes", "This response is a synthetic educational example. Any missing detail should be clarified during due diligence; no unstated control, capability, or commercial term should be assumed.")
    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.line(.65*inch, .48*inch, 7.85*inch, .48*inch)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(.65*inch, .32*inch, "SYNTHETIC CLASSROOM DOCUMENT | NOT A REAL SUPPLIER PROPOSAL")
        canvas.drawRightString(7.85*inch, .32*inch, f"Page {document.page}")
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return path


if __name__ == "__main__":
    for item in PROPOSALS:
        print(generate_one(item))
