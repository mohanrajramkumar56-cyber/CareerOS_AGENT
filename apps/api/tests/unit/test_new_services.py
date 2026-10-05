"""
Tests for all new Phase 6–10 services:
- email_classifier
- human_takeover
- notification_service
- storage
- policy_engine
- model_router
- policies API endpoints
- audit API endpoints
- resume export (DOCX path)
"""
from __future__ import annotations

import uuid
import pytest


# ══════════════════════════════════════════════════════════════════
# Email Classifier
# ══════════════════════════════════════════════════════════════════

class TestEmailClassifier:
    def test_classify_interview(self):
        from app.services.email_classifier import classify_email, EmailCategory
        result = classify_email(
            subject="Interview Invitation — Software Engineer",
            body="We would like to invite you for a technical interview next week.",
        )
        assert result.category == EmailCategory.INTERVIEW
        assert result.confidence >= 0.85
        assert result.sanitized_subject != ""

    def test_classify_rejection(self):
        from app.services.email_classifier import classify_email, EmailCategory
        result = classify_email(
            subject="Update on your application",
            body="Unfortunately, we have decided not to move forward with your application.",
        )
        assert result.category == EmailCategory.REJECTION
        assert result.confidence >= 0.85

    def test_classify_offer(self):
        from app.services.email_classifier import classify_email, EmailCategory
        result = classify_email(
            subject="Offer of Employment",
            body="We are pleased to offer you the position. Please review the offer letter attached.",
        )
        assert result.category == EmailCategory.OFFER
        assert result.confidence >= 0.90

    def test_classify_assessment(self):
        from app.services.email_classifier import classify_email, EmailCategory
        result = classify_email(
            subject="Coding Assessment Invitation",
            body="Please complete the HackerRank coding challenge within 48 hours.",
        )
        assert result.category == EmailCategory.ASSESSMENT
        assert result.confidence >= 0.85

    def test_classify_application_received(self):
        from app.services.email_classifier import classify_email, EmailCategory
        result = classify_email(
            subject="Application Received",
            body="Thank you for applying. We have received your application and will be in touch.",
        )
        assert result.category == EmailCategory.APPLICATION_RECEIVED

    def test_classify_unknown(self):
        from app.services.email_classifier import classify_email, EmailCategory
        result = classify_email(
            subject="Hello",
            body="Just a random email with no career-related content.",
        )
        assert result.category == EmailCategory.UNKNOWN
        assert result.confidence == 0.0

    def test_strips_html(self):
        from app.services.email_classifier import classify_email, EmailCategory
        result = classify_email(
            subject="Interview",
            body="<html><body><p>We'd like to <b>interview</b> you!</p></body></html>",
        )
        assert result.category == EmailCategory.INTERVIEW
        assert "<html>" not in result.sanitized_preview

    def test_sanitized_preview_max_length(self):
        from app.services.email_classifier import classify_email
        long_body = "x " * 5000
        result = classify_email(subject="Test", body=long_body)
        assert len(result.sanitized_preview) <= 200

    def test_scheduling(self):
        from app.services.email_classifier import classify_email, EmailCategory
        result = classify_email(
            subject="Schedule your interview",
            body="Please use Calendly to pick a time slot. No interview yet confirmed.",
        )
        # Calendly + "pick a time" should trigger scheduling OR interview — both valid
        assert result.category in (EmailCategory.SCHEDULING, EmailCategory.INTERVIEW)

    def test_matched_signals_populated(self):
        from app.services.email_classifier import classify_email, EmailCategory
        result = classify_email(
            subject="Interview scheduled",
            body="Your phone screen and technical interview are confirmed.",
        )
        assert result.category == EmailCategory.INTERVIEW
        assert len(result.matched_signals) > 0


# ══════════════════════════════════════════════════════════════════
# Human Takeover Detection
# ══════════════════════════════════════════════════════════════════

class TestHumanTakeover:
    def test_detects_recaptcha(self):
        from app.services.human_takeover import detect_captcha_on_page, TakeoverReason
        signal = detect_captcha_on_page('<div class="g-recaptcha" data-sitekey="xxx"></div>')
        assert signal is not None
        assert signal.required is True
        assert signal.reason == TakeoverReason.CAPTCHA

    def test_detects_hcaptcha(self):
        from app.services.human_takeover import detect_captcha_on_page
        signal = detect_captcha_on_page('<iframe src="https://hcaptcha.com/captcha"></iframe>')
        assert signal is not None

    def test_no_captcha_returns_none(self):
        from app.services.human_takeover import detect_captcha_on_page
        signal = detect_captcha_on_page("<form><input type='text' name='email'></form>")
        assert signal is None

    def test_detects_legal_question(self):
        from app.services.human_takeover import detect_legal_question, TakeoverReason
        signal = detect_legal_question(
            "Background check authorization",
            "I consent to a background check",
        )
        assert signal is not None
        assert signal.reason == TakeoverReason.LEGAL_QUESTION

    def test_detects_payment(self):
        from app.services.human_takeover import detect_payment_request, TakeoverReason
        signal = detect_payment_request("Please pay the application fee of $50.")
        assert signal is not None
        assert signal.reason == TakeoverReason.PAYMENT_REQUEST

    def test_no_payment_in_normal_text(self):
        from app.services.human_takeover import detect_payment_request
        signal = detect_payment_request("Please submit your resume and cover letter.")
        assert signal is None

    def test_analyze_page_payment_priority(self):
        from app.services.human_takeover import analyze_page_for_takeover, TakeoverReason
        # Payment should be detected even if there's also a captcha
        html = '<div class="g-recaptcha"></div>'
        text = "Please pay the application fee of $25."
        signal = analyze_page_for_takeover(html, text)
        assert signal is not None
        assert signal.reason == TakeoverReason.PAYMENT_REQUEST

    def test_analyze_page_captcha(self):
        from app.services.human_takeover import analyze_page_for_takeover, TakeoverReason
        html = '<div data-sitekey="abc123"></div>'
        text = "Please complete the form below."
        signal = analyze_page_for_takeover(html, text)
        assert signal is not None
        assert signal.reason == TakeoverReason.CAPTCHA

    def test_analyze_page_clean(self):
        from app.services.human_takeover import analyze_page_for_takeover
        signal = analyze_page_for_takeover(
            "<form><input name='email'></form>",
            "Please enter your email address.",
        )
        assert signal is None

    def test_analyze_page_legal_field(self):
        from app.services.human_takeover import analyze_page_for_takeover, TakeoverReason
        signal = analyze_page_for_takeover(
            "<form></form>",
            "Normal text",
            field_labels=["Background check authorization"],
        )
        assert signal is not None
        assert signal.reason == TakeoverReason.LEGAL_QUESTION


# ══════════════════════════════════════════════════════════════════
# Notification Service
# ══════════════════════════════════════════════════════════════════

class TestNotificationService:
    @pytest.mark.asyncio
    async def test_notify_no_adapters(self):
        """Notification with no adapters configured never raises."""
        from app.services.notification_service import NotificationService, Notification, NotificationEvent
        svc = NotificationService()
        # Disable telegram for this test
        svc.telegram.enabled = False
        notif = Notification(
            event=NotificationEvent.APPLICATION_SUBMITTED,
            title="Test",
            message="Test notification",
        )
        # Should not raise
        await svc.notify(notif)

    @pytest.mark.asyncio
    async def test_notify_human_approval(self):
        from app.services.notification_service import NotificationService
        svc = NotificationService()
        svc.telegram.enabled = False
        # Should not raise
        await svc.notify_human_approval_required("abc12345", "Software Engineer")

    @pytest.mark.asyncio
    async def test_notify_email_classified_interview(self):
        from app.services.notification_service import NotificationService
        svc = NotificationService()
        svc.telegram.enabled = False
        await svc.notify_email_classified("interview", "Interview Invitation", "app-001")

    @pytest.mark.asyncio
    async def test_notify_email_classified_rejection(self):
        from app.services.notification_service import NotificationService
        svc = NotificationService()
        svc.telegram.enabled = False
        await svc.notify_email_classified("rejection", "Application Update")

    @pytest.mark.asyncio
    async def test_get_notification_service_singleton(self):
        from app.services.notification_service import get_notification_service
        svc1 = get_notification_service()
        svc2 = get_notification_service()
        assert svc1 is svc2

    def test_notification_event_values(self):
        from app.services.notification_service import NotificationEvent
        assert NotificationEvent.INTERVIEW_DETECTED == "interview_detected"
        assert NotificationEvent.OFFER_DETECTED == "offer_detected"
        assert NotificationEvent.REJECTION_DETECTED == "rejection_detected"


# ══════════════════════════════════════════════════════════════════
# Storage Service
# ══════════════════════════════════════════════════════════════════

class TestStorageService:
    @pytest.mark.asyncio
    async def test_local_storage_save_and_load(self, tmp_path):
        from app.services.storage import LocalStorage
        storage = LocalStorage(base_path=str(tmp_path))
        key = "test/resume.pdf"
        data = b"PDF content here"
        await storage.save(key, data, "application/pdf")
        loaded = await storage.load(key)
        assert loaded == data

    @pytest.mark.asyncio
    async def test_local_storage_delete(self, tmp_path):
        from app.services.storage import LocalStorage
        storage = LocalStorage(base_path=str(tmp_path))
        key = "test/file.txt"
        await storage.save(key, b"hello")
        await storage.delete(key)
        with pytest.raises(FileNotFoundError):
            await storage.load(key)

    @pytest.mark.asyncio
    async def test_local_storage_delete_nonexistent(self, tmp_path):
        from app.services.storage import LocalStorage
        storage = LocalStorage(base_path=str(tmp_path))
        # Should not raise on deleting a non-existent file
        await storage.delete("nonexistent/file.txt")

    def test_local_storage_get_url(self, tmp_path):
        from app.services.storage import LocalStorage
        storage = LocalStorage(base_path=str(tmp_path))
        url = storage.get_url("resumes/abc.pdf")
        assert "/api/v1/resumes/artifacts/" in url

    @pytest.mark.asyncio
    async def test_local_storage_missing_file(self, tmp_path):
        from app.services.storage import LocalStorage
        storage = LocalStorage(base_path=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            await storage.load("nonexistent.pdf")

    def test_get_storage_returns_local_by_default(self, monkeypatch):
        monkeypatch.setenv("STORAGE_BACKEND", "local")
        from app.services import storage as storage_module
        # Force reimport
        import importlib
        importlib.reload(storage_module)
        backend = storage_module.get_storage()
        assert isinstance(backend, storage_module.LocalStorage)


# ══════════════════════════════════════════════════════════════════
# Policy Engine
# ══════════════════════════════════════════════════════════════════

class TestPolicyEngine:
    def test_policy_decision_constants(self):
        from app.services.policy_engine import PolicyDecision
        # PolicyDecision is a constants class, not a dataclass
        assert PolicyDecision.ALLOW == "allow"
        assert PolicyDecision.DENY == "deny"
        assert PolicyDecision.REQUIRE_APPROVAL == "require_approval"

    def test_policy_evaluation_result(self):
        from app.services.policy_engine import PolicyDecision, PolicyEvaluationResult
        result = PolicyEvaluationResult(decision=PolicyDecision.ALLOW, reason="no rules")
        assert result.decision == PolicyDecision.ALLOW
        assert result.reason == "no rules"

    @pytest.mark.asyncio
    async def test_record_audit_log_standalone(self, db_session):
        """audit() is the standalone audit function in policy_engine."""
        from app.services.policy_engine import audit
        # Should not raise
        entry = await audit(
            db=db_session,
            action="test.action",
            user_id=None,  # No FK constraint — audit logs don't require a user
            resource_type="test",
            resource_id=str(uuid.uuid4()),
            success=True,
        )
        await db_session.commit()
        assert entry.action == "test.action"
        assert entry.success is True


# ══════════════════════════════════════════════════════════════════
# Model Router
# ══════════════════════════════════════════════════════════════════

class TestModelRouter:
    @pytest.mark.asyncio
    async def test_ollama_health_check_unreachable(self):
        """Ollama health check returns False when not running."""
        from app.services.model_router import OllamaProvider
        provider = OllamaProvider(
            base_url="http://localhost:19999",  # Not running
            default_model="llama3",
        )
        result = await provider.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_model_router_no_providers_raises(self):
        """ModelRouter raises RuntimeError when no providers available."""
        from app.services.model_router import ModelRouter
        router = ModelRouter()
        router._ollama_available = False
        router.openai = None
        with pytest.raises(RuntimeError, match="No AI model provider"):
            await router.complete("Test prompt")

    @pytest.mark.asyncio
    async def test_embed_returns_empty_when_unavailable(self):
        """embed() returns [] gracefully when Ollama is not running."""
        from app.services.model_router import ModelRouter
        router = ModelRouter()
        router._ollama_available = False
        result = await router.embed("test text")
        assert result == []

    def test_get_model_router_singleton(self):
        from app.services.model_router import get_model_router
        r1 = get_model_router()
        r2 = get_model_router()
        assert r1 is r2

    def test_task_model_map_has_all_types(self):
        from app.services.model_router import ModelRouter, TaskType
        for task_type in TaskType:
            assert task_type in ModelRouter.TASK_MODEL_MAP


# ══════════════════════════════════════════════════════════════════
# Policies API
# ══════════════════════════════════════════════════════════════════

class TestPoliciesAPI:
    async def _setup(self, client) -> dict:
        """Register, login, create profile — return auth headers."""
        email = f"policy_{uuid.uuid4()}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        login = await client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        await client.post("/api/v1/candidates/profile", json={"full_name": "Policy User"}, headers=headers)
        return headers

    @pytest.mark.asyncio
    async def test_list_policies_empty(self, client):
        headers = await self._setup(client)
        r = await client.get("/api/v1/policies/", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_policy(self, client):
        headers = await self._setup(client)
        r = await client.post("/api/v1/policies/", json={
            "action": "application.submit",
            "enabled": True,
            "requires_approval": True,
        }, headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert data["action"] == "application.submit"
        assert data["requires_approval"] is True

    @pytest.mark.asyncio
    async def test_get_policy_by_id(self, client):
        headers = await self._setup(client)
        create = await client.post("/api/v1/policies/", json={
            "action": "resume.generate",
            "enabled": True,
            "requires_approval": False,
        }, headers=headers)
        policy_id = create.json()["id"]
        r = await client.get(f"/api/v1/policies/{policy_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["id"] == policy_id

    @pytest.mark.asyncio
    async def test_update_policy(self, client):
        headers = await self._setup(client)
        create = await client.post("/api/v1/policies/", json={
            "action": "email.send_followup",
            "enabled": True,
            "requires_approval": True,
        }, headers=headers)
        policy_id = create.json()["id"]
        r = await client.put(f"/api/v1/policies/{policy_id}", json={
            "requires_approval": False,
            "max_per_day": 3,
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["requires_approval"] is False
        assert r.json()["max_per_day"] == 3

    @pytest.mark.asyncio
    async def test_delete_policy(self, client):
        headers = await self._setup(client)
        create = await client.post("/api/v1/policies/", json={
            "action": "notification.send",
            "enabled": True,
            "requires_approval": False,
        }, headers=headers)
        policy_id = create.json()["id"]
        r = await client.delete(f"/api/v1/policies/{policy_id}", headers=headers)
        assert r.status_code == 204
        # Verify gone
        r2 = await client.get(f"/api/v1/policies/{policy_id}", headers=headers)
        assert r2.status_code == 404

    @pytest.mark.asyncio
    async def test_get_valid_actions(self, client):
        headers = await self._setup(client)
        r = await client.get("/api/v1/policies/actions", headers=headers)
        assert r.status_code == 200
        actions = r.json()
        assert "application.submit" in actions
        assert "resume.generate" in actions

    @pytest.mark.asyncio
    async def test_policy_requires_auth(self, client):
        r = await client.get("/api/v1/policies/")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_cross_user_policy_isolation(self, client):
        """User cannot access another user's policy."""
        headers1 = await self._setup(client)
        headers2 = await self._setup(client)
        create = await client.post("/api/v1/policies/", json={
            "action": "job.discover",
            "enabled": True,
            "requires_approval": False,
        }, headers=headers1)
        policy_id = create.json()["id"]
        # User 2 should not see user 1's policy
        r = await client.get(f"/api/v1/policies/{policy_id}", headers=headers2)
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════
# Audit API
# ══════════════════════════════════════════════════════════════════

class TestAuditAPI:
    async def _setup(self, client) -> dict:
        email = f"audit_{uuid.uuid4()}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        login = await client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
        token = login.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_list_audit_logs_empty(self, client):
        headers = await self._setup(client)
        r = await client.get("/api/v1/audit/", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_audit_requires_auth(self, client):
        r = await client.get("/api/v1/audit/")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_audit_no_create_endpoint(self, client):
        """Audit logs must be read-only via API — no POST route exists."""
        headers = await self._setup(client)
        r = await client.post("/api/v1/audit/", json={"action": "fake"}, headers=headers)
        # FastAPI returns 405 Method Not Allowed or 422 if route accepts different methods
        assert r.status_code in (405, 422)

    @pytest.mark.asyncio
    async def test_audit_no_delete_endpoint(self, client):
        """Audit logs are immutable — no delete route exists."""
        headers = await self._setup(client)
        fake_id = str(uuid.uuid4())
        r = await client.delete(f"/api/v1/audit/{fake_id}", headers=headers)
        assert r.status_code in (405, 404)

    @pytest.mark.asyncio
    async def test_audit_get_nonexistent(self, client):
        headers = await self._setup(client)
        r = await client.get(f"/api/v1/audit/{uuid.uuid4()}", headers=headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_audit_pagination(self, client):
        headers = await self._setup(client)
        r = await client.get("/api/v1/audit/?page=1&page_size=10", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["page"] == 1
        assert data["page_size"] == 10


# ══════════════════════════════════════════════════════════════════
# Resume Export (DOCX — no weasyprint needed for this path)
# ══════════════════════════════════════════════════════════════════

class TestResumeExport:
    def test_markdown_to_docx_basic(self):
        try:
            from app.services.resume_export import markdown_to_docx
        except ImportError:
            pytest.skip("python-docx not installed")

        md = """# John Doe
## Experience
### Software Engineer at Acme
- Built scalable APIs
- Led team of 5 engineers

## Skills
Python, FastAPI, PostgreSQL
"""
        result = markdown_to_docx(md, title="John Doe Resume")
        assert isinstance(result, bytes)
        assert len(result) > 0
        # DOCX files start with PK (ZIP magic bytes)
        assert result[:2] == b"PK"

    def test_markdown_to_docx_empty(self):
        try:
            from app.services.resume_export import markdown_to_docx
        except ImportError:
            pytest.skip("python-docx not installed")
        result = markdown_to_docx("", title="Empty")
        assert isinstance(result, bytes)

    def test_markdown_to_pdf_missing_deps(self):
        """PDF export raises ImportError when weasyprint not installed."""
        import sys
        # Temporarily mock weasyprint as missing
        original = sys.modules.get("weasyprint")
        sys.modules["weasyprint"] = None  # type: ignore
        try:
            from app.services import resume_export
            import importlib
            importlib.reload(resume_export)
            with pytest.raises((ImportError, TypeError)):
                resume_export.markdown_to_pdf("# Test")
        finally:
            if original is None:
                sys.modules.pop("weasyprint", None)
            else:
                sys.modules["weasyprint"] = original


# ══════════════════════════════════════════════════════════════════
# Rate Limiting
# ══════════════════════════════════════════════════════════════════

class TestRateLimiting:
    def test_limiter_exists(self):
        from app.core.rate_limit import limiter
        assert limiter is not None

    def test_retry_decorator_exists(self):
        from app.core.retry import external_call_retry, http_retry, db_retry, email_retry
        assert callable(http_retry)
        assert callable(db_retry)
        assert callable(email_retry)
