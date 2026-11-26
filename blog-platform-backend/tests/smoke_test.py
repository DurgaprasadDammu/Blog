import time
import subprocess
import sys
import httpx

BASE = "http://localhost:8000"


def check(label, condition, extra=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label} {extra}")
    if not condition:
        FAILURES.append(label)


FAILURES = []


def main():
    client = httpx.Client(base_url=BASE, timeout=10)

    # --- Register users ---
    r = client.post("/api/auth/register", json={
        "username": "admin1", "email": "admin1@test.com", "password": "AdminPass123", "role": "admin"
    })
    check("register admin", r.status_code == 201, r.text)

    r = client.post("/api/auth/register", json={
        "username": "author1", "email": "author1@test.com", "password": "AuthorPass123", "role": "author"
    })
    check("register author", r.status_code == 201, r.text)

    r = client.post("/api/auth/register", json={
        "username": "author2", "email": "author2@test.com", "password": "AuthorPass123", "role": "author"
    })
    check("register author2", r.status_code == 201, r.text)

    r = client.post("/api/auth/register", json={
        "username": "user1", "email": "user1@test.com", "password": "UserPass123", "role": "user"
    })
    check("register plain user", r.status_code == 201, r.text)

    # --- Login ---
    def login(username, password):
        r = client.post("/api/auth/login", json={"username": username, "password": password})
        check(f"login {username}", r.status_code == 200, r.text)
        return r.json()["access_token"]

    admin_token = login("admin1", "AdminPass123")
    author_token = login("author1", "AuthorPass123")
    author2_token = login("author2", "AuthorPass123")
    user_token = login("user1", "UserPass123")

    def auth(token):
        return {"Authorization": f"Bearer {token}"}

    # Wrong password
    r = client.post("/api/auth/login", json={"username": "admin1", "password": "wrong"})
    check("login wrong password rejected", r.status_code == 401, r.text)

    # --- /me ---
    r = client.get("/api/users/me", headers=auth(author_token))
    check("get /me", r.status_code == 200 and r.json()["username"] == "author1", r.text)

    # --- Category (author can create) ---
    r = client.post("/api/categories", json={"name": "Technology", "description": "Tech posts"}, headers=auth(author_token))
    check("create category as author", r.status_code == 201, r.text)
    cat_id = r.json()["id"]
    check("category slug generated", r.json()["slug"] == "technology", r.json().get("slug"))

    # Plain user cannot create category
    r = client.post("/api/categories", json={"name": "ShouldFail"}, headers=auth(user_token))
    check("plain user forbidden from creating category", r.status_code == 403, r.text)

    # --- Post creation ---
    r = client.post("/api/posts", json={
        "title": "Getting Started with FastAPI",
        "content": "FastAPI is a modern, fast web framework for building APIs with Python.",
        "excerpt": "An intro to FastAPI",
        "category_id": cat_id,
        "tag_names": ["python", "fastapi", "webdev"],
        "status": "published"
    }, headers=auth(author_token))
    check("create published post", r.status_code == 201, r.text)
    post1 = r.json()
    check("post slug generated", post1["slug"] == "getting-started-with-fastapi", post1.get("slug"))
    check("post has 3 tags", len(post1["tags"]) == 3, post1.get("tags"))
    check("published_at set", post1["published_at"] is not None)

    r = client.post("/api/posts", json={
        "title": "Draft Post About PostgreSQL",
        "content": "PostgreSQL is a powerful open-source relational database.",
        "tag_names": ["postgresql", "database"],
        "status": "draft"
    }, headers=auth(author_token))
    check("create draft post", r.status_code == 201, r.text)
    post2 = r.json()
    check("draft has no published_at", post2["published_at"] is None)

    # Plain user cannot create posts
    r = client.post("/api/posts", json={"title": "Nope", "content": "x", "tag_names": []}, headers=auth(user_token))
    check("plain user forbidden from creating post", r.status_code == 403, r.text)

    # author2 creates another published post for pagination/search testing
    r = client.post("/api/posts", json={
        "title": "Advanced Python Tips",
        "content": "Learn advanced python tricks and fastapi patterns.",
        "tag_names": ["python", "tips"],
        "status": "published"
    }, headers=auth(author2_token))
    check("author2 create published post", r.status_code == 201, r.text)
    post3 = r.json()

    # --- Public listing: only published visible to anon ---
    r = client.get("/api/posts")
    check("public list status 200", r.status_code == 200, r.text)
    data = r.json()
    titles = [p["title"] for p in data["items"]]
    check("draft NOT visible to public", "Draft Post About PostgreSQL" not in titles, titles)
    check("published post visible to public", "Getting Started with FastAPI" in titles, titles)
    check("pagination fields present", "total" in data and "total_pages" in data, data.keys())

    # --- Author sees own draft when requesting draft status ---
    r = client.get("/api/posts", params={"status": "draft"}, headers=auth(author_token))
    check("author sees own draft with status filter", any(p["title"] == "Draft Post About PostgreSQL" for p in r.json()["items"]), r.text)

    # --- Search by title/content/tag ---
    r = client.get("/api/posts", params={"search": "fastapi"})
    check("search 'fastapi' matches by title/content/tag", r.status_code == 200 and r.json()["total"] >= 2, r.text)

    r = client.get("/api/posts", params={"tag": "python"})
    check("filter by tag=python", r.status_code == 200 and r.json()["total"] >= 2, r.text)

    r = client.get("/api/posts", params={"search": "postgresql"})
    check("search 'postgresql' does not leak draft to public", all(p["title"] != "Draft Post About PostgreSQL" for p in r.json()["items"]), r.text)

    # --- Pagination ---
    r = client.get("/api/posts", params={"page": 1, "page_size": 1})
    check("pagination page_size=1 returns 1 item", len(r.json()["items"]) == 1, r.text)

    # --- Get single post + view count increments ---
    r1 = client.get(f"/api/posts/{post1['slug']}")
    vc1 = r1.json()["view_count"]
    r2 = client.get(f"/api/posts/{post1['slug']}")
    vc2 = r2.json()["view_count"]
    check("view_count increments on repeated views", vc2 == vc1 + 1, f"{vc1} -> {vc2}")

    # Author viewing own post should NOT increment
    r3 = client.get(f"/api/posts/{post1['slug']}", headers=auth(author_token))
    vc3 = r3.json()["view_count"]
    check("author's own view does not increment count", vc3 == vc2, f"{vc2} -> {vc3}")

    # --- Update post (only owner/admin) ---
    r = client.put(f"/api/posts/{post1['id']}", json={"title": "Getting Started with FastAPI (Updated)"}, headers=auth(author_token))
    check("owner can update post", r.status_code == 200 and r.json()["title"].endswith("(Updated)"), r.text)

    r = client.put(f"/api/posts/{post1['id']}", json={"title": "Hacked"}, headers=auth(author2_token))
    check("non-owner author forbidden from updating post", r.status_code == 403, r.text)

    r = client.put(f"/api/posts/{post1['id']}", json={"title": "Admin Edit"}, headers=auth(admin_token))
    check("admin can update any post", r.status_code == 200, r.text)

    # --- Publish draft ---
    r = client.patch(f"/api/posts/{post2['id']}/status", json={"status": "published"}, headers=auth(author_token))
    check("publish draft post", r.status_code == 200 and r.json()["status"] == "published", r.text)
    check("published_at stamped on publish", r.json()["published_at"] is not None)

    # --- Archive ---
    r = client.post(f"/api/posts/{post2['id']}/archive", headers=auth(author_token))
    check("archive post", r.status_code == 200 and r.json()["is_archived"] is True, r.text)

    # --- Comments (with rate limiting, nested replies) ---
    r = client.post(f"/api/posts/{post1['id']}/comments", json={"content": "Great post!"}, headers=auth(user_token))
    check("create top-level comment", r.status_code == 201, r.text)
    comment1 = r.json()

    r = client.post(f"/api/posts/{post1['id']}/comments", json={"content": "Thanks!", "parent_id": comment1["id"]}, headers=auth(author_token))
    check("create nested reply", r.status_code == 201, r.text)
    reply1 = r.json()
    check("reply has correct parent_id", reply1["parent_id"] == comment1["id"])

    r = client.post(f"/api/posts/{post1['id']}/comments", json={"content": "A deeper reply", "parent_id": reply1["id"]}, headers=auth(user_token))
    check("create deeply nested reply", r.status_code == 201, r.text)

    r = client.get(f"/api/posts/{post1['id']}/comments")
    check("list comments returns top-level with nested replies", r.status_code == 200, r.text)
    comments_list = r.json()
    check("top-level comment has nested replies array populated", len(comments_list) > 0 and len(comments_list[0]["replies"]) > 0, comments_list)

    # No auth -> comment fails
    r = client.post(f"/api/posts/{post1['id']}/comments", json={"content": "anon"})
    check("anonymous comment rejected (auth required)", r.status_code == 401, r.text)

    # --- Rate limiting on comments ---
    rate_hit = False
    for i in range(8):
        rr = client.post(f"/api/posts/{post1['id']}/comments", json={"content": f"spam {i}"}, headers=auth(user_token))
        if rr.status_code == 429:
            rate_hit = True
            break
    check("rate limiting kicks in on repeated comments", rate_hit)

    # --- Soft delete post ---
    r = client.delete(f"/api/posts/{post3['id']}", headers=auth(author2_token))
    check("soft delete post", r.status_code == 204, r.text)
    r = client.get(f"/api/posts/{post3['slug']}")
    check("soft-deleted post no longer publicly accessible", r.status_code == 404, r.text)

    # --- Role update by admin ---
    r = client.get("/api/users", headers=auth(admin_token))
    check("admin can list users", r.status_code == 200, r.text)
    user1_id = [u for u in r.json() if u["username"] == "user1"][0]["id"]

    r = client.patch(f"/api/users/{user1_id}/role", json={"role": "author"}, headers=auth(admin_token))
    check("admin can change user role", r.status_code == 200 and r.json()["role"] == "author", r.text)

    r = client.get("/api/users", headers=auth(user_token))
    check("non-admin forbidden from listing users", r.status_code == 403, r.text)

    # --- Tags list ---
    r = client.get("/api/tags")
    check("list tags", r.status_code == 200 and len(r.json()) >= 3, r.text)

    # --- Token refresh ---
    r = client.post("/api/auth/login", json={"username": "author1", "password": "AuthorPass123"})
    refresh_token = r.json()["refresh_token"]
    r = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    check("refresh token flow works", r.status_code == 200 and "access_token" in r.json(), r.text)

    print("\n" + "=" * 50)
    if FAILURES:
        print(f"{len(FAILURES)} CHECK(S) FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
