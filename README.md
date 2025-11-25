# Action Bundle Manager

장비 문제 대응을 위한 액션 번들 관리 웹 애플리케이션입니다. CSV 기반으로 데이터를 관리하며, 여러 데이터 세트를 탭으로 전환하여 사용할 수 있습니다.

## 주요 기능

- **다중 데이터 세트 지원**: 여러 세트의 번들을 독립적으로 관리 (세트 A, 세트 B 등)
- **액션 번들 관리**: 장비 문제 대응을 위한 액션 번들을 생성, 수정, 삭제
- **명령어 분해**: Command 필드에 여러 명령어를 입력하면 자동으로 개별 Command ID로 분해
- **명령어별 Description**: 각 명령어마다 Description을 별도로 관리
- **링크 관리**: 번들 또는 특정 명령어에 참고 링크를 여러 개 등록 가능
- **검색 기능**: Bundle Name과 Keywords로 검색, 키워드 후보 클릭으로 빠른 검색
- **CSV 가져오기/내보내기**: 메인 CSV, 메모 CSV, 링크 CSV를 각각 가져오고 내보낼 수 있음

## 기술 스택

- **Backend**: FastAPI
- **Storage**: CSV 파일 기반
- **Frontend**: Jinja2 Templates
- **Python**: 3.11+

## 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/KipCod/autoap.git
cd autoap
```

### 2. Conda 가상환경 생성 및 활성화

```bash
conda create -n autoap python=3.11 -y
conda activate autoap
```

### 3. 의존성 패키지 설치

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

### 방법 3: 직접 실행

```bash
python app/main.py
```

애플리케이션이 실행되면 브라우저에서 `http://127.0.0.1:8000`으로 접속하세요.

## 데이터 저장 구조

애플리케이션은 CSV 파일 기반으로 데이터를 저장합니다. 각 데이터 세트마다 3개의 CSV 파일이 사용됩니다:

- **메인 CSV**: 번들 기본 정보 (ID, Part, Bundle Name, Command, Keywords)
- **메모 CSV**: 각 명령어별 Description, Memo, OneNote Link
- **링크 CSV**: 번들 또는 명령어에 연결된 참고 링크들

데이터 세트 구성은 `app/datasets.json` 파일에서 관리합니다. 이 파일을 수정하여 세트 이름, 파일명을 변경하거나 새 세트를 추가할 수 있습니다.

## CSV 파일 형식

### 메인 CSV

다음 컬럼을 포함합니다:

- **ID**: 액션 번들 고유 ID
- **Part**: 부품/영역
- **Bundle Name**: 번들 이름
- **Command**: 명령어 (여러 줄 가능, 각 줄이 개별 명령어로 분해됨)
- **Keywords**: 키워드 (검색에 사용, 쉼표로 구분)

### 메모 CSV

다음 컬럼을 포함합니다:

- **ID**: 액션 번들 ID (메인 CSV의 ID와 연결)
- **Command ID**: 명령어 순서 (1부터 시작)
- **Command Text**: 명령어 텍스트
- **Description**: 해당 명령어에 대한 설명/의도
- **Memo text**: 실행 중 생긴 메모나 관찰 내용
- **onenote link**: OneNote 링크 URL

### 링크 CSV

다음 컬럼을 포함합니다:

- **ID**: 링크 고유 ID
- **Bundle ID**: 연결된 번들 ID (선택)
- **Command ID**: 연결된 명령어 순서 (선택, Bundle ID와 함께 사용)
- **URL**: 링크 URL
- **Description**: 링크 설명
- **Tags**: 태그 (쉼표로 구분)

## 데이터 세트 구성

데이터 세트는 `app/datasets.json` 파일에서 관리합니다. 기본적으로 "세트 A"와 "세트 B" 두 개의 세트가 포함되어 있습니다.

### 세트 추가/수정 방법

1. `app/datasets.json` 파일을 엽니다
2. 필요한 만큼 객체를 추가하거나 기존 값을 수정합니다
3. `id`: URL 파라미터와 파일명 접두사로 사용 (영문 소문자/숫자 조합 권장)
4. `label`: 화면 상단 탭에 표시될 이름
5. `*_csv`: `app/` 디렉터리를 기준으로 한 상대 경로
6. FastAPI 서버를 재시작하면 새 설정이 반영됩니다

예시:

```json
{
  "datasets": [
    {
      "id": "set_a",
      "label": "세트 A",
      "main_csv": "set_a_main.csv",
      "memo_csv": "set_a_memos.csv",
      "link_csv": "set_a_links.csv"
    },
    {
      "id": "set_b",
      "label": "세트 B",
      "main_csv": "set_b_main.csv",
      "memo_csv": "set_b_memos.csv",
      "link_csv": "set_b_links.csv"
    }
  ]
}
```

## 주요 기능 설명

### 1. 데이터 세트 전환

- 홈 화면 상단의 탭에서 원하는 데이터 세트를 선택합니다
- 각 세트는 독립적인 CSV 파일 세트를 사용합니다

### 2. 액션 번들 생성

1. 홈 화면에서 "+ New Bundle" 링크 클릭 또는 `/bundle/new` 접속
2. Part, Bundle Name (필수), Command, Keywords 입력
3. Command 필드에 여러 명령어를 줄바꿈으로 구분하여 입력
4. 저장하면 자동으로 각 명령어가 개별 Command ID로 분해되어 메모 CSV에 저장됨

### 3. 액션 번들 수정

1. 번들 카드를 클릭하여 상세 페이지로 이동
2. 상단 폼에서 Part, Bundle Name, Keywords, Command 수정
3. Command 필드가 변경되면 자동으로 메모 항목도 동기화됨

### 4. 메모 및 Description 관리

1. 번들 상세 페이지의 "Command Memos" 섹션에서 각 명령어별로 관리
2. **Description**: 해당 명령어에 대한 설명/의도 입력
3. **Memo**: 실행 중 생긴 메모나 관찰 내용 입력
4. **OneNote Link**: 관련 문서 링크 입력
5. 모든 입력 완료 후 "Save Memo Updates" 버튼 클릭

### 5. 링크 관리

#### 번들 상세 페이지에서 링크 추가

1. 번들 상세 페이지 하단의 "참고 링크" 섹션으로 이동
2. URL, Description, Tags 입력
3. Command 선택: 특정 명령어에 연결하려면 드롭다운에서 선택 (선택사항)
4. "링크 추가" 버튼 클릭

#### 링크 탭에서 링크 추가

1. 홈 화면에서 "Links" 탭 클릭
2. URL, Description, Tags 입력 후 "링크 추가" 버튼 클릭
3. 번들에 연결되지 않은 일반 링크로 저장됨

### 6. 검색

1. 홈 화면 상단의 검색창에 Bundle Name 또는 Keywords 입력
2. 검색 결과가 실시간으로 필터링됨
3. **키워드 후보**: 검색창 아래에 자주 사용된 키워드가 칩 형태로 표시되며, 클릭하면 해당 키워드로 검색됨

### 7. CSV 내보내기

1. 헤더 메뉴에서 "Export Main CSV", "Export Memo CSV", "Export Link CSV" 링크 클릭
2. 파일명 앞에 현재 세트 ID가 자동으로 붙습니다 (예: `set_a_action_bundles.csv`)

## 프로젝트 구조

```
auto_ap/
├── app/
│   ├── __init__.py              # 패키지 초기화
│   ├── main.py                  # FastAPI 애플리케이션 메인
│   ├── models.py                # 데이터 모델 (ActionBundle, CommandMemo, LinkEntry, DatasetState)
│   ├── database.py              # CSV 파일 읽기/쓰기 로직
│   ├── services.py              # 비즈니스 로직 (명령어 분해, 키워드 추출 등)
│   ├── dataset_config.py        # 데이터 세트 설정 로더
│   ├── datasets.json            # 데이터 세트 정의 파일
│   ├── static/
│   │   └── styles.css           # 스타일시트
│   └── templates/
│       ├── layout.html          # 기본 레이아웃
│       ├── home.html            # 홈 페이지 (번들 목록, 링크 탭)
│       ├── bundle_form.html     # 번들 생성 폼
│       └── bundle_detail.html   # 번들 상세 페이지
├── requirements.txt             # Python 의존성 패키지
├── README.md                    # 이 파일
└── 사용_설명서.md              # 상세 사용 설명서
```

## API 엔드포인트

### 번들 관리
- `GET /`: 홈 페이지 (번들 목록 또는 링크 탭)
- `GET /bundle/new`: 새 번들 생성 폼
- `POST /bundle`: 번들 생성
- `GET /bundle/{bundle_id}`: 번들 상세 페이지
- `POST /bundle/{bundle_id}/update`: 번들 수정
- `POST /bundle/{bundle_id}/memos`: 메모 업데이트
- `POST /bundle/{bundle_id}/delete`: 번들 삭제

### 링크 관리
- `POST /links`: 링크 추가
- `POST /links/{link_id}/delete`: 링크 삭제

### CSV 내보내기
- `GET /export/main?dataset={dataset_id}`: 메인 CSV 내보내기
- `GET /export/memos?dataset={dataset_id}`: 메모 CSV 내보내기
- `GET /export/links?dataset={dataset_id}`: 링크 CSV 내보내기

## 주의사항

- 메인 CSV의 Command 필드를 수정하면, 해당 번들의 메모 항목이 자동으로 동기화됩니다
- 명령어가 삭제되면 해당 Command ID의 메모도 함께 삭제됩니다
- Description은 번들 단위가 아니라 각 명령어별로 관리됩니다
- 각 데이터 세트는 독립적인 CSV 파일 세트를 사용하므로, 세트 간 데이터는 공유되지 않습니다
- `app/datasets.json` 파일을 수정한 후에는 서버를 재시작해야 변경사항이 반영됩니다

## 문제 해결

### ImportError: attempted relative import with no known parent package

이 오류는 이전 버전에서 `python app/main.py`처럼 직접 실행할 때 발생했지만, 현재 버전에서는 자동으로 처리됩니다. 다음 방법 중 하나를 사용하세요:

```bash
# 방법 1: uvicorn 사용 (권장)
uvicorn app.main:app --reload

# 방법 2: Python 모듈로 실행
python -m app.main

# 방법 3: 직접 실행 (자동으로 import 경로 처리)
python app/main.py
```

### CSV 파일이 생성되지 않아요

- `app/datasets.json` 파일이 올바르게 설정되어 있는지 확인하세요
- 첫 번들을 생성하면 자동으로 CSV 파일이 생성됩니다
- 파일 권한 문제가 있는지 확인하세요

### 세트가 표시되지 않아요

- `app/datasets.json` 파일 형식이 올바른지 확인하세요
- 서버를 재시작했는지 확인하세요
- JSON 파일에 최소 1개의 세트가 정의되어 있어야 합니다

## 상세 사용 설명서

더 자세한 사용 방법은 `사용_설명서.md` 파일을 참고하세요.

## 라이선스

이 프로젝트는 내부 사용을 위한 것입니다.
