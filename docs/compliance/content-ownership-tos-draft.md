# Bhapi Platform — Content Ownership Terms of Service (DRAFT)

**Version:** 0.1 (Draft for Legal Review)
**Date:** March 19, 2026
**Status:** DRAFT — Not for public use. Requires legal counsel review.
**Jurisdictions:** US, EU, UK, Australia, Brazil

---

> **LEGAL REVIEW REQUIRED:** This document is a working draft and has not been reviewed by qualified legal counsel. It must not be published, distributed, or presented to users in its current form. All provisions require review against applicable law in each jurisdiction listed above.

---

## Table of Contents

1. [Acceptance by Parent or Guardian](#1-acceptance-by-parent-or-guardian)
2. [Content Ownership](#2-content-ownership)
3. [No Training on Child Content](#3-no-training-on-child-content)
4. [AI-Generated Content (Phase 3)](#4-ai-generated-content-phase-3)
5. [Third-Party Content Processing](#5-third-party-content-processing)
6. [Content Removal Rights](#6-content-removal-rights)
7. [Data Retention](#7-data-retention)
8. [CSAM Exception](#8-csam-exception)
9. [Jurisdiction-Specific Provisions](#9-jurisdiction-specific-provisions)
10. [Changes to These Terms](#10-changes-to-these-terms)

---

## 1. Acceptance by Parent or Guardian

### 1.1 Minors Cannot Agree to Terms of Service

Minors do not have legal capacity to enter into binding contracts in any jurisdiction covered by this agreement. Accordingly, **a parent or legal guardian must accept these Terms of Service on behalf of any child user** before the child may access any feature of the Bhapi platform (including Bhapi Social, Bhapi Safety, and the Bhapi browser extension).

By completing the account registration process and confirming acceptance, the parent or legal guardian:

- Acknowledges they have read and understood these Terms in full;
- Agrees on behalf of themselves and the child to be bound by these Terms;
- Confirms they are the child's parent or legal guardian;
- Accepts responsibility for supervising the child's use of the platform.

### 1.2 Age-Tiered Onboarding

Bhapi operates across three age tiers. Separate, age-appropriate versions of these Terms and associated privacy notices are provided for each tier:

| Tier | Age Range | Language Complexity |
|------|-----------|---------------------|
| Tier 1 — Little Explorers | Ages 5–9 | Simplified — large print, plain words, illustrated summaries |
| Tier 2 — Discovery | Ages 10–12 | Moderate — plain English, shorter sentences, key terms defined |
| Tier 3 — Connected | Ages 13–15 | Full — standard legal language with a plain-language summary |

The parent or guardian receives and must accept the full legal version of these Terms regardless of the child's age tier. The child-facing version is provided for comprehension purposes in compliance with the UK Age Appropriate Design Code (AADC) and is not a substitute for parental consent.

### 1.3 UK AADC Child-Friendly Language Requirement

In compliance with the UK Children's Code (Age Appropriate Design Code), Bhapi publishes a child-friendly summary of key terms alongside this document. That summary:

- Uses language appropriate to the child's age tier;
- Avoids legalese and technical jargon;
- Highlights rights in plain terms (e.g., "You own what you create. We can't sell it. You can delete it any time.");
- Is reviewed by child literacy experts before each publication.

### 1.4 Verification of Parental Identity

Bhapi uses age and identity verification measures consistent with COPPA 2026 and applicable law. Verification methods may include:

- Credit or debit card verification (US);
- Yoti digital identity verification (EU, UK, AU);
- Government ID document check (where required by law);
- Knowledge-based authentication.

Providing false information during verification is a breach of these Terms and may result in account termination.

---

## 2. Content Ownership

### 2.1 Child Retains Ownership

All content created by a child user on the Bhapi platform ("Child-Created Content") is and remains the intellectual property of the child, represented by their parent or legal guardian. Bhapi does not claim ownership of Child-Created Content.

Child-Created Content includes but is not limited to:

- Text posts, comments, captions, and messages;
- Images, drawings, illustrations, and graphics uploaded or created in-app;
- Videos and audio recordings;
- Creative works produced using Bhapi's creative tools;
- Profile information and biographical content voluntarily provided by the user.

### 2.2 Limited License Granted to Bhapi

By posting or uploading Child-Created Content, the parent or guardian grants Bhapi a **limited, non-exclusive, revocable, royalty-free license** solely for the following purposes:

1. **Display:** To display, render, and transmit the content within the Bhapi platform to the child and, where applicable, to other permitted users (e.g., friends or family approved by the parent);
2. **Safety Screening:** To submit content to automated safety classification systems for the purposes of detecting harmful, illegal, or age-inappropriate material, including CSAM detection (see Section 8);
3. **Platform Operation:** To store, cache, replicate, and back up content as reasonably necessary to operate, maintain, and improve the technical reliability of the platform;
4. **Legal Compliance:** To retain or disclose content to the extent required by applicable law (see Section 8).

### 2.3 Scope Limitations

This license expressly does **not** permit Bhapi to:

- Sell, license, or sublicense Child-Created Content to any third party for commercial purposes;
- Use Child-Created Content in advertising, marketing, or promotional materials;
- Use Child-Created Content to train, fine-tune, or evaluate any artificial intelligence or machine learning model (see Section 3 for the full prohibition);
- Share Child-Created Content with third parties except as set out in Section 5 (safety providers) and Section 8 (CSAM legal obligation).

### 2.4 License Termination on Deletion

The license granted in Section 2.2 terminates automatically when:

- The child or parent deletes the specific piece of content; or
- The account is deleted in full.

Termination of the license triggers the deletion timelines set out in Sections 6 and 7. Residual copies held in encrypted backups are purged on the schedule described in Section 7.4.

---

## 3. No Training on Child Content

### 3.1 Absolute Prohibition

Bhapi **will not** use any Child-Created Content to train, fine-tune, benchmark, evaluate, or otherwise develop any artificial intelligence or machine learning model, whether operated by Bhapi or any third party. This prohibition is unconditional and applies regardless of:

- Whether the content has been anonymized or pseudonymized;
- Whether the parent or guardian purports to consent (this consent is not sought and will not be relied upon);
- The type of AI system (generative, discriminative, safety classifier, or otherwise).

### 3.2 Covered Content Types

The prohibition in Section 3.1 applies to all of the following:

| Content Type | Examples |
|--------------|----------|
| Text | Posts, messages, comments, captions, bio fields |
| Images | Photos, drawings, uploaded images, in-app creations |
| Video | Uploaded clips, stories, live recordings |
| Audio | Voice messages, audio recordings |
| Creative works | Stories, poems, artwork created using platform tools |
| Behavioral data | Interaction patterns, engagement signals, navigation logs |
| Inferred data | Interests, preferences, or attributes inferred from usage |

### 3.3 Moderation Model Training

Bhapi's automated content moderation systems (including safety classifiers) are trained exclusively on:

- Synthetic datasets generated for moderation research purposes;
- Curated datasets obtained from third-party providers under data use agreements that prohibit child data;
- Publicly available academic datasets that do not include data from minors.

No Child-Created Content, even after aggregation or transformation, is used in moderation model training.

### 3.4 Third-Party AI Providers

This prohibition applies to all Bhapi staff, employees, contractors, and third-party service providers. Bhapi's contracts with third-party AI and content processing vendors explicitly prohibit those vendors from using Child-Created Content for model training. Vendors who breach this contractual obligation will be terminated and, where applicable, reported to relevant data protection authorities.

### 3.5 Audit and Enforcement

Bhapi maintains an internal AI data governance log that records:

- All datasets used in AI model training or evaluation;
- Contractual confirmations from third-party vendors that child data is excluded;
- Annual internal audits of data flows to verify compliance with this prohibition.

Audit logs are available to regulators upon lawful request.

---

## 4. AI-Generated Content (Phase 3)

> **Implementation Note:** Bhapi AI Creative Tools are planned for Phase 3. This section applies when those features are released. Date: TBD.

### 4.1 Ownership of AI-Generated Output

Content generated by Bhapi's AI creative tools ("AI-Generated Content") in response to a child's prompt or input is **licensed to the child (via the parent or guardian) for personal, non-commercial use**. Bhapi does not claim ownership of AI-Generated Content.

### 4.2 AI Provider Terms

Bhapi's AI creative tools are powered by third-party large language model (LLM) providers, which may include Anthropic, OpenAI, and Google. The terms and policies of these providers apply to the output generated by their models. Parents and guardians are encouraged to review the relevant provider policies:

- Anthropic: [https://www.anthropic.com/legal/consumer-usage-policy](https://www.anthropic.com/legal/consumer-usage-policy)
- OpenAI: [https://openai.com/policies/usage-policies](https://openai.com/policies/usage-policies)
- Google: [https://policies.google.com/terms/generative-ai](https://policies.google.com/terms/generative-ai)

### 4.3 No Bhapi Ownership Claim

Bhapi does not assert any intellectual property rights over AI-Generated Content. The child and parent or guardian may use, modify, share (within the platform), and delete AI-Generated Content as they would any other Child-Created Content.

### 4.4 Moderation of AI-Generated Content

AI-Generated Content is subject to the same content moderation pipeline as user-created content. Content that violates Bhapi's community guidelines will be removed regardless of whether it was created by the child directly or generated by an AI tool.

### 4.5 Transparency Disclosure

AI-Generated Content will be labeled as such within the platform interface. Bhapi is committed to transparency in AI use in compliance with the EU AI Act (Regulation (EU) 2024/1689) requirements for AI-generated content identification.

---

## 5. Third-Party Content Processing

### 5.1 Why Third Parties Process Child Content

Bhapi uses a small number of specialist third-party providers to operate safety-critical functions that cannot reasonably be performed in-house. Each provider is bound by a data processing agreement that limits use to the stated purpose, prohibits secondary use of child data, and requires deletion of data after processing.

### 5.2 Provider List

| Provider | Parent Company | Purpose | Data Type | Retention |
|----------|---------------|---------|-----------|-----------|
| Cloudflare R2 / Images / Stream | Cloudflare, Inc. | Media storage and global delivery | Images, video, audio | Until deletion request |
| Hive Moderation | The Hive | AI-based content safety classification (images and video) | Images, video frames | Processing only — not retained |
| Sensity AI | Sensity AI B.V. | Deepfake and synthetic media detection | Images, video frames | Processing only — not retained |
| PhotoDNA | Microsoft Corporation | CSAM hash-matching detection (legal obligation) | Image hashes only (not raw content) | Hash logs per NCMEC retention requirements |
| Google Cloud AI (Vision / Natural Language) | Google LLC | Text and image safety classification | Text, images | Processing only — not retained |

### 5.3 Separate Parental Consent

In accordance with COPPA 2026 requirements for children under 13, Bhapi obtains **separate, specific parental consent** for each third-party provider listed in Section 5.2 before child content is processed by that provider. Consent is:

- Granular — parents may consent to individual providers;
- Revocable — parents may withdraw consent at any time from the Privacy Dashboard;
- Recorded — Bhapi maintains a timestamped consent log per child account.

Where a parent refuses consent for a safety-critical provider (e.g., PhotoDNA for CSAM detection), Bhapi may restrict the child's access to content upload features, as operation without CSAM detection is not lawfully permissible.

### 5.4 No Advertising Use

None of the third-party providers listed in Section 5.2 are permitted to use child content for advertising targeting, behavioral profiling, or any purpose other than the specific safety function described.

---

## 6. Content Removal Rights

### 6.1 Right to Delete — Child and Parent

A child (where age-appropriate) or the child's parent or guardian may delete any piece of Child-Created Content at any time through:

- The in-app delete function on any content item;
- The Privacy Dashboard (available to parents via Bhapi Safety);
- A written deletion request submitted to privacy@bhapi.ai.

Deletion requests are processed immediately for platform-visible content. CDN purge and database hard delete follow the schedule in Section 7.

### 6.2 Platform-Initiated Removal

Bhapi may remove content that:

- Violates Bhapi's Community Guidelines;
- Is flagged as harmful, illegal, or age-inappropriate by automated safety systems;
- Is reported by another user or parent and confirmed to violate guidelines upon review;
- Is required to be removed by law or regulatory order.

Platform-initiated removal does not affect the child's underlying ownership of the content. Where technically feasible, the parent or guardian will be provided with a copy of removed content on request, unless retention is prohibited by law (e.g., CSAM content under Section 8).

### 6.3 Moderation Appeals

Parents and guardians may appeal content moderation decisions that they believe were made in error. The appeals process is as follows:

1. Submit an appeal via the moderation appeals portal within **14 days** of the removal notification;
2. Appeals are reviewed by a human moderator within **5 business days**;
3. The decision (uphold or overturn) is communicated with a brief explanation;
4. A second-level appeal to the Bhapi Trust and Safety team is available within **7 days** of the first-level decision;
5. Second-level decisions are final within the platform appeals process but do not affect statutory rights to complain to regulators.

### 6.4 CDN Purge Timeline

Upon deletion (by user or by platform):

- **Immediate:** Content removed from platform display and user access;
- **Within 72 hours:** Content purged from Cloudflare CDN edge cache and Cloudflare R2 storage;
- **Within 30 days:** Content hard-deleted from Bhapi's primary database;
- **Within 90 days:** Content purged from encrypted backup archives.

---

## 7. Data Retention

### 7.1 Governing Policies

Data retention periods for Child-Created Content are determined by the strictest applicable requirement across COPPA (US), GDPR (EU), the UK GDPR, the Australian Privacy Act 1988, and Brazil's LGPD. Where jurisdictional requirements differ, Bhapi applies the shorter retention period by default.

### 7.2 Retention Periods by Content Type

| Content Type | Active Retention | Post-Deletion Archive | Hard Delete |
|--------------|-----------------|----------------------|-------------|
| Text posts and comments | Duration of account | 30-day recovery window | Day 30 |
| Private messages | Duration of account | 30-day recovery window | Day 30 |
| Images and videos | Duration of account | CDN: 72 hours; DB: 30 days | Day 30 |
| Audio recordings | Duration of account | CDN: 72 hours; DB: 30 days | Day 30 |
| Moderation logs | 2 years (legal basis: legitimate interest / legal obligation) | N/A | Year 2 |
| Consent records | Duration of account + 3 years | N/A | Year 3 post-deletion |
| Safety incident records | As required by applicable law (minimum 1 year) | Per legal hold | Per legal hold |

### 7.3 Account Deletion

When a parent or guardian requests full account deletion:

1. The account is immediately deactivated and the child loses access;
2. A **30-day recovery window** begins — the account can be restored within this period on request;
3. After 30 days, hard deletion of all content and personal data is initiated;
4. Media files are purged from Cloudflare R2 within 72 hours of the end of the recovery window;
5. Database records are hard-deleted within 30 days of the end of the recovery window;
6. Encrypted backup archives are purged on the next backup rotation cycle, not to exceed 90 days.

### 7.4 Backup Retention

Encrypted backups are retained for up to 90 days for disaster recovery purposes. Backup data is encrypted at rest (AES-256) and access is restricted to a limited set of Bhapi engineering personnel. Backup data is not used for any purpose other than system recovery.

### 7.5 Legal Holds

Where Bhapi receives a lawful request (court order, regulatory direction, or law enforcement request) to preserve specific data, a legal hold will be applied regardless of the standard retention schedule. Legal holds are logged and reviewed quarterly. Data subject to a legal hold will not be deleted until the hold is lifted.

---

## 8. CSAM Exception

### 8.1 Legal Obligation

The detection, reporting, and preservation of child sexual abuse material (CSAM) is a legal obligation in all jurisdictions where Bhapi operates. In the United States, this obligation arises under 18 U.S.C. § 2258A (PROTECT Our Children Act), which requires electronic service providers to report apparent CSAM to the National Center for Missing and Exploited Children (NCMEC).

**This Section 8 operates as an exception to all other content removal and retention provisions in these Terms, including Sections 6 and 7.**

### 8.2 Preservation on Account Deletion

Content that has been flagged and confirmed (or reasonably suspected) as CSAM **will not be deleted** upon account deletion or upon a content removal request. Such content will be preserved in an encrypted, access-restricted environment for the purpose of:

- Fulfilling mandatory reporting obligations to NCMEC and/or law enforcement;
- Supporting law enforcement investigations;
- Complying with any legal hold or court order.

This preservation obligation continues regardless of:

- The parent's or guardian's deletion request;
- The standard retention schedules set out in Section 7;
- Any other provision of these Terms.

### 8.3 Handling Procedures

Confirmed or suspected CSAM content is handled under strict protocols:

- **Detection:** PhotoDNA hash-matching (Microsoft) and Hive/Sensity image classifiers are used for automated detection. Positive matches trigger immediate quarantine;
- **Quarantine:** Flagged content is immediately removed from user-accessible areas and placed in an encrypted, access-controlled quarantine environment;
- **Human Review:** A designated Trust and Safety specialist reviews flagged content. Analysts are supported by counseling resources and are subject to mandatory exposure limits;
- **Reporting:** Confirmed CSAM is reported to NCMEC via CyberTipline within 24 hours of confirmation, as required by 18 U.S.C. § 2258A;
- **Law Enforcement:** Where required, Bhapi cooperates with law enforcement requests in accordance with applicable law and Bhapi's Law Enforcement Response Policy;
- **Access Restriction:** Quarantined CSAM content is accessible only to designated Trust and Safety personnel and, through lawful process, to law enforcement. No other Bhapi staff have access.

### 8.4 Notification to Parents

Where a CSAM report has been made, Bhapi may be legally prohibited from notifying the account holder (parent or guardian). Bhapi follows the guidance of NCMEC and law enforcement regarding any such notification restrictions.

---

## 9. Jurisdiction-Specific Provisions

### 9.1 United States — COPPA

**Applicable to users in the United States, and to all users under 13 globally.**

- **Verifiable Parental Consent (VPC):** Before any personal data or content from a child under 13 is collected, Bhapi obtains verifiable parental consent using methods approved by the FTC. Consent is obtained separately for each material data practice.
- **COPPA 2026 Compliance:** Bhapi's consent framework complies with the updated COPPA Rule effective April 22, 2026, including consent for push notifications, third-party data sharing, and AI feature engagement.
- **Right to Refuse Partial Collection:** Parents may consent to Bhapi's internal use of child data while refusing to consent to disclosure of that data to third parties. Refusal of third-party disclosure may limit access to certain content upload features (see Section 5.3).
- **Parental Review:** Parents have the right to review all personal information collected from their child and request its deletion at any time.
- **No Behavioral Advertising:** Bhapi does not engage in behavioral advertising targeted at children under 13 in the United States.

### 9.2 European Union — GDPR

**Applicable to users in EU member states.**

- **Parental Consent Age:** The GDPR permits EU member states to set the digital consent age between 13 and 16. Bhapi applies the age of **16** as a conservative default, with parental consent required for all users under 16 in the EU, unless a member state has set a lower age (minimum 13) and the parent has confirmed residence in that state.
- **Right to Erasure (Article 17):** Parents and children (where age-appropriate) have the right to request erasure of personal data. Erasure requests are processed within 30 days. Exceptions apply under Article 17(3) (legal obligation, legal claims, public interest).
- **Data Portability (Article 20):** Parents may request a machine-readable export of the child's personal data and content in a structured, commonly used format (JSON).
- **Legal Basis:** Processing of child content for safety purposes is based on compliance with a legal obligation (Article 6(1)(c)) and, for optional features, explicit parental consent (Article 6(1)(a)).
- **EU Representative:** [To be appointed — required under GDPR Article 27 where applicable.]
- **EU AI Act:** Bhapi's AI-powered safety systems comply with the EU AI Act (Regulation (EU) 2024/1689), including transparency obligations for AI-generated content and human oversight of high-risk AI decisions.

### 9.3 United Kingdom — UK AADC / UK GDPR

**Applicable to users in the United Kingdom.**

- **UK Children's Code (AADC):** Bhapi is designed to meet all 15 standards of the Age Appropriate Design Code, including privacy by default, data minimization, no nudge techniques, no profiling by default, and age-appropriate language.
- **Privacy by Default:** The highest privacy settings are applied by default for child users. Parents must actively adjust settings to reduce protections; settings may not be reduced below the minimum required by the Code.
- **No Nudge Techniques:** Bhapi does not use design features that encourage children to weaken their privacy protections or to share more data than necessary.
- **Age Estimation:** Where required, Bhapi uses age estimation technology calibrated to provide a high level of confidence, consistent with ICO guidance.
- **UK GDPR:** UK GDPR rights (access, rectification, erasure, portability, restriction, objection) apply to all UK users. Data Protection Impact Assessments (DPIAs) have been completed for high-risk processing activities.
- **ICO Registration:** [Registration number to be inserted — required for UK data controllers.]

### 9.4 Australia — Online Safety Act

**Applicable to users in Australia.**

- **Online Safety Act 2021 Compliance:** Bhapi complies with the Online Safety Act 2021 (Cth), including the Basic Online Safety Expectations (BOSE) and any applicable Online Safety Codes.
- **eSafety Commissioner Reporting:** Bhapi has established procedures for reporting seriously harmful content to the eSafety Commissioner as required under the Act. Bhapi will comply with removal notices issued by the Commissioner within the required timeframes.
- **Age Verification:** Bhapi implements age assurance measures consistent with requirements published by the eSafety Commissioner and the Online Safety (Restricted Access System) Declaration.
- **Australian Privacy Act 1988:** Bhapi complies with the Australian Privacy Principles (APPs) under the Privacy Act 1988 (Cth), including APP 8 requirements for cross-border disclosure of personal information.
- **Australian Privacy Act Reform:** Bhapi monitors and will implement requirements arising from the Privacy and Other Legislation Amendment Act 2024 as they take effect.

### 9.5 Brazil — LGPD

**Applicable to users in Brazil.**

- **Lei Geral de Proteção de Dados (LGPD):** Bhapi's processing of child data in Brazil is based on specific consent of the parent or legal guardian (Article 14(1) LGPD).
- **Data Minimization:** Bhapi collects only the minimum personal data necessary from Brazilian child users for the stated purpose. Collection of non-essential data requires separate, specific consent.
- **Parental Consent:** Consent is collected in plain, accessible language. Parents are informed of the specific data practices for which consent is sought. Consent records are maintained and available to the Autoridade Nacional de Proteção de Dados (ANPD) upon request.
- **Data Subject Rights:** Brazilian users have rights of access, correction, anonymization, portability, deletion, and revocation of consent under LGPD. Requests are processed within 15 days.
- **DPO Appointment:** [Data Protection Officer to be appointed — LGPD compliance requirement where applicable.]

---

## 10. Changes to These Terms

### 10.1 Notification of Material Changes

Bhapi will provide **30 days' advance notice** before any material change to these Terms takes effect. Notice will be provided by:

- Email to the parent or guardian's registered email address;
- In-app notification in the Bhapi Safety app;
- A notice banner on the Bhapi platform login page.

A "material change" includes any change to the content ownership provisions (Section 2), the no-training prohibition (Section 3), third-party content processors (Section 5), content removal rights (Section 6), or data retention periods (Section 7).

### 10.2 Acceptance of Changes

The parent or guardian's continued use of the Bhapi platform after the 30-day notice period constitutes acceptance of the updated Terms. Where a material change is introduced, Bhapi will request explicit re-acceptance (click-through confirmation) from the parent or guardian at their next login following the effective date.

### 10.3 Right to Reject Changes

If a parent or guardian does not agree to a material change to these Terms, they may delete the child's account before the effective date. Account deletion before the effective date will be processed without any penalty. The rights and obligations under the previous version of the Terms will govern any outstanding matters as of the date of deletion.

### 10.4 Non-Material Changes

Bhapi may update these Terms without 30 days' notice for non-material changes, such as corrections of typographical errors, clarifications that do not alter the substance of any provision, or updates to contact information. Non-material changes will be noted in the version history below.

### 10.5 Version History

| Version | Date | Summary | Status |
|---------|------|---------|--------|
| 0.1 | March 19, 2026 | Initial draft for legal review | DRAFT |

---

## Contact and Complaints

**Privacy inquiries:** privacy@bhapi.ai

**Trust and Safety:** safety@bhapi.ai

**Moderation appeals:** appeals@bhapi.ai

**Law enforcement requests:** law-enforcement@bhapi.ai (see Law Enforcement Response Policy)

**Postal address:** [To be inserted — registered office address required]

**US COPPA inquiries:** In addition to contacting Bhapi, US parents may file a complaint with the Federal Trade Commission at reportfraud.ftc.gov.

**UK ICO complaints:** UK users may complain to the Information Commissioner's Office at ico.org.uk/make-a-complaint.

**EU supervisory authority:** EU users may contact their national data protection supervisory authority. A list is available at edpb.europa.eu.

**Australian complaints:** Australian users may contact the Office of the Australian Information Commissioner at oaic.gov.au or the eSafety Commissioner at esafety.gov.au.

**Brazilian complaints:** Brazilian users may contact the Autoridade Nacional de Proteção de Dados (ANPD) at gov.br/anpd.

---

*This document is a draft prepared for internal review and legal counsel review only. It does not constitute legal advice and must not be treated as final or legally binding. All provisions must be reviewed and approved by qualified legal counsel in each applicable jurisdiction before publication.*

**Document classification:** INTERNAL DRAFT — PRIVILEGED AND CONFIDENTIAL
