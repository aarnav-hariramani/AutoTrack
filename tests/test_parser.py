from src.internship_logger import nlp_parser as nlp

def test_classify_status():
    subj = "Thank you for applying to Acme for Software Engineering Intern"
    body = "We received your application."
    assert nlp.classify_status(subj, body) == "Applied"

def test_extract_role():
    subj = "Application Confirmation - Data Science Intern (Summer 2026)"
    assert "intern" in nlp.extract_role(subj, "").lower()

def test_extract_company():
    subj = "Your application to Globex — SWE Intern"
    frm = "Globex Careers <careers@globex.com>"
    assert nlp.extract_company(subj, frm, "").lower().startswith("globex")
