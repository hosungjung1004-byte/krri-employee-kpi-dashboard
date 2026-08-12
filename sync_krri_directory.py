"""KRRI 공식 조직도에서 공개된 소속·이름·직위만 동기화한다."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.krri.re.kr/web/contents/krri030801.do"
OUTPUT = Path(__file__).resolve().parent / "data" / "krri_directory.json"


def clean(value: str) -> str:
    return " ".join(value.split())


def main() -> None:
    response = requests.get(BASE_URL, timeout=30)
    response.raise_for_status()
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    organizations = []
    seen_codes = set()
    for anchor in soup.select('[onclick*="fn_goList"]'):
        match = re.search(r"fn_goList\('([^']+)'\)", anchor.get("onclick", ""))
        name = clean(anchor.get_text(" ", strip=True))
        if match and name and match.group(1) not in seen_codes:
            seen_codes.add(match.group(1))
            organizations.append({"code": match.group(1), "name": name})

    division_codes = {item["code"]: item["name"] for item in organizations if item["name"].endswith("본부")}
    members = []
    seen_members = set()
    for organization in organizations:
        detail = requests.get(
            BASE_URL,
            params={"code": organization["code"], "schM": "list", "viewCount": 500},
            timeout=30,
        )
        detail.raise_for_status()
        detail.encoding = "utf-8"
        page = BeautifulSoup(detail.text, "html.parser")
        for row in page.select("table tbody tr"):
            cells = [clean(cell.get_text(" ", strip=True)) for cell in row.select("th,td")]
            if len(cells) < 3 or cells[0] == "검색 결과가 없습니다.":
                continue
            department, name, position = cells[:3]
            division = next(
                (division_name for code, division_name in sorted(division_codes.items(), key=lambda item: len(item[0]), reverse=True) if organization["code"].startswith(code)),
                organization["name"],
            )
            key = (department, name, position)
            if key not in seen_members:
                seen_members.add(key)
                members.append({"division": division, "department": department, "name": name, "position": position})

    payload = {
        "source": BASE_URL,
        "retrieved_at": date.today().isoformat(),
        "organizations": organizations,
        "members": sorted(members, key=lambda item: (item["division"], item["department"], item["position"] != "본부장", item["name"])),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {len(organizations)} organizations and {len(members)} public members to {OUTPUT}")


if __name__ == "__main__":
    main()
