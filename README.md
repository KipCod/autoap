# Action Bundle Manager

장비 문제 대응을 위한 액션 번들 관리 웹 애플리케이션입니다. 메인 CSV와 메모 CSV 두 개의 파일을 연동하여 관리합니다.

## 주요 기능

- **액션 번들 관리**: 장비 문제 대응을 위한 액션 번들을 생성, 수정, 삭제
- **명령어 분해**: 메인 CSV의 Command 필드에 여러 명령어가 포함된 경우, 자동으로 개별 Command ID로 분해하여 메모 CSV에 저장
- **CSV 동기화**: 메인 CSV를 수정하면 대응하는 메모 CSV도 자동으로 동기화
- **검색 기능**: Bundle Name과 Keywords로 검색
- **CSV 가져오기/내보내기**: 메인 CSV와 메모 CSV를 각각 가져오고 내보낼 수 있음

## 기술 스택

- **Backend**: FastAPI
- **Database**: SQLite (SQLModel)
- **Frontend**: Jinja2 Templates
- **Python**: 3.11+

## 설치 방법

### 1. Conda 가상환경 생성 및 활성화

```bash
conda create -n autoap python=3.11 -y
conda activate autoap
```

### 2. 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

## 실행 방법

### 방법 1: uvicorn으로 직접 실행 (권장)

```bash
uvicorn app.main:app --reload
```

### 방법 2: Python 모듈로 실행

```bash
python -m app.main
```

애플리케이션이 실행되면 브라우저에서 `http://127.0.0.1:8000`으로 접속하세요.

## 데이터베이스

애플리케이션은 SQLite 데이터베이스를 사용하며, `app/data.db` 파일에 저장됩니다. 첫 실행 시 자동으로 생성됩니다.

## CSV 파일 형식

### 메인 CSV (action_bundles.csv)

다음 컬럼을 포함해야 합니다:

- **ID**: 액션 번들 고유 ID
- **Part**: 부품/영역
- **Bundle Name**: 번들 이름
- **Command**: 명령어 (여러 줄 가능, 각 줄이 개별 명령어로 분해됨)
- **Description**: 설명
- **Keywords**: 키워드 (검색에 사용)
- **Expected Outcome**: 예상 결과
- **Interpretation**: 해석
- **Updated Date**: 업데이트 날짜 (YYYY-MM-DD 형식)
- **Todo**: 할 일

### 메모 CSV (command_memos.csv)

다음 컬럼을 포함해야 합니다:

- **ID**: 액션 번들 ID (메인 CSV의 ID와 연결)
- **Command ID**: 명령어 순서 (1부터 시작)
- **Command Text**: 명령어 텍스트
- **Memo text**: 메모 텍스트
- **onenote link**: OneNote 링크

## 주요 기능 설명

### 1. 액션 번들 생성

1. 홈 화면에서 "Create the first one?" 링크 클릭 또는 `/bundle/new` 접속
2. 폼에 정보 입력
3. Command 필드에 여러 명령어를 줄바꿈으로 구분하여 입력
4. 저장하면 자동으로 각 명령어가 개별 Command ID로 분해되어 메모 CSV에 저장됨

### 2. 액션 번들 수정

1. 번들 카드를 클릭하여 상세 페이지로 이동
2. "Edit" 버튼 클릭
3. 정보 수정 후 저장
4. Command 필드가 변경되면 자동으로 메모 항목도 동기화됨

### 3. 메모 관리

1. 번들 상세 페이지에서 각 명령어별로 메모 텍스트와 OneNote 링크 입력 가능
2. 메모는 Command ID 순서대로 표시됨
3. 메모 수정 후 저장하면 데이터베이스에 반영됨

### 4. CSV 가져오기

1. 홈 화면에서 "Main CSV" 또는 "Memo CSV" 파일 선택
2. "Import" 버튼 클릭
3. 메인 CSV를 가져오면 ID가 일치하는 기존 항목은 업데이트되고, 새로운 항목은 생성됨
4. 메모 CSV를 가져오면 해당 액션 번들의 기존 메모가 모두 삭제되고 새로 가져온 메모로 교체됨

### 5. CSV 내보내기

1. 홈 화면에서 "Export Main CSV" 또는 "Export Memos CSV" 링크 클릭
2. CSV 파일이 다운로드됨

### 6. 검색

1. 홈 화면 상단의 검색창에 Bundle Name 또는 Keywords 입력
2. 검색 결과가 실시간으로 필터링됨

## 프로젝트 구조

```
auto_ap/
├── app/
│   ├── __init__.py          # 패키지 초기화
│   ├── main.py              # FastAPI 애플리케이션 메인
│   ├── models.py            # 데이터베이스 모델 (ActionBundle, CommandMemo)
│   ├── database.py          # 데이터베이스 설정 및 세션 관리
│   ├── services.py          # 비즈니스 로직 (CSV 가져오기/내보내기, 명령어 분해 등)
│   ├── data.db              # SQLite 데이터베이스 파일 (자동 생성)
│   ├── static/
│   │   └── styles.css       # 스타일시트
│   └── templates/
│       ├── layout.html      # 기본 레이아웃
│       ├── home.html        # 홈 페이지
│       ├── bundle_form.html # 번들 생성/수정 폼
│       └── bundle_detail.html # 번들 상세 페이지
├── requirements.txt         # Python 의존성 패키지
└── README.md               # 이 파일
```

## API 엔드포인트

- `GET /`: 홈 페이지 (번들 목록)
- `GET /bundle/new`: 새 번들 생성 폼
- `POST /bundle`: 번들 생성
- `GET /bundle/{bundle_id}`: 번들 상세 페이지
- `POST /bundle/{bundle_id}/update`: 번들 수정
- `POST /bundle/{bundle_id}/memos`: 메모 업데이트
- `POST /bundle/{bundle_id}/delete`: 번들 삭제
- `GET /export/main`: 메인 CSV 내보내기
- `GET /export/memos`: 메모 CSV 내보내기
- `POST /import/main`: 메인 CSV 가져오기
- `POST /import/memos`: 메모 CSV 가져오기

## 주의사항

- 메인 CSV의 Command 필드를 수정하면, 해당 번들의 메모 항목이 자동으로 동기화됩니다.
- 메모 CSV를 가져올 때는 기존 메모가 모두 삭제되고 새로 가져온 메모로 교체됩니다.
- ID가 일치하는 항목은 업데이트되고, 새로운 ID는 생성됩니다.

## 문제 해결

### ImportError: attempted relative import with no known parent package

이 오류는 `python app/main.py`처럼 직접 실행할 때 발생합니다. 다음 방법 중 하나를 사용하세요:

```bash
# 방법 1: uvicorn 사용 (권장)
uvicorn app.main:app --reload

# 방법 2: Python 모듈로 실행
python -m app.main
```

## 라이선스

이 프로젝트는 내부 사용을 위한 것입니다.

