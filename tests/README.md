# Tests

이 프로젝트는 현재 `unittest`/`pytest` 스타일로 확장 가능한 최소 자동 점검 테스트를 포함합니다.

## 실행 방법

```bash
python -m pytest -q
```

또는 의존성 없는 표준 라이브러리 방식:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```
