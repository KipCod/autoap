from typing import Dict, List, Tuple
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# 직접 실행과 모듈 실행 모두 지원
try:
    from .dataset_config import DatasetDefinition, VersionDefinition, load_dataset_definitions, load_app_config
    from .database import get_all_data, save_all_data
    from .models import ActionBundle, DatasetState, LinkEntry
    from .services import (
        get_next_bundle_id,
        get_next_link_id,
        keyword_candidates,
        normalize_commands,
        sync_memos,
    )
    from .link_tree import (
        build_keyword_tree,
        load_tagged_database,
        save_tagged_database,
        get_procedures_by_tag,
        search_procedures_by_title,
        TreeNode,
        tree_node_to_dict,
        build_networkx_graph,
        graph_to_visjs_json,
    )
except ImportError:
    # 직접 실행 시 (python app/main.py)
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from dataset_config import DatasetDefinition, VersionDefinition, load_dataset_definitions, load_app_config
    from database import get_all_data, save_all_data
    from models import ActionBundle, DatasetState, LinkEntry
    from services import (
        get_next_bundle_id,
        get_next_link_id,
        keyword_candidates,
        normalize_commands,
        sync_memos,
    )
    from link_tree import (
        build_keyword_tree,
        load_tagged_database,
        save_tagged_database,
        get_procedures_by_tag,
        search_procedures_by_title,
        TreeNode,
        tree_node_to_dict,
        build_networkx_graph,
        graph_to_visjs_json,
    )

# 절대 경로로 static 폴더 설정
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="Action Bundle Manager")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

DATASET_DEFINITIONS: List[DatasetDefinition] = load_dataset_definitions()
DATASET_MAP: Dict[str, DatasetDefinition] = {dataset.id: dataset for dataset in DATASET_DEFINITIONS}
DEFAULT_DATASET_ID = DATASET_DEFINITIONS[0].id
APP_CONFIG = load_app_config()

# 메모리 내 데이터 저장소 (세트별)
_dataset_state: Dict[str, DatasetState] = {}


def _load_data() -> None:
    """각 세트의 CSV 데이터를 메모리에 로드"""
    for definition in DATASET_DEFINITIONS:
        bundles, memos_by_action, links = get_all_data(
            definition.main_csv, definition.memo_csv, definition.link_csv
        )
        # 버전 구조에서는 tagged_database는 버전 선택 시 로드
        _dataset_state[definition.id] = DatasetState(
            bundles=bundles,
            memos_by_action=memos_by_action,
            links=links,
            tagged_database=[],
        )


def _get_dataset(dataset_id: str | None) -> Tuple[str, DatasetDefinition, DatasetState]:
    """dataset 식별자를 검증하고 상태 반환"""
    resolved_id = dataset_id or DEFAULT_DATASET_ID
    if resolved_id not in DATASET_MAP:
        raise HTTPException(status_code=404, detail="Dataset not found")
    state = _dataset_state.get(resolved_id)
    if state is None:
        definition = DATASET_MAP[resolved_id]
        bundles, memos_by_action, links = get_all_data(
            definition.main_csv, definition.memo_csv, definition.link_csv
        )
        # 버전 구조에서는 tagged_database는 버전 선택 시 로드
        state = DatasetState(
            bundles=bundles,
            memos_by_action=memos_by_action,
            links=links,
            tagged_database=[],
        )
        _dataset_state[resolved_id] = state
    return resolved_id, DATASET_MAP[resolved_id], state


def _layout_context(dataset_id: str, extra: dict, view: str = "bundles") -> dict:
    context = dict(extra)
    context.update(
        {
            "datasets": DATASET_DEFINITIONS,
            "active_dataset_id": dataset_id,
            "active_dataset": DATASET_MAP.get(dataset_id),
            "current_view": view,
            "app_title": APP_CONFIG.get("app_title", "CoSy AP Manager"),
            "tab_names": APP_CONFIG.get("tab_names", {"bundles": "APs", "links": "Links"}),
        }
    )
    return context


def _merge_tags(*parts: str) -> str:
    tokens: List[str] = []
    for part in parts:
        if not part:
            continue
        for raw in part.split(","):
            cleaned = raw.strip()
            if cleaned and cleaned not in tokens:
                tokens.append(cleaned)
    return ", ".join(tokens)


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _save_dataset(dataset_id: str) -> None:
    """해당 세트의 데이터를 CSV에 저장"""
    definition = DATASET_MAP[dataset_id]
    state = _dataset_state.get(dataset_id)
    if state is None:
        return
    save_all_data(
        definition.main_csv,
        definition.memo_csv,
        definition.link_csv,
        state.bundles,
        state.memos_by_action,
        state.links,
    )


@app.on_event("startup")
def on_startup() -> None:
    """앱 시작 시 CSV 파일 자동 로드"""
    _load_data()


@app.get("/", response_class=HTMLResponse)
def read_home(
    request: Request,
    dataset: str | None = None,
    version: str | None = None,
    query: str | None = None,
    view: str = "bundles",
) -> HTMLResponse:
    """홈 페이지 - 번들 목록 표시"""
    dataset_id, _, state = _get_dataset(dataset)
    view = view if view in {"bundles", "links"} else "bundles"
    all_bundles = list(state.bundles.values())
    all_bundles.sort(key=lambda b: b.id or 0, reverse=True)

    bundles_list = all_bundles
    # 검색 필터링
    if query:
        query_lower = query.lower()
        bundles_list = [
            bundle
            for bundle in all_bundles
            if query_lower in bundle.bundle_name.lower() or query_lower in bundle.keywords.lower()
        ]
    
    bundle_lookup = {bundle.id: bundle for bundle in all_bundles}
    bundle_cards = [
        {"bundle": bundle, "commands": normalize_commands(bundle.command_text)}
        for bundle in bundles_list
    ]

    keyword_pool = keyword_candidates(state.bundles)

    link_rows = []
    for link in sorted(state.links.values(), key=lambda link: link.id or 0):
        bundle = bundle_lookup.get(link.bundle_id)
        command_label = None
        if bundle and link.command_order:
            memos = state.memos_by_action.get(bundle.id or 0, [])
            memo = next((m for m in memos if m.command_order == link.command_order), None)
            if memo:
                command_label = memo.command_text
        link_rows.append({"entry": link, "bundle": bundle, "command_label": command_label})
    
    # Links 탭용 데이터 로드
    link_tree_data = None
    other_keywords_data = None
    tagged_database = []
    search_query = None
    active_version = None
    hardware_graph_data = None
    active_dataset = DATASET_MAP.get(dataset_id)
    
    if view == "links" and active_dataset:
        # 버전 선택 처리
        version_id = version or (active_dataset.versions[0].id if active_dataset.versions else None)
        if version_id:
            for ver in active_dataset.versions:
                if ver.id == version_id:
                    active_version = ver
                    break
        
        # 버전이 있으면 해당 버전의 데이터 로드
        if active_version:
            # tagged_database 로드
            if active_version.tagged_database_csv:
                tagged_database = load_tagged_database(active_version.tagged_database_csv)
            
            # tree.txt 파싱 및 프로시저 매칭
            if active_version.tree_txt:
                tree_nodes = build_keyword_tree(active_version.tree_txt)
                link_tree_data = [tree_node_to_dict(node, tagged_database) for node in tree_nodes]
                
                # networkx 그래프 생성
                graph = build_networkx_graph(tree_nodes)
                if graph:
                    hardware_graph_data = graph_to_visjs_json(graph)
                
                # networkx 그래프 생성
                graph = build_networkx_graph(tree_nodes)
                if graph:
                    hardware_graph_data = graph_to_visjs_json(graph)
            
            # other_keywords.txt 파싱 및 프로시저 매칭
            if active_version.other_keywords_txt:
                other_nodes = build_keyword_tree(active_version.other_keywords_txt)
                other_keywords_data = [tree_node_to_dict(node, tagged_database) for node in other_nodes]
        
        # 검색 쿼리 처리
        search_query = request.query_params.get("search_query", "")
    
    # 이미지 URL 생성
    image_url = None
    if active_dataset and active_dataset.image_paths and len(active_dataset.image_paths) > 0:
        image_path = Path(active_dataset.image_paths[0])
        if image_path.is_absolute():
            # 절대 경로인 경우 /image/{dataset_id} 엔드포인트 사용
            image_url = f"/image/{dataset_id}"
        else:
            # 상대 경로인 경우 /static/... 사용
            image_url = f"/static/{active_dataset.image_paths[0]}"
    
    return templates.TemplateResponse(
        "home.html",
        _layout_context(
            dataset_id,
            {
                "request": request,
                "bundles": bundle_cards,
                "links": link_rows,
                "query": query or "",
                "view": view,
                "keyword_candidates": keyword_pool,
                "bundle_options": all_bundles,
                "image_url": image_url,
                "link_tree_data": link_tree_data,
                "other_keywords_data": other_keywords_data,
                "tagged_database": tagged_database,
                "search_query": search_query,
                "active_version": active_version,
                "version": version,
                "hardware_graph_data": hardware_graph_data,
            },
            view=view,
        ),
    )


@app.get("/bundle/new", response_class=HTMLResponse)
def new_bundle_form(request: Request, dataset: str | None = None) -> HTMLResponse:
    """새 번들 생성 폼"""
    dataset_id, _, _ = _get_dataset(dataset)
    return templates.TemplateResponse(
        "bundle_form.html",
        _layout_context(
            dataset_id,
            {
                "request": request,
                "bundle": None,
            },
        ),
    )


@app.post("/bundle")
def create_bundle(
    dataset: str = Form(...),
    part: str = Form(...),
    bundle_name: str = Form(...),
    command_text: str = Form(""),
    keywords: str = Form(""),
) -> RedirectResponse:
    """새 번들 생성"""
    dataset_id, _, state = _get_dataset(dataset)
    bundle_id = get_next_bundle_id(state.bundles)
    
    bundle = ActionBundle(
        id=bundle_id,
        part=part,
        bundle_name=bundle_name,
        command_text=command_text.strip(),
        keywords=keywords,
    )
    
    # 명령어를 메모로 동기화
    sync_memos(bundle, bundle.command_text)
    
    state.bundles[bundle_id] = bundle
    state.memos_by_action[bundle_id] = bundle.memos
    
    _save_dataset(dataset_id)
    
    return RedirectResponse(url=f"/bundle/{bundle_id}?dataset={dataset_id}", status_code=303)


@app.get("/bundle/{bundle_id}", response_class=HTMLResponse)
def bundle_detail(bundle_id: int, request: Request, dataset: str | None = None) -> HTMLResponse:
    """번들 상세 페이지"""
    dataset_id, _, state = _get_dataset(dataset)
    bundle = state.bundles.get(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    
    memos = sorted(bundle.memos, key=lambda memo: memo.command_order)
    command_list = normalize_commands(bundle.command_text)
    
    bundle_links: List[dict] = []
    for link in sorted(state.links.values(), key=lambda l: l.id or 0):
        if link.bundle_id != bundle_id:
            continue
        command_label = None
        if link.command_order:
            memo = next((m for m in memos if m.command_order == link.command_order), None)
            if memo:
                command_label = memo.command_text
        bundle_links.append({"entry": link, "command_label": command_label})

    return templates.TemplateResponse(
        "bundle_detail.html",
        _layout_context(
            dataset_id,
            {
                "request": request,
                "bundle": bundle,
                "memos": memos,
                "commands": command_list,
                "bundle_links": bundle_links,
            },
        ),
    )


@app.post("/bundle/{bundle_id}/update")
def update_bundle(
    bundle_id: int,
    dataset: str = Form(...),
    part: str = Form(...),
    bundle_name: str = Form(...),
    command_text: str = Form(""),
    keywords: str = Form(""),
) -> RedirectResponse:
    """번들 수정"""
    dataset_id, _, state = _get_dataset(dataset)
    bundle = state.bundles.get(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    
    bundle.part = part
    bundle.bundle_name = bundle_name
    bundle.command_text = command_text.strip()
    bundle.keywords = keywords
    
    # 명령어 변경 시 메모 동기화
    sync_memos(bundle, bundle.command_text)
    state.memos_by_action[bundle_id] = bundle.memos
    
    _save_dataset(dataset_id)
    
    return RedirectResponse(url=f"/bundle/{bundle_id}?dataset={dataset_id}", status_code=303)


@app.post("/bundle/{bundle_id}/memos")
async def update_memos(bundle_id: int, request: Request) -> RedirectResponse:
    """메모 업데이트"""
    form = await request.form()
    dataset_key = form.get("dataset")
    dataset_id, _, state = _get_dataset(dataset_key)
    bundle = state.bundles.get(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    
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
        elif key.startswith("description_"):
            order = int(key.split("_")[-1])
            memo_payload.append(
                {
                    "command_order": order,
                    "description": value,
                }
            )
    
    # 메모 업데이트
    aggregated: Dict[int, Dict[str, str]] = {}
    for payload in memo_payload:
        order = int(payload["command_order"])
        aggregated.setdefault(order, {}).update(payload)

    for order, payload in aggregated.items():
        memo = next((m for m in bundle.memos if m.command_order == order), None)
        if memo:
            if "memo_text" in payload:
                memo.memo_text = payload.get("memo_text", "")
                memo.onenote_link = payload.get("onenote_link", "")
            if "description" in payload:
                memo.description = payload.get("description", "")
    
    state.memos_by_action[bundle_id] = bundle.memos
    _save_dataset(dataset_id)
    
    return RedirectResponse(url=f"/bundle/{bundle_id}?dataset={dataset_id}", status_code=303)


@app.post("/bundle/{bundle_id}/delete")
def delete_bundle(bundle_id: int, dataset: str = Form(...)) -> RedirectResponse:
    """번들 삭제"""
    dataset_id, _, state = _get_dataset(dataset)
    if bundle_id in state.bundles:
        del state.bundles[bundle_id]
    if bundle_id in state.memos_by_action:
        del state.memos_by_action[bundle_id]
    
    _save_dataset(dataset_id)
    
    return RedirectResponse(url=f"/?dataset={dataset_id}", status_code=303)


@app.post("/links")
async def create_links(request: Request) -> RedirectResponse:
    """여러 링크를 한 번에 추가"""
    form = await request.form()
    dataset_id, _, state = _get_dataset(form.get("dataset"))
    return_to = form.get("return_to") or f"/?dataset={dataset_id}&view=links"
    global_tags = form.get("global_tags", "").strip()
    default_bundle = form.get("bundle_default", "")
    default_command = form.get("command_default", "")
    entries_blob = form.get("link_entries", "") or ""

    lines = [line.strip() for line in entries_blob.replace("\r", "").split("\n")]
    next_link_id = get_next_link_id(state.links)
    created = 0

    for line in lines:
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        url = parts[0] if parts else ""
        if not url:
            continue
        description = parts[1] if len(parts) >= 2 else ""
        per_tags = parts[2] if len(parts) >= 3 else ""
        per_bundle = parts[3] if len(parts) >= 4 else ""
        per_command = parts[4] if len(parts) >= 5 else ""

        bundle_value = _parse_optional_int(per_bundle or default_bundle)
        command_value = _parse_optional_int(per_command or default_command)
        tags = _merge_tags(per_tags, global_tags)

        entry = LinkEntry(
            id=next_link_id,
            bundle_id=bundle_value,
            command_order=command_value,
            url=url,
            description=description,
            tags=tags,
        )
        state.links[next_link_id] = entry
        next_link_id += 1
        created += 1

    if created:
        _save_dataset(dataset_id)

    return RedirectResponse(url=return_to, status_code=303)


@app.post("/links/{link_id}/delete")
def delete_link(link_id: int, dataset: str = Form(...), return_to: str | None = Form(None)) -> RedirectResponse:
    """링크 삭제"""
    dataset_id, _, state = _get_dataset(dataset)
    if link_id in state.links:
        del state.links[link_id]
        _save_dataset(dataset_id)
    target = return_to or f"/?dataset={dataset_id}&view=links"
    return RedirectResponse(url=target, status_code=303)


@app.get("/export/main")
def export_main(dataset: str | None = None) -> StreamingResponse:
    """메인 CSV 내보내기"""
    import io
    import csv

    dataset_id, _, state = _get_dataset(dataset)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["ID", "Part", "Bundle Name", "Command", "Keywords"])
    writer.writeheader()
    
    for bundle_id in sorted(state.bundles.keys()):
        bundle = state.bundles[bundle_id]
        writer.writerow(
            {
                "ID": bundle.id or "",
                "Part": bundle.part,
                "Bundle Name": bundle.bundle_name,
                "Command": bundle.command_text,
                "Keywords": bundle.keywords,
            }
        )
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{dataset_id}_action_bundles.csv"'},
    )


@app.get("/export/memos")
def export_memos(dataset: str | None = None) -> StreamingResponse:
    """메모 CSV 내보내기"""
    import io
    import csv
    
    dataset_id, _, state = _get_dataset(dataset)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["ID", "Command ID", "Command Text", "Memo text", "onenote link"])
    writer.writeheader()
    
    for action_id in sorted(state.memos_by_action.keys()):
        memos = sorted(state.memos_by_action[action_id], key=lambda m: m.command_order)
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
        headers={"Content-Disposition": f'attachment; filename="{dataset_id}_command_memos.csv"'},
    )


@app.get("/export/links")
def export_links(dataset: str | None = None) -> StreamingResponse:
    """링크 CSV 내보내기"""
    import io
    import csv

    dataset_id, _, state = _get_dataset(dataset)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["ID", "URL", "Description", "Tags"])
    writer.writeheader()

    for link_id in sorted(state.links.keys()):
        link = state.links[link_id]
        writer.writerow(
            {
                "ID": link.id or "",
                "URL": link.url,
                "Description": link.description,
                "Tags": link.tags,
            }
        )

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{dataset_id}_links.csv"'},
    )


@app.get("/image/{dataset_id}")
def get_dataset_image(dataset_id: str) -> FileResponse:
    """데이터셋 이미지 제공"""
    if dataset_id not in DATASET_MAP:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    definition = DATASET_MAP[dataset_id]
    if not definition.image_paths or len(definition.image_paths) == 0:
        raise HTTPException(status_code=404, detail="Image not configured for this dataset")
    
    image_path = Path(definition.image_paths[0])
    
    # 절대 경로인 경우 직접 사용
    if image_path.is_absolute():
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Image file not found")
        return FileResponse(str(image_path))
    
    # 상대 경로인 경우 static 폴더 기준
    static_image_path = STATIC_DIR / definition.image_paths[0]
    if not static_image_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(str(static_image_path))


@app.get("/links/manage", response_class=HTMLResponse)
def manage_links_page(request: Request, dataset: str | None = None, version: str | None = None) -> HTMLResponse:
    """프로시저 관리 페이지"""
    dataset_id, definition, state = _get_dataset(dataset)
    
    # 버전 선택 처리
    version_id = version or (definition.versions[0].id if definition.versions else None)
    active_version = None
    if version_id:
        for ver in definition.versions:
            if ver.id == version_id:
                active_version = ver
                break
    
    # 모든 키워드 수집 (tree.txt + other_keywords.txt)
    all_keywords = set()
    tagged_database = []
    
    if active_version:
        if active_version.tree_txt:
            tree_nodes = build_keyword_tree(active_version.tree_txt)
            for node in tree_nodes:
                all_keywords.update(node.get_all_keywords())
        if active_version.other_keywords_txt:
            other_nodes = build_keyword_tree(active_version.other_keywords_txt)
            for node in other_nodes:
                all_keywords.update(node.get_all_keywords())
        if active_version.tagged_database_csv:
            tagged_database = load_tagged_database(active_version.tagged_database_csv)
    
    return templates.TemplateResponse(
        "manage_links.html",
        _layout_context(
            dataset_id,
            {
                "request": request,
                "tagged_database": tagged_database,
                "all_keywords": sorted(all_keywords),
                "active_version": active_version,
                "version": version,
            },
            view="links",
        ),
    )


@app.post("/links/update-procedure")
async def update_procedure(request: Request) -> RedirectResponse:
    """프로시저 태그 업데이트"""
    form = await request.form()
    dataset_id, definition, state = _get_dataset(form.get("dataset"))
    version_id = form.get("version", "")
    code = form.get("code", "").strip()
    new_tag = form.get("tag", "").strip()
    
    # 버전 찾기
    active_version = None
    if version_id:
        for ver in definition.versions:
            if ver.id == version_id:
                active_version = ver
                break
    
    if active_version and active_version.tagged_database_csv:
        # tagged_database 로드
        tagged_database = load_tagged_database(active_version.tagged_database_csv)
        
        # 프로시저 찾아서 태그 업데이트
        for entry in tagged_database:
            if entry.get("code") == code:
                entry["tag"] = new_tag
                break
        
        # 저장
        save_tagged_database(active_version.tagged_database_csv, tagged_database)
    
    return_url = f"/?dataset={dataset_id}&view=links"
    if version_id:
        return_url += f"&version={version_id}"
    return RedirectResponse(url=return_url, status_code=303)


@app.post("/links/add-procedure")
async def add_procedure(request: Request) -> RedirectResponse:
    """새 프로시저 추가"""
    form = await request.form()
    dataset_id, definition, state = _get_dataset(form.get("dataset"))
    version_id = form.get("version", "")
    
    code = form.get("code", "").strip()
    title = form.get("title", "").strip()
    link = form.get("link", "").strip()
    tag = form.get("tag", "").strip()
    
    # 버전 찾기
    active_version = None
    if version_id:
        for ver in definition.versions:
            if ver.id == version_id:
                active_version = ver
                break
    
    if code and title and link and active_version and active_version.tagged_database_csv:
        # tagged_database 로드
        tagged_database = load_tagged_database(active_version.tagged_database_csv)
        
        # 중복 체크
        existing_codes = {e.get("code") for e in tagged_database}
        if code not in existing_codes:
            tagged_database.append({
                "code": code,
                "title": title,
                "link": link,
                "tag": tag or "REST",
            })
            
            # 저장
            save_tagged_database(active_version.tagged_database_csv, tagged_database)
    
    return_url = f"/?dataset={dataset_id}&view=links"
    if version_id:
        return_url += f"&version={version_id}"
    return RedirectResponse(url=return_url, status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", reload=True)
