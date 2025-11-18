from datetime import date
from typing import Dict, List

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import get_all_data, save_all_data
from .models import ActionBundle, CommandMemo
from .services import get_next_bundle_id, normalize_commands, sync_memos, _parse_date

app = FastAPI(title="Action Bundle Manager")
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 메모리 내 데이터 저장소
_bundles: Dict[int, ActionBundle] = {}
_memos_by_action: Dict[int, List[CommandMemo]] = {}


def _load_data() -> None:
    """CSV 파일에서 데이터 로드"""
    global _bundles, _memos_by_action
    _bundles, _memos_by_action = get_all_data()


def _save_data() -> None:
    """데이터를 CSV 파일에 저장"""
    save_all_data(_bundles, _memos_by_action)


@app.on_event("startup")
def on_startup() -> None:
    """앱 시작 시 CSV 파일 자동 로드"""
    _load_data()


@app.get("/", response_class=HTMLResponse)
def read_home(request: Request, query: str | None = None) -> HTMLResponse:
    """홈 페이지 - 번들 목록 표시"""
    bundles_list = list(_bundles.values())
    
    # 검색 필터링
    if query:
        query_lower = query.lower()
        bundles_list = [
            bundle
            for bundle in bundles_list
            if query_lower in bundle.bundle_name.lower() or query_lower in bundle.keywords.lower()
        ]
    
    # 날짜순 정렬 (최신순)
    bundles_list.sort(key=lambda b: b.updated_date if isinstance(b.updated_date, date) else date.today(), reverse=True)
    
    return templates.TemplateResponse("home.html", {"request": request, "bundles": bundles_list, "query": query or ""})


@app.get("/bundle/new", response_class=HTMLResponse)
def new_bundle_form(request: Request) -> HTMLResponse:
    """새 번들 생성 폼"""
    return templates.TemplateResponse("bundle_form.html", {"request": request, "bundle": None})


@app.post("/bundle")
def create_bundle(
    part: str = Form(...),
    bundle_name: str = Form(...),
    command_text: str = Form(""),
    description: str = Form(""),
    keywords: str = Form(""),
    expected_outcome: str = Form(""),
    interpretation: str = Form(""),
    updated_date: str = Form(""),
    todo: str = Form(""),
) -> RedirectResponse:
    """새 번들 생성"""
    bundle_id = get_next_bundle_id(_bundles)
    
    bundle = ActionBundle(
        id=bundle_id,
        part=part,
        bundle_name=bundle_name,
        command_text=command_text.strip(),
        description=description,
        keywords=keywords,
        expected_outcome=expected_outcome,
        interpretation=interpretation,
        updated_date=_parse_date(updated_date),
        todo=todo,
    )
    
    # 명령어를 메모로 동기화
    sync_memos(bundle, bundle.command_text)
    
    _bundles[bundle_id] = bundle
    _memos_by_action[bundle_id] = bundle.memos
    
    _save_data()
    
    return RedirectResponse(url=f"/bundle/{bundle_id}", status_code=303)


@app.get("/bundle/{bundle_id}", response_class=HTMLResponse)
def bundle_detail(bundle_id: int, request: Request) -> HTMLResponse:
    """번들 상세 페이지"""
    bundle = _bundles.get(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    
    memos = sorted(bundle.memos, key=lambda memo: memo.command_order)
    command_list = normalize_commands(bundle.command_text)
    
    return templates.TemplateResponse(
        "bundle_detail.html",
        {"request": request, "bundle": bundle, "memos": memos, "commands": command_list},
    )


@app.post("/bundle/{bundle_id}/update")
def update_bundle(
    bundle_id: int,
    part: str = Form(...),
    bundle_name: str = Form(...),
    command_text: str = Form(""),
    description: str = Form(""),
    keywords: str = Form(""),
    expected_outcome: str = Form(""),
    interpretation: str = Form(""),
    updated_date: str = Form(""),
    todo: str = Form(""),
) -> RedirectResponse:
    """번들 수정"""
    bundle = _bundles.get(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    
    bundle.part = part
    bundle.bundle_name = bundle_name
    bundle.command_text = command_text.strip()
    bundle.description = description
    bundle.keywords = keywords
    bundle.expected_outcome = expected_outcome
    bundle.interpretation = interpretation
    bundle.updated_date = _parse_date(updated_date)
    bundle.todo = todo
    
    # 명령어 변경 시 메모 동기화
    sync_memos(bundle, bundle.command_text)
    _memos_by_action[bundle_id] = bundle.memos
    
    _save_data()
    
    return RedirectResponse(url=f"/bundle/{bundle_id}", status_code=303)


@app.post("/bundle/{bundle_id}/memos")
async def update_memos(bundle_id: int, request: Request) -> RedirectResponse:
    """메모 업데이트"""
    bundle = _bundles.get(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    
    form = await request.form()
    memo_payload: List[dict[str, str]] = []
    
    for key, value in form.multi_items():
        if key.startswith("memo_text_"):
            order = int(key.split("_")[-1])
            memo_payload.append(
                {
                    "command_order": order,
                    "memo_text": value,
                    "onenote_link": form.get(f"onenote_link_{order}", ""),
                }
            )
    
    # 메모 업데이트
    for payload in memo_payload:
        order = int(payload["command_order"])
        memo = next((m for m in bundle.memos if m.command_order == order), None)
        if memo:
            memo.memo_text = payload.get("memo_text", "")
            memo.onenote_link = payload.get("onenote_link", "")
    
    _memos_by_action[bundle_id] = bundle.memos
    _save_data()
    
    return RedirectResponse(url=f"/bundle/{bundle_id}", status_code=303)


@app.post("/bundle/{bundle_id}/delete")
def delete_bundle(bundle_id: int) -> RedirectResponse:
    """번들 삭제"""
    if bundle_id in _bundles:
        del _bundles[bundle_id]
    if bundle_id in _memos_by_action:
        del _memos_by_action[bundle_id]
    
    _save_data()
    
    return RedirectResponse(url="/", status_code=303)


@app.get("/export/main")
def export_main() -> StreamingResponse:
    """메인 CSV 내보내기"""
    from .database import save_bundles
    import io
    import csv
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["ID", "Part", "Bundle Name", "Command", "Description", "Keywords", "Expected Outcome", "Interpretation", "Updated Date", "Todo"])
    writer.writeheader()
    
    for bundle_id in sorted(_bundles.keys()):
        bundle = _bundles[bundle_id]
        writer.writerow(
            {
                "ID": bundle.id or "",
                "Part": bundle.part,
                "Bundle Name": bundle.bundle_name,
                "Command": bundle.command_text,
                "Description": bundle.description,
                "Keywords": bundle.keywords,
                "Expected Outcome": bundle.expected_outcome,
                "Interpretation": bundle.interpretation,
                "Updated Date": (
                    bundle.updated_date.isoformat()
                    if isinstance(bundle.updated_date, date)
                    else str(bundle.updated_date)
                    if bundle.updated_date
                    else ""
                ),
                "Todo": bundle.todo,
            }
        )
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="action_bundles.csv"'},
    )


@app.get("/export/memos")
def export_memos() -> StreamingResponse:
    """메모 CSV 내보내기"""
    import io
    import csv
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["ID", "Command ID", "Command Text", "Memo text", "onenote link"])
    writer.writeheader()
    
    for action_id in sorted(_memos_by_action.keys()):
        memos = sorted(_memos_by_action[action_id], key=lambda m: m.command_order)
        for memo in memos:
            writer.writerow(
                {
                    "ID": memo.action_id,
                    "Command ID": memo.command_order,
                    "Command Text": memo.command_text,
                    "Memo text": memo.memo_text,
                    "onenote link": memo.onenote_link,
                }
            )
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="command_memos.csv"'},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", reload=True)
