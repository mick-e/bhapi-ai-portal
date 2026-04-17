"""FERPA annual notification templates per 34 CFR 99.7.

Contents reviewed by counsel. Templates use Python string.Template syntax
for safe interpolation (no code execution risk from user-supplied values).
"""

from string import Template

TEMPLATE_VERSION = "v1"

ANNUAL_NOTIFICATION_TEMPLATE_V1 = Template("""Dear $parent_name,

This notice fulfills the annual FERPA notification requirement of $school_name for school year $school_year.

Under the Family Educational Rights and Privacy Act (FERPA), parents and eligible students have the right to:

1. Inspect and review the student's education records
2. Request amendment of records believed to be inaccurate
3. Provide written consent before disclosure of personally identifiable information
4. File a complaint with the U.S. Department of Education

The following data categories are designated as educational records:
$record_categories

For full text of these rights and procedures to exercise them, visit:
$portal_url/ferpa/notice

To opt out of directory-information disclosures, contact $contact_email by $opt_out_deadline.

Sincerely,
$school_name""")


def render_annual_notification(
    *,
    parent_name: str,
    school_name: str,
    school_year: str,
    record_categories: str,
    portal_url: str,
    contact_email: str,
    opt_out_deadline: str,
) -> str:
    """Render the annual FERPA notification for a parent."""
    return ANNUAL_NOTIFICATION_TEMPLATE_V1.safe_substitute(
        parent_name=parent_name,
        school_name=school_name,
        school_year=school_year,
        record_categories=record_categories,
        portal_url=portal_url,
        contact_email=contact_email,
        opt_out_deadline=opt_out_deadline,
    )
