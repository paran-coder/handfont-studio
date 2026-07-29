# HandFont Font Builder 알려진 한계 v1.5.0

## 데이터

- 전체 입력은 실제 손글씨가 아닌 합성 SVG다.
- 템플릿의 실제 기준선·안전 영역 정보가 아직 SVG manifest에 포함되지 않는다.

## 메트릭

- baseline, cap height, x-height, descender는 문자군 규칙으로 추정한다.
- 글자별 optical side bearing과 kerning은 생성하지 않는다.
- 복잡한 구두점의 위치는 휴리스틱이므로 사용자 조정이 필요할 수 있다.

## 폰트 기능

- TrueType `glyf` 기반 Regular 한 스타일만 생성한다.
- OpenType GSUB/GPOS, kerning, ligature, hinting, variable font를 지원하지 않는다.
- OTF/CFF와 WOFF2 출력은 아직 범위 밖이다.
- 한글 11,172자 조합과 자모 기반 생성은 포함하지 않는다.

## 검증

- fontTools, Fontconfig, Pillow에서 검증했으나 Windows DirectWrite, macOS CoreText, Adobe 앱, 모바일 앱의 실기기 설치 검증은 아직 수행하지 않았다.
- OTS Sanitizer와 FontBakery 검증은 이번 실행 환경에 포함되지 않았다.
