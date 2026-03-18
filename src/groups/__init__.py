"""Group & member management module."""

# Import models so they are registered with Base.metadata for create_all
from src.groups.agreement import FamilyAgreement as FamilyAgreement  # noqa: F401
from src.groups.emergency_contacts import EmergencyContact as EmergencyContact  # noqa: F401
from src.groups.service import check_family_agreement_signed as check_family_agreement_signed  # noqa: F401
