from enum import StrEnum


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SectionKind(StrEnum):
    CONTACT = "contact"
    SUMMARY = "summary"
    EDUCATION = "education"
    EXPERIENCE = "experience"
    SKILLS = "skills"
    PROJECTS = "projects"
    CERTIFICATIONS = "certifications"
    AWARDS = "awards"
    PUBLICATIONS = "publications"
    OTHER = "other"


class SkillSource(StrEnum):
    GAZETTEER = "gazetteer"
    NER = "ner"


class EvidenceStrength(StrEnum):
    CLAIMED = "claimed"
    DEMONSTRATED = "demonstrated"


class AnalysisErrorCode(StrEnum):
    FILE_TOO_LARGE = "file_too_large"
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
    ENCRYPTED_PDF = "encrypted_pdf"
    CORRUPT_PDF = "corrupt_pdf"
    TOO_MANY_PAGES = "too_many_pages"
    NOT_MACHINE_READABLE = "not_machine_readable"
    EMPTY_DOCUMENT = "empty_document"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"
