"""账单测试：新增 / 列表 / 删除 / 权限 / 分摊明细。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import apply_and_approve, create_post, create_room, room_member_ids


def test_create_bill_splits_evenly(client: TestClient, make_user) -> None:
    owner = make_user("user1")
    m2 = make_user("user2")
    m3 = make_user("user3")
    post = create_post(client, owner["headers"], need_count=5)
    room = create_room(client, owner["headers"], post["id"])
    apply_and_approve(client, owner["headers"], m2["headers"], room["id"])
    apply_and_approve(client, owner["headers"], m3["headers"], room["id"])
    member_ids = room_member_ids(client, owner["headers"], room["id"])

    resp = client.post(
        f"/api/rooms/{room['id']}/bills",
        headers=owner["headers"],
        json={
            "amount_cents": 10000,
            "note": "晚饭",
            "participant_member_ids": list(member_ids.values()),
        },
    )
    assert resp.status_code == 201, resp.text
    bill = resp.json()
    assert bill["payer_id"] == owner["id"]
    assert sum(share["amount_cents"] for share in bill["shares"]) == 10000
    assert len(bill["shares"]) == 3


def test_bill_amount_must_be_positive(client: TestClient, make_user) -> None:
    owner = make_user("user1")
    post = create_post(client, owner["headers"], need_count=2)
    room = create_room(client, owner["headers"], post["id"])
    member_ids = room_member_ids(client, owner["headers"], room["id"])

    resp = client.post(
        f"/api/rooms/{room['id']}/bills",
        headers=owner["headers"],
        json={"amount_cents": 0, "participant_member_ids": list(member_ids.values())},
    )
    assert resp.status_code == 422


def test_pending_member_cannot_create_bill(client: TestClient, make_user) -> None:
    """B4：pending 成员记账被拒（403），且账单未被创建。"""
    owner = make_user("user1")
    applicant = make_user("user2")
    post = create_post(client, owner["headers"], need_count=3)
    room = create_room(client, owner["headers"], post["id"])
    req = client.post(f"/api/rooms/{room['id']}/join-requests", headers=applicant["headers"])
    assert req.status_code == 201
    applicant_member_id = req.json()["id"]

    resp = client.post(
        f"/api/rooms/{room['id']}/bills",
        headers=applicant["headers"],
        json={"amount_cents": 500, "participant_member_ids": [applicant_member_id]},
    )
    assert resp.status_code == 403
    assert client.get(f"/api/rooms/{room['id']}/bills", headers=owner["headers"]).json() == []


def test_participant_must_be_joined_member(client: TestClient, make_user) -> None:
    owner = make_user("user1")
    applicant = make_user("user2")
    post = create_post(client, owner["headers"], need_count=3)
    room = create_room(client, owner["headers"], post["id"])
    req = client.post(f"/api/rooms/{room['id']}/join-requests", headers=applicant["headers"])
    pending_id = req.json()["id"]

    resp = client.post(
        f"/api/rooms/{room['id']}/bills",
        headers=owner["headers"],
        json={"amount_cents": 500, "participant_member_ids": [pending_id]},
    )
    assert resp.status_code == 403


def test_delete_bill_only_by_owner(client: TestClient, make_user) -> None:
    owner = make_user("user1")
    member = make_user("user2")
    post = create_post(client, owner["headers"], need_count=3)
    room = create_room(client, owner["headers"], post["id"])
    apply_and_approve(client, owner["headers"], member["headers"], room["id"])
    member_ids = room_member_ids(client, owner["headers"], room["id"])

    created = client.post(
        f"/api/rooms/{room['id']}/bills",
        headers=owner["headers"],
        json={"amount_cents": 900, "participant_member_ids": list(member_ids.values())},
    )
    bill_id = created.json()["id"]

    assert (
        client.delete(f"/api/rooms/{room['id']}/bills/{bill_id}", headers=member["headers"]).status_code
        == 403
    )
    assert (
        client.delete(f"/api/rooms/{room['id']}/bills/{bill_id}", headers=owner["headers"]).status_code
        == 204
    )
