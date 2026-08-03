from app.scoring import classify_remote, classify_track_domain, has_profile_anchor, score_opportunity


def test_remote_power_bi_dashboard_scores_high():
    score, keywords, remote_type, is_remote = score_opportunity(
        "Power BI Dashboard Developer",
        "Example",
        "Remote Worldwide",
        "Build dashboards with Power BI, SQL, DAX, APIs and data visualization.",
    )
    assert is_remote
    assert remote_type == "remote"
    assert score >= 70
    assert "power bi" in keywords


def test_onsite_only_is_rejected():
    remote_type, is_remote = classify_remote(
        "Data Analyst",
        "Abidjan office",
        "This is an onsite role, no remote option.",
    )
    assert remote_type == "onsite"
    assert not is_remote


def test_remote_work_not_considered_is_rejected():
    remote_type, is_remote = classify_remote(
        "Power BI Analyst",
        "Houston, TX",
        "This position requires being onsite. Remote work not considered.",
    )
    assert remote_type == "onsite"
    assert not is_remote


def test_general_software_engineer_has_no_profile_anchor():
    assert not has_profile_anchor("Staff Software Engineer", "Build product APIs with Python and SQL.")


def test_consultance_app_development_is_classified():
    track, domain = classify_track_domain(
        "Request for quotes - dashboard application development consultant",
        "consultance",
        "Build a web dashboard, API integration and data visualization platform.",
    )
    assert track == "consultance"
    assert domain in {"data-bi", "developpement-app"}


def test_me_job_is_classified_apart():
    track, domain = classify_track_domain(
        "Monitoring and Evaluation Data Analyst",
        "full-time",
        "Research, indicators, survey data, dashboard reporting.",
    )
    assert track == "emploi-data"
    assert domain == "suivi-evaluation-etudes"


def test_communication_consultance_is_classified_apart():
    track, domain = classify_track_domain(
        "Digital communications consultant",
        "consultancy",
        "Prepare social media content, campaign assets, infographics and publications.",
    )
    assert track == "consultance"
    assert domain == "communication"
