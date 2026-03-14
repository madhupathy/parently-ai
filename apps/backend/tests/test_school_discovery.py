"""Tests for the school discovery pipeline services."""

from __future__ import annotations

import json
import os
import sys

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestPromptLoader:
    """Tests for services/prompt_loader.py."""

    def test_load_context_returns_dict(self) -> None:
        from services.prompt_loader import load_context
        ctx = load_context()
        assert isinstance(ctx, dict)
        assert ctx.get("version") == "v1"
        assert "discovery_keywords" in ctx
        assert "email_platform_domains" in ctx

    def test_load_prompt_substitutes_variables(self) -> None:
        from services.prompt_loader import load_prompt, load_context
        ctx = load_context()
        prompt = load_prompt("school_discovery_prompt_v1", context=ctx)
        # max_discovery_candidates should be substituted with "3"
        assert "3" in prompt
        # Template variable should NOT remain
        assert "{{max_discovery_candidates}}" not in prompt

    def test_load_prompt_with_extra_vars(self) -> None:
        from services.prompt_loader import load_prompt
        prompt = load_prompt(
            "school_discovery_prompt_v1",
            extra_vars={"max_discovery_candidates": 5},
        )
        assert "5" in prompt

    def test_load_prompt_missing_file_raises(self) -> None:
        from services.prompt_loader import load_prompt
        import pytest
        with pytest.raises(FileNotFoundError):
            load_prompt("nonexistent_prompt_v99")

    def test_list_prompts_returns_all(self) -> None:
        from services.prompt_loader import list_prompts
        prompts = list_prompts()
        assert "school_discovery_prompt_v1" in prompts
        assert "digest_compose_prompt_v1" in prompts
        assert "email_school_classifier_prompt_v1" in prompts
        assert len(prompts) >= 7


class TestSchoolDiscoveryQueryBuilder:
    """Tests for services/school_discovery.py."""

    def test_tokenize_basic(self) -> None:
        from services.school_discovery import tokenize_school_query
        result = tokenize_school_query("Harmony Georgetown, Georgetown, TX 78628")
        assert result["school_tokens"] == ["Harmony", "Georgetown"]
        assert result["city"] == "Georgetown"
        assert result["state"] == "TX"
        assert result["zip_code"] == "78628"

    def test_tokenize_no_location(self) -> None:
        from services.school_discovery import tokenize_school_query
        result = tokenize_school_query("Lincoln Elementary")
        assert result["school_tokens"] == ["Lincoln", "Elementary"]
        assert result["city"] is None
        assert result["state"] is None
        assert result["zip_code"] is None

    def test_tokenize_with_zip_only(self) -> None:
        from services.school_discovery import tokenize_school_query
        result = tokenize_school_query("Round Rock High School 78665")
        assert result["zip_code"] == "78665"

    def test_expand_abbreviations(self) -> None:
        from services.school_discovery import expand_abbreviations
        expansions = expand_abbreviations(["Harmony", "Georgetown"])
        assert "Harmony Science Academy" in expansions
        assert "HSA" in expansions

    def test_expand_abbreviations_unknown(self) -> None:
        from services.school_discovery import expand_abbreviations
        expansions = expand_abbreviations(["Lincoln", "Elementary"])
        assert expansions == []

    def test_build_search_queries_returns_list(self) -> None:
        from services.school_discovery import build_search_queries
        queries = build_search_queries("Harmony Georgetown, Georgetown, TX 78628")
        assert isinstance(queries, list)
        assert len(queries) >= 3
        assert len(queries) <= 6

    def test_build_search_queries_no_duplicates(self) -> None:
        from services.school_discovery import build_search_queries
        queries = build_search_queries("KIPP Austin, Austin, TX")
        assert len(queries) == len(set(queries))

    def test_build_search_queries_max(self) -> None:
        from services.school_discovery import build_search_queries
        queries = build_search_queries("Harmony Georgetown", max_queries=2)
        assert len(queries) <= 2


class TestSourceVerifier:
    """Tests for services/source_verifier.py deterministic scoring."""

    def test_score_full_match(self) -> None:
        from services.source_verifier import score_candidate
        candidate = {"name": "Harmony Georgetown", "homepage_url": "https://harmonytx.org"}
        fetch_result = {
            "snippets": ["Harmony Science Academy Georgetown"],
            "found_calendar_pages": ["https://harmonytx.org/calendar"],
            "found_ics_links": ["https://harmonytx.org/cal.ics"],
            "found_rss_links": [],
            "found_pdf_links": ["https://harmonytx.org/calendar.pdf"],
            "http_status": 200,
        }
        score = score_candidate(candidate, fetch_result, "Harmony Georgetown, Georgetown, TX")
        assert score >= 0.80

    def test_score_no_match(self) -> None:
        from services.source_verifier import score_candidate
        candidate = {"name": "Some Other School", "homepage_url": "https://example.com"}
        fetch_result = {
            "snippets": ["Unrelated Content"],
            "found_calendar_pages": [],
            "found_ics_links": [],
            "found_rss_links": [],
            "found_pdf_links": [],
            "http_status": 200,
        }
        score = score_candidate(candidate, fetch_result, "Harmony Georgetown, Georgetown, TX")
        assert score < 0.3

    def test_score_partial_match(self) -> None:
        from services.source_verifier import score_candidate
        candidate = {"name": "Harmony Georgetown", "homepage_url": "https://harmonytx.org"}
        fetch_result = {
            "snippets": ["Harmony Science Academy Georgetown Campus"],
            "found_calendar_pages": ["https://harmonytx.org/calendar"],
            "found_ics_links": [],
            "found_rss_links": [],
            "found_pdf_links": [],
            "http_status": 200,
        }
        score = score_candidate(candidate, fetch_result, "Harmony Georgetown, Georgetown, TX")
        assert 0.3 <= score <= 0.9

    def test_score_and_classify_verified(self) -> None:
        from services.source_verifier import score_and_classify
        candidate = {"name": "Harmony Georgetown", "homepage_url": "https://harmonytx.org"}
        fetch_result = {
            "snippets": ["Harmony Science Academy Georgetown"],
            "found_calendar_pages": ["https://harmonytx.org/calendar"],
            "found_ics_links": ["https://harmonytx.org/cal.ics"],
            "found_rss_links": [],
            "found_pdf_links": ["https://harmonytx.org/calendar.pdf"],
            "http_status": 200,
        }
        score, status = score_and_classify(
            candidate, fetch_result, "Harmony Georgetown, Georgetown, TX",
            use_llm_for_gray_zone=False,
        )
        assert score >= 0.80
        assert status == "verified"

    def test_score_and_classify_needs_confirmation(self) -> None:
        from services.source_verifier import score_and_classify
        candidate = {"name": "Harmony Georgetown", "homepage_url": "https://harmonytx.org"}
        fetch_result = {
            "snippets": ["Harmony Science Academy"],
            "found_calendar_pages": [],
            "found_ics_links": [],
            "found_rss_links": [],
            "found_pdf_links": [],
            "http_status": 200,
        }
        score, status = score_and_classify(
            candidate, fetch_result, "Harmony Georgetown, Georgetown, TX",
            use_llm_for_gray_zone=False,
        )
        assert status in ("needs_confirmation", "failed")

    def test_score_clamped_to_range(self) -> None:
        from services.source_verifier import score_candidate
        candidate = {"name": "X", "homepage_url": ""}
        fetch_result = {
            "snippets": [],
            "found_calendar_pages": [],
            "found_ics_links": [],
            "found_rss_links": [],
            "found_pdf_links": [],
            "http_status": None,
        }
        score = score_candidate(candidate, fetch_result, "Test School")
        assert 0.0 <= score <= 1.0


class TestEmailClassifier:
    """Tests for services/email_classifier.py deterministic pass."""

    def test_classify_classdojo(self) -> None:
        from services.email_classifier import classify_email
        result = classify_email(
            sender="noreply@classdojo.com",
            subject="Emma earned 5 points!",
            snippet="Emma has been doing great in class today.",
            child_names=["Emma", "Liam"],
            use_llm=False,
        )
        assert result["platform"] == "classdojo"
        assert result["confidence"] >= 0.9
        assert result["child_match"] == "Emma"

    def test_classify_brightwheel(self) -> None:
        from services.email_classifier import classify_email
        result = classify_email(
            sender="updates@brightwheel.com",
            subject="Daily Report for Liam",
            snippet="Here's what Liam did today",
            child_names=["Emma", "Liam"],
            use_llm=False,
        )
        assert result["platform"] == "brightwheel"
        assert result["child_match"] == "Liam"

    def test_classify_school_direct(self) -> None:
        from services.email_classifier import classify_email
        result = classify_email(
            sender="principal@lincolnelem.k12.tx.us",
            subject="Field Trip Permission Slip",
            snippet="Please sign and return the attached form",
            use_llm=False,
        )
        assert result["platform"] == "school_direct"
        assert result["confidence"] >= 0.7

    def test_classify_unknown(self) -> None:
        from services.email_classifier import classify_email
        result = classify_email(
            sender="spam@random.com",
            subject="Win a prize!",
            snippet="Click here to claim",
            use_llm=False,
        )
        assert result["platform"] == "unknown"

    def test_is_actionable_detection(self) -> None:
        from services.email_classifier import classify_email
        result = classify_email(
            sender="noreply@classdojo.com",
            subject="Permission slip due tomorrow",
            snippet="Please sign the permission slip for the field trip",
            use_llm=False,
        )
        assert result["extracted"]["is_actionable"] is True

    def test_urgency_high(self) -> None:
        from services.email_classifier import classify_email
        result = classify_email(
            sender="noreply@classdojo.com",
            subject="URGENT: School closure today",
            snippet="Due to weather, school is closed today",
            use_llm=False,
        )
        assert result["extracted"]["urgency"] == "high"

    def test_batch_classify(self) -> None:
        from services.email_classifier import classify_emails_batch
        emails = [
            {"sender": "noreply@classdojo.com", "subject": "Points for Emma", "snippet": "Emma earned 3 points"},
            {"sender": "updates@brightwheel.com", "subject": "Liam's report", "snippet": "Daily update for Liam"},
            {"sender": "random@gmail.com", "subject": "Hello", "snippet": "How are you?"},
        ]
        results = classify_emails_batch(emails, child_names=["Emma", "Liam"], use_llm=False)
        assert len(results) == 3
        assert results[0]["platform"] == "classdojo"
        assert results[1]["platform"] == "brightwheel"
        assert results[2]["platform"] == "unknown"


class TestSiteFetcher:
    """Tests for services/site_fetcher.py HTML parsing helpers."""

    def test_extract_snippets(self) -> None:
        from bs4 import BeautifulSoup
        from services.site_fetcher import _extract_snippets
        html = "<html><head><title>Harmony Science Academy</title></head><body><h1>Welcome</h1><h2>Calendar</h2></body></html>"
        soup = BeautifulSoup(html, "lxml")
        snippets = _extract_snippets(soup)
        assert any("Harmony" in s for s in snippets)
        assert any("Welcome" in s for s in snippets)

    def test_find_calendar_links(self) -> None:
        from bs4 import BeautifulSoup
        from services.site_fetcher import _find_calendar_links
        html = """
        <html><body>
          <a href="/calendar">School Calendar</a>
          <a href="/events">Events Page</a>
          <a href="/about">About Us</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        hints = [".ics", "ical", "subscribe", "calendar feed", "rss", "/calendar", "/events"]
        links = _find_calendar_links(soup, "https://example.com", hints)
        assert len(links) >= 2
        assert "https://example.com/calendar" in links

    def test_find_rss_links(self) -> None:
        from bs4 import BeautifulSoup
        from services.site_fetcher import _find_rss_links
        html = """
        <html><head>
          <link rel="alternate" type="application/rss+xml" href="/feed.xml" />
        </head><body></body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        links = _find_rss_links(soup, "https://example.com")
        assert len(links) >= 1
        assert "https://example.com/feed.xml" in links

    def test_find_ics_links(self) -> None:
        from bs4 import BeautifulSoup
        from services.site_fetcher import _find_links_by_pattern
        html = """
        <html><body>
          <a href="/calendar.ics">Subscribe to Calendar</a>
          <a href="/events/download.ical">iCal Download</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        links = _find_links_by_pattern(soup, "https://example.com", [".ics", "ical"])
        assert len(links) >= 2


class TestCalendarIngest:
    """Tests for services/calendar_ingest.py ICS/RSS parsing."""

    def test_parse_ics_text(self) -> None:
        from services.calendar_ingest import parse_ics_text
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART:20260315
DTEND:20260316
SUMMARY:Spring Break Begins
DESCRIPTION:No school - Spring Break
END:VEVENT
BEGIN:VEVENT
DTSTART:20260401
SUMMARY:STAAR Testing
DESCRIPTION:State testing day
END:VEVENT
END:VCALENDAR"""
        events = parse_ics_text(ics_content)
        assert len(events) == 2
        assert events[0]["title"] == "Spring Break Begins"
        assert events[0]["start_date"] == "2026-03-15"
        assert events[0]["category"] == "holiday"
        assert events[1]["title"] == "STAAR Testing"
        assert events[1]["category"] == "testing"

    def test_categorize_events(self) -> None:
        from services.calendar_ingest import _categorize_event
        assert _categorize_event("No School - Teacher Development") == "holiday"
        assert _categorize_event("STAAR Testing Window") == "testing"
        assert _categorize_event("Parent Conference Night") == "parent_event"
        assert _categorize_event("Field Trip to Museum") == "school_event"
        assert _categorize_event("Registration Deadline") == "deadline"
        assert _categorize_event("Regular School Day") == "other"


class TestModels:
    """Tests for new DiscoveryJob and SchoolSource models."""

    def test_discovery_job_model(self) -> None:
        from storage.models import DiscoveryJob
        job = DiscoveryJob(
            user_id=1,
            child_id=1,
            school_query_text="Harmony Georgetown",
            status="queued",
        )
        assert job.school_query_text == "Harmony Georgetown"
        assert job.status == "queued"
        assert job.result() == {}

    def test_discovery_job_result_json(self) -> None:
        from storage.models import DiscoveryJob
        job = DiscoveryJob(
            user_id=1,
            child_id=1,
            school_query_text="Test",
            result_json='{"candidates": [{"name": "Test School"}]}',
        )
        result = job.result()
        assert result["candidates"][0]["name"] == "Test School"

    def test_school_source_model(self) -> None:
        from storage.models import SchoolSource
        source = SchoolSource(
            user_id=1,
            child_id=1,
            school_query="Harmony Georgetown",
            verified_name="Harmony Science Academy Georgetown",
            homepage_url="https://harmonytx.org",
            ics_urls_json='["https://harmonytx.org/cal.ics"]',
            rss_urls_json='[]',
            pdf_urls_json='["https://harmonytx.org/calendar.pdf"]',
            confidence_score=0.92,
            status="verified",
        )
        assert source.ics_urls() == ["https://harmonytx.org/cal.ics"]
        assert source.rss_urls() == []
        assert source.pdf_urls() == ["https://harmonytx.org/calendar.pdf"]

    def test_school_source_empty_json(self) -> None:
        from storage.models import SchoolSource
        source = SchoolSource(
            user_id=1,
            child_id=1,
            school_query="Test",
        )
        assert source.ics_urls() == []
        assert source.rss_urls() == []
        assert source.pdf_urls() == []

    def test_child_has_discovery_relationships(self) -> None:
        from storage.models import Child
        rels = Child.__mapper__.relationships
        assert "discovery_jobs" in rels
        assert "school_sources" in rels
