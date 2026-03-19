"""Legal document content — privacy policy and terms of service."""

PRIVACY_POLICY = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Privacy Policy — Bhapi</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         max-width: 800px; margin: 0 auto; padding: 2rem; line-height: 1.6; color: #1a1a1a; }
  h1 { font-size: 1.75rem; border-bottom: 2px solid #2563eb; padding-bottom: 0.5rem; }
  h2 { font-size: 1.25rem; margin-top: 2rem; color: #1e40af; }
  h3 { font-size: 1.1rem; margin-top: 1.5rem; }
  table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
  th, td { border: 1px solid #d1d5db; padding: 0.5rem; text-align: left; font-size: 0.9rem; }
  th { background: #f3f4f6; }
  ul { padding-left: 1.5rem; }
  .updated { color: #6b7280; font-size: 0.9rem; }
</style>
</head>
<body>
<h1>Privacy Policy</h1>
<p class="updated">Last updated: 24 February 2026</p>

<h2>1. Data Controller</h2>
<p>Bhapi (&ldquo;we&rdquo;, &ldquo;us&rdquo;, &ldquo;our&rdquo;) operates the bhapi.ai platform.
We are the data controller responsible for your personal data.</p>
<p><strong>Data Protection Officer:</strong> <a href="mailto:dpo@bhapi.ai">dpo@bhapi.ai</a></p>

<h2>2. Data We Collect</h2>
<table>
<tr><th>Category</th><th>Examples</th><th>Purpose</th></tr>
<tr><td>Account data</td><td>Email, display name, account type, hashed password</td>
    <td>Account creation and authentication</td></tr>
<tr><td>Group membership</td><td>Parent-child relationships, roles</td>
    <td>Access control and family/school/club structure</td></tr>
<tr><td>AI interaction metadata</td><td>Platform name, timestamp, session duration</td>
    <td>Usage monitoring and safety analysis</td></tr>
<tr><td>Risk events</td><td>Flagged content categories, severity, PII indicators</td>
    <td>Child safety alerting</td></tr>
<tr><td>Content excerpts</td><td>Partial AI prompts/responses when risk-flagged (PII redacted)</td>
    <td>Guardian review of safety concerns</td></tr>
<tr><td>Spend data</td><td>LLM API costs, provider, token counts</td>
    <td>Budget monitoring and alerts</td></tr>
<tr><td>Billing data</td><td>Subscription plan, payment status (card details held by Stripe)</td>
    <td>Subscription management</td></tr>
</table>

<h2>3. Lawful Basis for Processing</h2>
<ul>
<li><strong>Contract</strong> (GDPR Art. 6(1)(b)): Account data, billing, and service delivery.</li>
<li><strong>Legitimate interest</strong> (GDPR Art. 6(1)(f)): Safety monitoring of children&rsquo;s AI usage
    where the guardian has enrolled the child. We have conducted a balancing test confirming
    that the child&rsquo;s safety interest outweighs the privacy intrusion, given our data
    minimisation measures.</li>
<li><strong>Consent</strong> (GDPR Art. 6(1)(a)): Processing of children&rsquo;s data requires
    verifiable guardian consent, enforced per jurisdiction (see Section 7).</li>
<li><strong>Legal obligation</strong> (GDPR Art. 6(1)(c)): Consent records, audit logs, and data
    retention as required by COPPA, GDPR, and LGPD.</li>
</ul>

<h2>4. Data Minimisation</h2>
<p>We follow the principle of data minimisation:</p>
<ul>
<li>Raw AI prompts and responses are <strong>not stored</strong> by default.</li>
<li>Only content flagged by our safety engine is retained, and PII within it is
    automatically redacted before storage.</li>
<li>Content excerpts are automatically deleted after 12 months.</li>
<li>We collect only the minimum data necessary for each stated purpose.</li>
</ul>

<h2>5. Data Retention</h2>
<table>
<tr><th>Data Type</th><th>Retention Period</th></tr>
<tr><td>Risk events and content excerpts</td><td>12 months</td></tr>
<tr><td>Audit log entries</td><td>24 months</td></tr>
<tr><td>Account data</td><td>Until account deletion</td></tr>
<tr><td>Consent records</td><td>Until withdrawal + 6 months</td></tr>
<tr><td>Spend records</td><td>12 months</td></tr>
<tr><td>Session tokens</td><td>24 hours (auto-expiry)</td></tr>
</table>
<p>When you delete your account, all associated data is deleted immediately via cascading
soft-delete, except where retention is required by law.</p>

<h2>6. Your Rights (Data Subject Rights)</h2>
<p>Under GDPR, you have the following rights:</p>
<ul>
<li><strong>Access</strong> (Art. 15): Request a copy of your personal data.</li>
<li><strong>Rectification</strong> (Art. 16): Correct inaccurate personal data.</li>
<li><strong>Erasure</strong> (Art. 17): Request deletion of your personal data (&ldquo;right to be forgotten&rdquo;).</li>
<li><strong>Portability</strong> (Art. 20): Receive your data in a machine-readable format (ZIP export).</li>
<li><strong>Object</strong> (Art. 21): Object to processing based on legitimate interest.</li>
<li><strong>Restrict processing</strong> (Art. 18): Request limitation of processing.</li>
<li><strong>Withdraw consent</strong> (Art. 7(3)): Withdraw consent at any time without affecting
    the lawfulness of prior processing.</li>
</ul>
<p>To exercise these rights, use the compliance features in your dashboard or email
<a href="mailto:dpo@bhapi.ai">dpo@bhapi.ai</a>. We respond within 30 days.</p>

<h2>7. Children&rsquo;s Data</h2>
<p>Bhapi processes children&rsquo;s data for safety monitoring purposes. We comply with:</p>
<ul>
<li><strong>COPPA</strong> (US): Verifiable parental consent required for children under 13.</li>
<li><strong>GDPR Article 8</strong> (EU): Parental consent required for children under 16.</li>
<li><strong>LGPD Article 14</strong> (Brazil): Parental consent required for children under 18.</li>
<li><strong>Australian Privacy Act</strong>: Parental consent required for children under 16.</li>
</ul>
<p>Monitoring cannot begin until the guardian has provided consent for the specific child member.
Consent can be withdrawn at any time, which immediately stops data processing for that member.</p>

<h2>8. International Transfers</h2>
<p>We store data in the region closest to your location where possible:</p>
<ul>
<li>EU user data is stored in EU data centres.</li>
<li>Australian user data is stored in AU data centres.</li>
<li>Where cross-border transfers are necessary, we use Standard Contractual Clauses (SCCs)
    approved by the European Commission.</li>
</ul>

<h2>9. Third Parties</h2>
<table>
<tr><th>Provider</th><th>Purpose</th><th>Data Shared</th></tr>
<tr><td>Stripe</td><td>Subscription billing</td><td>Email, subscription plan (no AI data)</td></tr>
<tr><td>SendGrid</td><td>Transactional email</td><td>Email address, display name</td></tr>
<tr><td>LLM providers (OpenAI, Anthropic, Google, Microsoft)</td>
    <td>Spend data synchronisation</td><td>API credentials only (no user content)</td></tr>
<tr><td>Cloud infrastructure (Render/GCP)</td><td>Hosting</td>
    <td>All data (encrypted at rest, DPA in place)</td></tr>
</table>
<p>We never sell personal data. We never share children&rsquo;s data with advertisers.</p>

<h2>10. Cookies</h2>
<p>We use a single session cookie (<code>bhapi_session</code>) for authentication. This cookie is:</p>
<ul>
<li><strong>HttpOnly</strong>: Not accessible to JavaScript.</li>
<li><strong>Secure</strong>: Only transmitted over HTTPS in production.</li>
<li><strong>SameSite=Lax</strong>: Protected against CSRF attacks.</li>
</ul>
<p>We do not use tracking cookies, analytics cookies, or third-party advertising cookies.</p>

<h2>11. Security</h2>
<p>We protect your data with:</p>
<ul>
<li>Encryption at rest (AES-256) and in transit (TLS 1.2+)</li>
<li>LLM API credentials encrypted with Fernet/Cloud KMS</li>
<li>bcrypt password hashing</li>
<li>Rate limiting and brute-force protection</li>
<li>Multi-tenant data isolation</li>
<li>Annual penetration testing by CREST-certified providers</li>
<li>Immutable audit logging</li>
</ul>

<h2>12. Changes to This Policy</h2>
<p>We will notify you of material changes via email and update the &ldquo;Last updated&rdquo;
date. Continued use of the platform after notification constitutes acceptance.</p>

<h2>13. Contact</h2>
<p>For privacy inquiries: <a href="mailto:dpo@bhapi.ai">dpo@bhapi.ai</a></p>
<p>For general support: <a href="mailto:support@bhapi.ai">support@bhapi.ai</a></p>
</body>
</html>"""


PRIVACY_FOR_CHILDREN = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Your Privacy — Easy Guide — Bhapi</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         max-width: 700px; margin: 0 auto; padding: 2rem; line-height: 1.8; color: #1a1a1a; }
  h1 { font-size: 1.75rem; color: #FF6B35; border-bottom: 3px solid #FF6B35; padding-bottom: 0.5rem; }
  h2 { font-size: 1.35rem; margin-top: 2rem; color: #0D9488; }
  p { font-size: 1.1rem; }
  .section { background: #f9fafb; border-radius: 12px; padding: 1.25rem 1.5rem;
             margin: 1.5rem 0; border-left: 4px solid #0D9488; }
  .updated { color: #6b7280; font-size: 0.9rem; }
  a { color: #0D9488; }
</style>
</head>
<body>
<h1>Your Privacy &mdash; Easy Guide</h1>
<p class="updated">Last updated: 18 March 2026</p>
<p>This page explains what Bhapi does in simple words. If you have questions, ask your parent or guardian.</p>

<div class="section">
<h2>What We Watch</h2>
<p>When you use AI tools like ChatGPT, Gemini, or Claude, Bhapi checks to make sure nothing unsafe is happening.</p>
<p>We see which AI tool you used and when you used it. We do <strong>not</strong> read everything you type.
We only look more closely if something seems unsafe.</p>
</div>

<div class="section">
<h2>Who Can See</h2>
<p>Only your parent or guardian can see your activity. If your school set up Bhapi, your teacher may also see it.</p>
<p>We never show your information to advertisers or strangers. We never sell your data.</p>
</div>

<div class="section">
<h2>Your Rights</h2>
<p>You have the right to:</p>
<ul>
<li>Ask your parent to show you what data we have about you.</li>
<li>Ask your parent to delete your data.</li>
<li>Ask your parent to stop collecting your data at any time.</li>
</ul>
<p>Your parent can do all of this from their Bhapi dashboard or by emailing us.</p>
</div>

<div class="section">
<h2>Need Help?</h2>
<p>If you have questions or something worries you:</p>
<ul>
<li>Talk to your parent or guardian.</li>
<li>Ask them to email <a href="mailto:help@bhapi.ai">help@bhapi.ai</a>.</li>
</ul>
</div>

</body>
</html>"""


TERMS_OF_SERVICE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Terms of Service — Bhapi</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         max-width: 800px; margin: 0 auto; padding: 2rem; line-height: 1.6; color: #1a1a1a; }
  h1 { font-size: 1.75rem; border-bottom: 2px solid #2563eb; padding-bottom: 0.5rem; }
  h2 { font-size: 1.25rem; margin-top: 2rem; color: #1e40af; }
  h3 { font-size: 1.1rem; margin-top: 1.5rem; }
  ul { padding-left: 1.5rem; }
  .updated { color: #6b7280; font-size: 0.9rem; }
</style>
</head>
<body>
<h1>Terms of Service</h1>
<p class="updated">Last updated: 24 February 2026</p>

<h2>1. Service Description</h2>
<p>Bhapi (&ldquo;the Service&rdquo;) is an AI governance platform operated at bhapi.ai. The Service
monitors children&rsquo;s AI tool usage across supported platforms (ChatGPT, Gemini, Copilot,
Claude, Grok) to provide safety alerts, risk analysis, spend tracking, and compliance reporting
for guardians, schools, and clubs.</p>

<h2>2. Eligibility</h2>
<ul>
<li>You must be at least 18 years old to create an account.</li>
<li>Minors may use the Service only as monitored members under a guardian&rsquo;s account.</li>
<li>By creating an account, you represent that you have the legal authority to consent to
    monitoring of the minors you enrol.</li>
<li>Schools and clubs must obtain appropriate parental/guardian consent before enrolling
    minors, in compliance with applicable laws (COPPA, GDPR, LGPD).</li>
</ul>

<h2>3. Account Responsibilities</h2>
<ul>
<li>You are responsible for maintaining the confidentiality of your account credentials.</li>
<li>You must provide accurate and current information.</li>
<li>You must notify us immediately of any unauthorised access to your account.</li>
<li>You are responsible for all activity under your account.</li>
</ul>

<h2>4. Guardian Consent Obligations</h2>
<ul>
<li>As a guardian, you consent to the monitoring of your enrolled members&rsquo; AI interactions
    for safety purposes.</li>
<li>You must inform monitored members that their AI usage is being monitored.</li>
<li>You may withdraw consent at any time, which immediately stops monitoring for the
    affected member.</li>
<li>You are responsible for ensuring your use of monitoring data is lawful and not coercive.</li>
</ul>

<h2>5. Acceptable Use</h2>
<p>You agree to use the Service only for its intended purpose of AI safety monitoring.
You must not:</p>
<ul>
<li>Use the Service for unlawful surveillance or harassment.</li>
<li>Attempt to access data belonging to other users or groups.</li>
<li>Interfere with the Service&rsquo;s security mechanisms, rate limits, or access controls.</li>
<li>Reverse-engineer, decompile, or disassemble any part of the Service.</li>
<li>Use the Service to monitor adults without their informed consent.</li>
<li>Resell, sublicence, or redistribute the Service without written permission.</li>
<li>Submit false, misleading, or malicious data to the platform.</li>
<li>Use automated tools to scrape or bulk-access the Service (except the provided API with
    valid authentication).</li>
</ul>

<h2>6. Prohibited Uses</h2>
<p>The Service must not be used to:</p>
<ul>
<li>Monitor individuals without legal authority or appropriate consent.</li>
<li>Conduct coercive surveillance that violates the monitored person&rsquo;s rights.</li>
<li>Store, transmit, or process illegal content.</li>
<li>Circumvent child protection regulations.</li>
<li>Engage in any activity that violates applicable laws or regulations.</li>
</ul>

<h2>7. Subscription and Billing</h2>
<ul>
<li>The Service offers subscription plans (Family, School, Club) billed monthly or annually
    via Stripe.</li>
<li>All plans include a 14-day free trial.</li>
<li>Prices are displayed in your local currency where available.</li>
<li>Subscriptions renew automatically unless cancelled before the renewal date.</li>
<li>You may cancel your subscription at any time from the billing settings page. Cancellation
    takes effect at the end of the current billing period.</li>
<li>We do not store your payment card details. All payment processing is handled by
    <a href="https://stripe.com">Stripe</a>.</li>
</ul>

<h2>8. Refund Policy</h2>
<ul>
<li>If you cancel during the 14-day free trial, you will not be charged.</li>
<li>For annual plans, you may request a pro-rata refund within 30 days of purchase.</li>
<li>Monthly plans are non-refundable but you may cancel to prevent future charges.</li>
<li>Refund requests should be sent to <a href="mailto:support@bhapi.ai">support@bhapi.ai</a>.</li>
</ul>

<h2>9. Intellectual Property</h2>
<ul>
<li>The Service, including its software, design, and documentation, is owned by Bhapi and
    protected by intellectual property laws.</li>
<li>Your data remains your property. We claim no ownership of your content.</li>
<li>You grant us a limited licence to process your data as described in our
    <a href="/legal/privacy">Privacy Policy</a>.</li>
<li>The Bhapi name, logo, and branding are trademarks of Bhapi. You may not use them
    without written permission.</li>
</ul>

<h2>10. Limitation of Liability</h2>
<ul>
<li>The Service is provided &ldquo;as is&rdquo; and &ldquo;as available&rdquo; without warranties
    of any kind, express or implied.</li>
<li>We do not guarantee that the Service will detect all safety risks. The Service is a
    supplementary tool and does not replace parental or educational oversight.</li>
<li>To the maximum extent permitted by law, our total liability for any claim arising from
    your use of the Service is limited to the fees you paid in the 12 months preceding
    the claim.</li>
<li>We are not liable for indirect, incidental, special, consequential, or punitive damages.</li>
<li>We are not responsible for actions taken by AI platforms monitored through the Service.</li>
</ul>

<h2>11. Indemnification</h2>
<p>You agree to indemnify and hold Bhapi harmless from any claims, damages, or expenses
arising from your use of the Service, your violation of these Terms, or your violation
of any third-party rights.</p>

<h2>12. Termination</h2>
<ul>
<li>You may terminate your account at any time from the account settings page.</li>
<li>We may suspend or terminate your account for violation of these Terms, with notice
    where practicable.</li>
<li>Upon termination, your data is deleted in accordance with our
    <a href="/legal/privacy">Privacy Policy</a> (immediate cascade deletion, with
    legally required records retained per retention schedule).</li>
<li>Sections 9-11 and 13-14 survive termination.</li>
</ul>

<h2>13. Governing Law</h2>
<p>These Terms are governed by the laws of England and Wales. Any disputes shall be
resolved in the courts of England and Wales, without prejudice to any mandatory consumer
protection laws in your jurisdiction.</p>

<h2>14. Dispute Resolution</h2>
<p>Before initiating legal proceedings, you agree to attempt resolution by contacting us at
<a href="mailto:legal@bhapi.ai">legal@bhapi.ai</a>. We will make good-faith efforts
to resolve disputes within 30 days.</p>

<h2>15. Changes to These Terms</h2>
<p>We may update these Terms from time to time. We will notify you of material changes
via email at least 30 days before they take effect. Continued use after the effective
date constitutes acceptance.</p>

<h2>16. Contact</h2>
<p>For legal inquiries: <a href="mailto:legal@bhapi.ai">legal@bhapi.ai</a></p>
<p>For general support: <a href="mailto:support@bhapi.ai">support@bhapi.ai</a></p>
</body>
</html>"""
