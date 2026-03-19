# Australian Online Safety Compliance Analysis

| Field | Value |
|-------|-------|
| **Document** | Australian Online Safety Act + Social Media Minimum Age Bill Analysis |
| **Date** | 2026-03-19 |
| **Status** | Research --- Requires Legal Review |
| **Author** | Bhapi Platform Team |
| **Version** | 1.0 |
| **Applicable Products** | Bhapi Social (Phase 2), Bhapi Safety (Phase 1) |

---

## Table of Contents

1. [Online Safety Act 2021 (Australia)](#1-online-safety-act-2021-australia)
2. [Social Media Minimum Age Act 2024](#2-social-media-minimum-age-act-2024)
3. [Exemption Analysis for Bhapi Social](#3-exemption-analysis-for-bhapi-social)
4. [Fallback Plan (If Exemption Denied)](#4-fallback-plan-if-exemption-denied)
5. [Technical Requirements for Australian Compliance](#5-technical-requirements-for-australian-compliance)
6. [Timeline](#6-timeline)

---

## 1. Online Safety Act 2021 (Australia)

The Online Safety Act 2021 was passed by the Australian Parliament on 23 June 2021 and came fully into force on **23 January 2022**. It replaced the Enhancing Online Safety Act 2015 and significantly expanded the regulatory powers of the eSafety Commissioner, Australia's independent online safety regulator.

### 1.1 Basic Online Safety Expectations (BOSE)

The Basic Online Safety Expectations (BOSE) are a key element of the Online Safety Act established under **Part 4 of the Act**. They set minimum safety expectations for providers of online services accessible to Australians.

**Scope:** BOSE applies to Social Media Services, Relevant Electronic Services, and Designated Internet Services. This includes social media platforms, messaging services, gaming services, file sharing services, and apps accessible from Australia.

**Key expectations include:**
- Take reasonable steps to ensure the safety of end-users
- Implement mechanisms for reporting and handling complaints
- Provide clear terms of service regarding prohibited content
- Take proactive measures to minimise harmful material (especially child sexual exploitation material)
- Respond to eSafety Commissioner reporting notices in a timely manner
- Designate a contact point for eSafety communications

**Enforcement model:** Compliance with BOSE is not mandatory per se --- the eSafety Commissioner cannot directly penalise non-compliance with the expectations themselves. However, eSafety **can issue reporting notices** requiring providers to report on how they are meeting the expectations. Failure to respond to a reporting notice is enforceable and backed by civil penalties. The Phase 2 industry codes, which took effect on **9 March 2026**, further strengthen these obligations.

**Relevance to Bhapi:** Both Bhapi Social and Bhapi Safety would likely qualify as "Relevant Electronic Services" under the Act. BOSE compliance should be assumed for any service accessible to Australian users.

### 1.2 Cyberbullying Takedown Scheme

The eSafety Commissioner administers a complaints-based cyberbullying takedown scheme under **Part 3 of the Act**.

**How it works:**
1. An Australian child (or their parent/guardian) reports serious cyberbullying material to the eSafety Commissioner
2. The Commissioner investigates whether the material meets the threshold of "serious cyberbullying material" --- material that is likely to have a seriously threatening, seriously intimidating, seriously harassing, or seriously humiliating effect on the target
3. If the threshold is met, the Commissioner can issue a **removal notice** to the platform or service provider
4. The provider must remove the material **within 24 hours** of receiving the notice (reduced from the previous 48-hour window)
5. The Commissioner can also issue end-user notices directly to the person who posted the material

**Scope:** The scheme covers the full range of online services used by children including social media platforms, games, websites, and messaging services.

**Adult cyber-abuse scheme:** The Act also introduced a world-first adult cyber-abuse scheme (Part 3, Division 2), enabling complaints about cyber-abuse material targeted at an adult ordinarily resident in Australia.

### 1.3 Image-Based Abuse Reporting Requirements

The Image-Based Abuse (IBA) scheme is established under **Part 6 of the Act**.

**Definition:** Image-based abuse is the sharing, or threatening to share, an intimate image or video of a person without their consent. This includes AI-generated deepfake intimate images.

**Reporting process:**
- The person depicted in the intimate image, their parent or guardian, or an authorised representative can report to eSafety
- eSafety can issue removal notices to platforms requiring takedown of the material
- Platforms must comply within **24 hours**

**Penalties for perpetrators:**
- Individuals who post intimate images without consent (including deepfakes) face civil penalties of up to **AUD $111,000**
- Platforms that fail to remove material after receiving a removal notice face penalties of up to **AUD $555,000**

**Effectiveness:** Between August 2018 and June 2023, eSafety sent 1,961 removal requests and achieved successful removal (all or some material) in **89.9%** of cases.

### 1.4 eSafety Commissioner Powers and Reporting Obligations

The eSafety Commissioner has broad regulatory powers under the Act:

| Power | Description | Reference |
|-------|-------------|-----------|
| **Removal notices** | Require removal of cyberbullying, cyber-abuse, or image-based abuse material | Parts 3, 6 |
| **Link deletion notices** | Require search engines to de-index harmful content | Part 9 |
| **App removal notices** | Require app stores to remove apps that facilitate harmful conduct | Part 9 |
| **Reporting notices** | Require service providers to report on BOSE compliance | Part 4 |
| **Investigation powers** | Investigate complaints and gather information from providers | Part 13 |
| **Industry codes/standards** | Register or determine binding industry codes and standards | Part 9 |

**Reporting obligations for service providers:**
- Respond to BOSE reporting notices within specified timeframes
- Designate a contact point for eSafety communications (updated February 2026 to include email notification)
- Comply with registered industry codes (Phase 2 codes effective 9 March 2026)
- Maintain records of content moderation actions

### 1.5 Content Takedown Requirements

**24-hour SLA:** Any online service provider (OSP) issued with a removal notice must remove the offending content **within 24 hours**, unless the Commissioner specifies a longer period. This applies to:

- Social media services
- Relevant electronic services
- Designated internet services
- Hosting services
- App distribution services

**Practical requirement:** Providers must have effective mechanisms in place that allow content removal to be completed within the 24-hour timeframe. This means:
- 24/7 moderation capability or on-call escalation
- Automated detection and flagging systems
- Clear internal escalation procedures
- Documented takedown workflows with audit trails

### 1.6 Penalties for Non-Compliance

| Violation | Individual Penalty | Corporate Penalty |
|-----------|-------------------|-------------------|
| Failure to comply with removal notice | AUD $111,000 | AUD $555,000 |
| Failure to comply with reporting notice | Civil penalties apply | Civil penalties apply |
| Posting intimate images without consent | AUD $111,000 | N/A |
| Breach of registered industry code | Civil penalties apply | Civil penalties apply |

Penalties are civil (not criminal) and are enforced through the Federal Court of Australia.

---

## 2. Social Media Minimum Age Act 2024

The **Online Safety Amendment (Social Media Minimum Age) Act 2024** was passed by the Parliament of Australia on **29 November 2024** and received Royal Assent in December 2024. It amends the Online Safety Act 2021 to introduce a minimum age of 16 for social media account holders.

### 2.1 Under-16 Ban --- Scope and Definitions

**Core prohibition:** Age-restricted social media platforms must take "reasonable steps" to prevent Australians under 16 from creating or holding an account.

**Definition of "age-restricted social media platform" (Section 63C of the amended Act):**

An electronic service is an age-restricted social media platform if ALL of the following criteria are met:

1. The **sole or a significant purpose** of the service is to enable online social interaction between two or more end-users
2. The service allows end-users to **link to, or interact with**, some or all of the other end-users
3. The service allows end-users to **post material** on the service
4. Any other conditions set out in the legislative rules are satisfied

A service is **not** an age-restricted social media platform if none of the material on the service is accessible to, or delivered to, end-users in Australia.

### 2.2 Platforms Designated as Age-Restricted

The following platforms were designated as age-restricted on **10 December 2025**:

- Facebook
- Instagram
- Reddit
- Snapchat
- TikTok
- X (formerly Twitter)
- Threads
- Twitch
- Kick
- YouTube

Additional platforms may be added by legislative rules at any time.

### 2.3 Exemptions

The following categories of services are explicitly **exempt** from the age-restriction:

| Exempt Category | Examples |
|----------------|----------|
| Messaging apps | WhatsApp, iMessage, Signal |
| Educational tools | Google Classroom, Canvas |
| Health services | Telehealth platforms, mental health apps |
| Some gaming platforms | Discord, Roblox |
| Children's versions | YouTube Kids |

**Key exemption criteria:**
- The primary purpose of the service is **not** social interaction (even if social features exist)
- The service falls into a specifically exempt category defined in legislative rules
- The service is not accessible to Australian end-users

**Important nuance:** The legislation distinguishes between services where social interaction is the *sole or significant purpose* versus services where social features are ancillary to a primary non-social purpose (e.g., education, safety monitoring, health).

### 2.4 Age Verification Requirements

The Act places the obligation on **platforms**, not on individual users or parents:

- Platforms must take **"reasonable steps"** to prevent under-16 accounts
- Platforms must also identify and **remove existing accounts** held by under-16 Australians
- If a platform collects government-issued ID for age verification, it **must also provide alternative methods** not dependent on the user having ID
- Age verification data must be **deleted immediately** after verification
- Verification data **cannot be used** for profiling or advertising
- The approach is **systemic** (platform-level obligation), not per-user (no individual penalties for minors or parents)

### 2.5 Enforcement Timeline and Penalties

| Date | Milestone |
|------|-----------|
| 29 November 2024 | Bill passed by Parliament |
| December 2024 | Royal Assent received |
| 10 December 2025 | Provisions took effect; initial 10 platforms designated |
| Ongoing | Additional platforms may be designated by legislative rules |

**Penalties:**
- Courts can impose fines of up to **150,000 penalty units** for corporations
- At current penalty unit values, this equates to **AUD $49.5 million**
- **No penalties** for under-16s who access age-restricted platforms
- **No penalties** for parents or carers

### 2.6 Current Legislative Status

As of March 2026, the Act is **in force**. The initial 10 platforms have been designated. The eSafety Commissioner oversees compliance and may recommend additional platform designations. Enforcement is active.

---

## 3. Exemption Analysis for Bhapi Social

This section analyses whether **Bhapi Social** (the social/community features planned for Phase 2) would be classified as an "age-restricted social media platform" under the Social Media Minimum Age Act 2024.

### 3.1 Arguments FOR Exemption

Bhapi Social has strong arguments that its primary purpose is **child safety and education**, not social interaction:

| Argument | Supporting Evidence |
|----------|-------------------|
| **Safety-first platform** | The platform's primary purpose is AI safety monitoring for families, schools, and clubs --- not social networking. Social features are ancillary to the safety mission. |
| **Educational purpose** | The platform includes AI literacy modules, safety education content, and academic integrity monitoring. Educational tools are explicitly exempt from the Act. |
| **Parental oversight built-in** | All child accounts require parental consent and are subject to parental monitoring. This is fundamentally different from mainstream social media where children operate independently. |
| **COPPA and GDPR compliant** | The platform already meets stringent US (COPPA 2026) and EU (GDPR) child protection standards, demonstrating a safety-first approach. |
| **Content pre-moderated for under-13** | All content for children under 13 goes through a consent-gated risk pipeline with keyword filtering and AI safety scoring. |
| **Analogous to exempt services** | The platform is more analogous to Google Classroom (exempt) or a parental control app than to Instagram or TikTok. |
| **No algorithmic engagement optimization** | Unlike age-restricted platforms, Bhapi Social does not use engagement-maximizing algorithms, infinite scroll, or addictive design patterns. |
| **Family agreement requirement** | Children under 13 cannot use capture/monitoring features without a signed Family Agreement, adding another layer of structured oversight. |

### 3.2 Arguments AGAINST Exemption

However, Bhapi Social does include features that could bring it within the Act's definition:

| Argument | Risk Factor |
|----------|------------|
| **Social feed** | Bhapi Social includes a content feed where users can view posts --- this meets the "post material" criterion in Section 63C. |
| **Messaging** | Direct messaging between users meets the "online social interaction" criterion. |
| **Following/connections** | The ability to follow other users meets the "link to, or interact with, other end-users" criterion. |
| **User-generated content** | Users can create and share content, which is a core characteristic of social media under the Act. |
| **Functional test, not intent test** | The Act uses a functional definition (what the service *does*), not an intent-based definition (what the service is *for*). Even if Bhapi's intent is safety, the functional characteristics could classify it as social media. |
| **"Significant purpose" threshold** | If social interaction is deemed a "significant purpose" of the service (even if not the sole purpose), the platform could be caught by the definition. The threshold for "significant" has not yet been tested by courts. |
| **Regulatory caution** | The eSafety Commissioner may take a broad interpretation of the definition to avoid creating loopholes that mainstream social media platforms could exploit. |

### 3.3 Risk Assessment

| Factor | Assessment |
|--------|-----------|
| **Likelihood of being classified as age-restricted** | **Medium** --- The functional definition is broad enough to capture Bhapi Social, but the safety/educational purpose and parental oversight model differentiate it significantly from designated platforms. |
| **Severity if classified** | **High** --- Would require blocking all under-16 Australian users from social features, significantly impacting the platform's value proposition for families. Penalties of up to AUD $49.5 million for non-compliance. |
| **Overall risk** | **Medium-High** --- The ambiguity in the legislation warrants proactive legal engagement rather than assumption of exemption. |

### 3.4 Recommendation

**Engage Australian legal counsel before Phase 2 launch to confirm Bhapi Social's status under the Act.**

Specifically:
1. Obtain a formal legal opinion on whether Bhapi Social meets the Section 63C definition of an "age-restricted social media platform"
2. If the opinion is ambiguous, proactively engage with the eSafety Commissioner to seek clarification or a formal exemption/no-action letter
3. If needed, explore whether Bhapi Social can be structured to fall outside the definition (e.g., by making social features opt-in modules rather than core platform functionality, or by limiting social features to family-group-only interactions that do not meet the "linking to other end-users" criterion)
4. Document the platform's safety-first design, parental oversight model, and educational purpose to support any exemption application
5. Monitor the eSafety Commissioner's designation of additional platforms for signals about how broadly the definition is being interpreted

**Do not assume exemption. Plan for the fallback scenario (Section 4) in parallel.**

---

## 4. Fallback Plan (If Exemption Denied)

If Australian legal counsel determines that Bhapi Social would be classified as an age-restricted social media platform, or if the eSafety Commissioner designates it as such, the following fallback plan applies.

### 4.1 Jurisdiction-Based Age Gating

**Bhapi Social serves 16+ in Australia only.** All other jurisdictions retain their existing age policies.

Implementation via the existing `age_tier_configs.jurisdiction` column:

```
jurisdiction: "AU"
social_minimum_age: 16
safety_minimum_age: null  (no minimum -- safety app available for all ages)
verification_required: true
verification_provider: "yoti"
enforcement_mode: "hard_block"
```

### 4.2 Product Separation

| Product | Australian Availability | Age Restriction |
|---------|------------------------|-----------------|
| **Bhapi Safety** (monitoring, risk detection, alerts, parental dashboard) | Available for all ages | None --- this is a safety/monitoring tool, not social media |
| **Bhapi Social** (feed, messaging, following, community features) | 16+ only in Australia | Hard block with mandatory Yoti age verification |

**Rationale:** Bhapi Safety is a parental monitoring and AI safety tool. It does not meet the Section 63C definition because:
- Its purpose is safety monitoring, not social interaction
- Parents/guardians are the primary users, not children
- Children do not "link to or interact with" other end-users through the safety product
- It is analogous to parental control software, which is not social media

### 4.3 Technical Implementation

1. **IP geolocation:** Use MaxMind GeoIP2 (already available in infrastructure) to detect Australian users at registration and login
2. **Yoti mandatory age verification:** Extend existing Yoti integration with an AU-specific flow that requires age verification before enabling any social features
3. **Jurisdiction column enforcement:** The `age_tier_configs.jurisdiction` column gates feature access at the API level --- Australian users under 16 receive `403 Forbidden` for all social endpoints
4. **Graceful degradation:** Under-16 Australian users see the Bhapi Safety product only, with a clear explanation that social features are not available in their jurisdiction due to Australian law
5. **VPN detection:** Implement basic VPN/proxy detection to prevent trivial circumvention (note: the Act requires "reasonable steps," not perfect enforcement)

### 4.4 Impact Assessment

| Jurisdiction | Impact |
|-------------|--------|
| Australia | Under-16 users lose social features; safety features unaffected |
| United States | No impact (COPPA governs, existing age tiers apply) |
| European Union | No impact (GDPR/DSA governs, existing age tiers apply) |
| United Kingdom | No impact (UK Online Safety Act governs separately) |
| Rest of world | No impact |

---

## 5. Technical Requirements for Australian Compliance

### 5.1 Implementation Matrix

| Requirement | Implementation | Phase | Priority | Effort |
|-------------|---------------|-------|----------|--------|
| **Yoti age verification (mandatory for AU)** | Extend existing Yoti integration with AU-specific flow. Add `jurisdiction` parameter to verification request. Enforce verification before social feature access for Australian users. | P1 | Critical | Medium |
| **eSafety Commissioner automated reporting** | Build API integration for submitting incident reports to eSafety. Include cyberbullying, image-based abuse, and illegal content categories. Maintain audit trail of all reports. | P1 | Critical | High |
| **24h content takedown SLA** | Add SLA monitoring to moderation queue. Implement countdown timer from report receipt. Alert on-call moderator at 12h, 18h, 22h marks. Auto-escalate to platform admin at 23h. Dashboard for SLA compliance metrics. | P1 | Critical | Medium |
| **Cyberbullying rapid-response workflow** | Automated escalation for cyberbullying reports. AI-assisted classification of report severity. Priority queue for Australian child reports. Template-based response to eSafety removal notices. | P1 | High | Medium |
| **Image-based abuse reporting** | Integration with eSafety for intimate image takedown requests. Automated hash-matching for known CSAM/IBA material (PhotoDNA or similar). Reporting workflow for AI-generated deepfake intimate images. | P2 | High | High |
| **BOSE compliance reporting** | Maintain records of safety measures, moderation actions, and complaint handling. Prepare template responses for eSafety reporting notices. Designate Australian contact point for eSafety communications. | P1 | Medium | Low |
| **AU jurisdiction age gate** | IP geolocation (MaxMind) + Yoti verification for social feature access. `age_tier_configs.jurisdiction = 'AU'` enforcement. VPN/proxy detection as "reasonable steps." | P1 | Critical | Medium |
| **Phase 2 industry code compliance** | Review and implement requirements of Phase 2 Online Safety Codes (effective 9 March 2026). Map existing safety features to code requirements. Gap analysis and remediation. | P1 | High | Medium |

### 5.2 Architecture Notes

**eSafety reporting integration:**
- No public API currently exists for automated eSafety incident reporting. Manual submission via eSafety's online portal is the current process. Monitor for API availability.
- In the interim, build an internal incident management system that generates eSafety-formatted reports for manual submission, with the architecture designed to support future API integration.

**Age verification flow for Australian users:**
```
Registration/Login
  -> IP Geolocation check
    -> If AU jurisdiction detected:
      -> Require Yoti age verification (mandatory)
      -> If age < 16:
        -> Social features blocked (hard gate)
        -> Safety features available
      -> If age >= 16:
        -> Full platform access
    -> If non-AU jurisdiction:
      -> Standard age tier logic applies
```

**Content takedown SLA monitoring:**
- All content reports receive a timestamp at ingestion
- SLA countdown begins from report receipt, not from review
- Moderation queue sorted by SLA remaining time (most urgent first)
- Automated alerts at configurable thresholds (default: 12h, 18h, 22h)
- Dashboard showing SLA compliance rate, average response time, and breach count

---

## 6. Timeline

### 6.1 Legal Engagement

| Date | Action | Owner |
|------|--------|-------|
| **Q2 2026** | Engage Australian legal counsel specializing in online safety regulation | Legal/Compliance |
| **Q2 2026** | Obtain formal legal opinion on Bhapi Social's classification under Section 63C | Legal counsel |
| **Q3 2026** | If classification is ambiguous: prepare exemption submission materials | Legal counsel + Product |
| **Q3 2026** | If applicable: submit exemption application or request no-action letter from eSafety Commissioner | Legal counsel |
| **Q3 2026** | Receive determination; proceed with either primary plan (exempt) or fallback plan (Section 4) | Legal/Compliance |

### 6.2 Technical Implementation

| Phase | Timeline | Deliverables |
|-------|----------|-------------|
| **Phase 1 (Foundation)** | Q2--Q3 2026 | Yoti AU-specific flow, AU jurisdiction age gate, BOSE compliance records, 24h takedown SLA monitoring, cyberbullying escalation workflow, eSafety contact point designation |
| **Phase 2 (Advanced)** | Q4 2026 | Image-based abuse reporting integration, deepfake detection for IBA, eSafety automated reporting (if API available), VPN/proxy detection, Phase 2 industry code compliance audit |
| **Ongoing** | Continuous | SLA compliance monitoring, regulatory change tracking, annual BOSE compliance review, legal counsel engagement for new eSafety designations |

### 6.3 Key Dependencies

- Australian legal counsel engagement is the **critical path** item --- all other decisions depend on the exemption analysis outcome
- Yoti integration already exists in the platform (COPPA 2026 compliance); AU-specific flow is an extension, not a new build
- eSafety Commissioner may release an API for incident reporting; architecture should be designed for future integration
- Monitor the eSafety Commissioner's website for additional platform designations that could signal how the definition is being interpreted

---

## References

### Legislation
- [Online Safety Act 2021 (Federal Register of Legislation)](https://www.legislation.gov.au/Details/C2021A00076)
- [Online Safety Amendment (Social Media Minimum Age) Act 2024 (Federal Register of Legislation)](https://www.legislation.gov.au/C2024A00127/asmade/text)

### Regulatory Guidance
- [eSafety Commissioner --- Learn about the Online Safety Act](https://www.esafety.gov.au/newsroom/whats-on/online-safety-act)
- [eSafety Commissioner --- Social Media Age Restrictions](https://www.esafety.gov.au/about-us/industry-regulation/social-media-age-restrictions)
- [eSafety Commissioner --- Basic Online Safety Expectations](https://www.esafety.gov.au/industry/basic-online-safety-expectations)
- [eSafety Commissioner --- Industry Regulation](https://www.esafety.gov.au/about-us/industry-regulation)
- [eSafety Commissioner --- Image-Based Abuse Scheme Regulatory Guidance (Feb 2024)](https://www.esafety.gov.au/sites/default/files/2024-02/Image-Based-Abuse-Scheme-Regulatory-Guidance-Feb2024.pdf)
- [eSafety Commissioner --- Report Image-Based Abuse](https://www.esafety.gov.au/key-topics/image-based-abuse/report-image-based-abuse)

### Analysis and Commentary
- [Library of Congress --- Australia: Online Safety Bill Passed](https://www.loc.gov/item/global-legal-monitor/2021-08-10/australia-online-safety-bill-passed/)
- [Library of Congress --- Australia: Social Media Banned for Children Under 16](https://www.loc.gov/item/global-legal-monitor/2024-12-08/australia-social-media-banned-for-children-under-16/)
- [MinterEllison --- Australia enforces minimum age of 16 for social media](https://www.minterellison.com/articles/16-becomes-minimum-age-for-social-media-in-australia)
- [MinterEllison --- The age of reason(able steps)](https://www.minterellison.com/articles/australias-impending-social-media-minimum-age-obligations)
- [Quinn Emanuel --- Australia Sets Minimum Age for Social Media Use](https://www.quinnemanuel.com/the-firm/publications/australia-sets-minimum-age-for-social-media-use-a-closer-look-at-the-online-safety-amendment-social-media-minimum-age-act-2024/)
- [Persona --- Australia's Online Safety Amendment: What Platforms Need to Know](https://withpersona.com/blog/australian-social-media-ban)
- [UNICEF Australia --- Social Media Ban Explainer](https://www.unicef.org.au/unicef-youth/staying-safe-online/social-media-ban-explainer)
- [Department of Infrastructure --- Social Media Minimum Age Bill 2024 Fact Sheet](https://www.infrastructure.gov.au/department/media/publications/online-safety-amendment-social-media-minimum-age-bill-2024-fact-sheet)
- [Parliamentary Education Office --- Online Safety Amendment Act 2024](https://peo.gov.au/understand-our-parliament/history-of-parliament/history-milestones/australian-parliament-history-timeline/events/online-safety-amendment-social-media-minimum-age-act-2024)

---

*This document is for internal planning purposes and does not constitute legal advice. Formal legal review by Australian-qualified counsel is required before any compliance decisions are finalized.*
