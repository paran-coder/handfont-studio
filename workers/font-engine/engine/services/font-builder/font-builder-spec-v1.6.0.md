# Font Builder 한글 확장 명세 v1.6.0

## 변경 사항

- 현대 한글 완성형과 호환 자모를 `hangul-square` 수직 클래스에 배치
- 한글 advance width를 1000 units로 고정
- 목표 윤곽 수직 범위를 `-40~760`으로 설정
- 목표 가로 윤곽 최대 폭을 880 units로 제한
- 실제 윤곽 폭에 따라 좌우 여백을 균형 배치
- cmap을 기준으로 OS/2 Unicode Range와 CodePage Range를 계산
- 한글 포함 시 Unicode Range bit 56과 Korean Wansung CodePage bit 19 설정
- 출력 파일명을 CLI에서 지정할 수 있는 `--output-basename` 추가
- 한글 specimen과 고정폭 검증 추가

## 검증 조건

- 한글 cmap 수가 입력 음절 수와 일치
- 모든 한글 advance width가 1000
- 윤곽선이 em-square 수직 범위를 벗어나지 않음
- `glyf`, `cmap`, `head`, `hhea`, `hmtx`, `maxp`, `name`, `OS/2`, `post`, `loca` 존재
- 빈 윤곽선·음수 오른쪽 여백·렌더링 실패 0건
