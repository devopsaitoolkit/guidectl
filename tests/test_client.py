"""Offline unit tests for guidectl (stdlib unittest — no network, no deps)."""

import unittest

from guidectl.client import GuideClient

GUIDES = {
    "api": "devopsaitoolkit",
    "version": "v1",
    "resource": "guides",
    "count": 3,
    "items": [
        {
            "id": "openstack-error-messaging-timeout",
            "title": "OpenStack Error: Messaging Timeout",
            "category": "openstack",
            "type": "error_guide",
            "tags": ["openstack", "rabbitmq", "errors"],
            "description": "Fix RPC messaging timeouts between OpenStack services.",
            "readingTime": 9,
            "url": "https://devopsaitoolkit.com/blog/openstack-error-messaging-timeout/",
            "pubDate": "2026-01-01",
        },
        {
            "id": "kubernetes-error-crashloopbackoff",
            "title": "Kubernetes Error: CrashLoopBackOff",
            "category": "kubernetes-helm",
            "type": "error_guide",
            "tags": ["kubernetes", "errors"],
            "description": "Diagnose and fix pods stuck in CrashLoopBackOff.",
            "readingTime": 11,
            "url": "https://devopsaitoolkit.com/blog/kubernetes-error-crashloopbackoff/",
            "pubDate": "2026-02-01",
        },
        {
            "id": "gitops-with-argocd-explained",
            "title": "GitOps with Argo CD, Explained",
            "category": "kubernetes-helm",
            "type": "guide",
            "tags": ["kubernetes", "gitops"],
            "description": "A practical intro to GitOps delivery with Argo CD.",
            "readingTime": 8,
            "url": "https://devopsaitoolkit.com/blog/gitops-with-argocd-explained/",
            "pubDate": "2026-03-01",
        },
    ],
}

META = {
    "api": "devopsaitoolkit",
    "version": "v1",
    "counts": {"prompts": 0, "guides": 3, "errorGuides": 2},
    "categories": [
        {"slug": "openstack", "name": "AI for OpenStack", "guides": 1, "errorGuides": 1},
        {"slug": "kubernetes-helm", "name": "AI for Kubernetes & Helm", "guides": 2, "errorGuides": 1},
    ],
}


class FakeClient(GuideClient):
    def __init__(self):
        super().__init__(cache=False)

    def fetch(self, path, refresh=False):
        if path == "meta.json":
            return META
        if path == "guides.json":
            return GUIDES
        if path.startswith("guides/"):
            cat = path[len("guides/"):-len(".json")]
            return {"items": [g for g in GUIDES["items"] if g["category"] == cat]}
        raise AssertionError(f"unexpected path {path}")


class GuideTests(unittest.TestCase):
    def setUp(self):
        self.c = FakeClient()

    def test_keyword_matches_title_and_description(self):
        self.assertEqual(
            [g["id"] for g in self.c.search("crashloopbackoff")],
            ["kubernetes-error-crashloopbackoff"],
        )
        self.assertEqual(
            [g["id"] for g in self.c.search("messaging timeout")],
            ["openstack-error-messaging-timeout"],
        )
        self.assertEqual(self.c.search("nonexistentxyz"), [])

    def test_type_filter(self):
        errs = self.c.search("", guide_type="error_guide")
        self.assertEqual({g["id"] for g in errs},
                         {"openstack-error-messaging-timeout", "kubernetes-error-crashloopbackoff"})
        guides = self.c.search("", guide_type="guide")
        self.assertEqual([g["id"] for g in guides], ["gitops-with-argocd-explained"])

    def test_category_and_type_combined(self):
        r = self.c.guides(category="kubernetes-helm", guide_type="guide")
        self.assertEqual([g["id"] for g in r], ["gitops-with-argocd-explained"])

    def test_category_filter_via_search(self):
        r = self.c.search("", category="openstack")
        self.assertEqual([g["id"] for g in r], ["openstack-error-messaging-timeout"])

    def test_tag_filter(self):
        r = self.c.search("", tag="gitops")
        self.assertEqual([g["id"] for g in r], ["gitops-with-argocd-explained"])

    def test_get_and_categories(self):
        self.assertEqual(self.c.get("gitops-with-argocd-explained")["type"], "guide")
        self.assertIsNone(self.c.get("nope"))
        self.assertEqual(len(self.c.categories()), 2)


if __name__ == "__main__":
    unittest.main()
