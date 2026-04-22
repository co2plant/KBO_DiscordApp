# Tests

이 저장소의 기본 자동 검증 기준은 `unittest`입니다.

## 전체 테스트 실행

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## 단계별 검증 예시

```bash
python3 -m unittest tests.test_crawler_cleanup tests.test_settings_validation tests.test_runtime_guard -v
```

## 선택 사항

`pytest`가 설치되어 있으면 `python -m pytest -q`로도 `unittest` 호환 테스트를 실행할 수 있지만,
현재 저장소에서 기준 명령은 위 `unittest` 명령입니다.
